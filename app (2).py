import streamlit as st
import pkg_resources
import nltk

# Проверка версии Streamlit
streamlit_version = pkg_resources.get_distribution("streamlit").version
print(f"Текущая версия Streamlit: {streamlit_version}")

# Определяем правильный метод перезапуска в зависимости от версии
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            st.warning("Невозможно выполнить rerun в данной версии Streamlit")

# Настройка страницы должна быть ПЕРВОЙ командой Streamlit
st.set_page_config(
    page_title="Synthetica Financial: Симулятор финансовых респондентов",
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# СНАЧАЛА определяем функцию ensure_nltk_resources
def ensure_nltk_resources():
    """Гарантирует наличие всех необходимых ресурсов NLTK"""
    resources = [
        ('punkt', 'tokenizers/punkt'),
        ('stopwords', 'corpora/stopwords')
    ]
    
    for resource, path in resources:
        try:
            nltk.data.find(path)
            print(f"Ресурс {resource} найден")
        except LookupError:
            print(f"Загрузка ресурса {resource}...")
            nltk.download(resource, quiet=True)

# ЗАТЕМ вызываем функцию
ensure_nltk_resources()

# Загрузка необходимых ресурсов NLTK
@st.cache_resource
def load_nltk_resources():
    """Загрузка необходимых ресурсов NLTK"""
    # Загружаем базовый punkt (без указания языка)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    # Загружаем стоп-слова (в том числе русские)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    # Проверяем наличие русских стоп-слов
    if 'russian' not in stopwords.fileids():  # Изменено с available_languages() на fileids()
        nltk.download('stopwords', quiet=True)

# Теперь вызываем функцию после определения и импорта nltk
ensure_nltk_resources()

# Остальные импорты
import os
import json
import random
import re
import math
import time
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Optional, Tuple, Union, Set
from datetime import datetime
import anthropic
import openai
from tqdm import tqdm
import concurrent.futures
from functools import lru_cache
from collections import Counter, defaultdict
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import warnings
warnings.filterwarnings('ignore')

@st.cache_resource
def load_nltk_resources():
    """Загрузка необходимых ресурсов NLTK"""
    # Загружаем базовый punkt (без указания языка)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    # Загружаем стоп-слова (в том числе русские)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    # Проверяем наличие русских стоп-слов
    if 'russian' not in stopwords.fileids():  # Изменено с available_languages() на fileids()
        nltk.download('stopwords', quiet=True)
        
# Вызываем загрузку ресурсов
load_nltk_resources()

# Класс для сериализации numpy типов в JSON
class NumpyEncoder(json.JSONEncoder):
    """Специальный класс для сериализации numpy типов в JSON"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

class BankReviewsAnalyzer:
    """Класс для анализа отзывов о банках и извлечения полезной информации"""

    def __init__(self):
        """Инициализация анализатора отзывов"""
        self.reviews_data = None
        self.banks = []
        self.common_issues = {}
        self.sentiment_by_bank = {}
        self.frequent_terms = {}
        self.topics = {}
        self.russian_stopwords = set(stopwords.words('russian')) | {
            'банк', 'банка', 'банку', 'банком', 'банке', 'банков', 'банки', 'банкам', 'банками', 'банках',
            'это', 'этот', 'эта', 'эти', 'того', 'этого', 'тот', 'те', 'который', 'которого', 'которая',
            'когда', 'где', 'как', 'что', 'чем', 'почему', 'зачем', 'кто', 'кого', 'кому', 'кем', 'ком'
        }

    def load_reviews(self, file_data) -> None:
        """
        Загрузка отзывов из Excel файла с настраиваемым форматом

        Args:
            file_data: Данные Excel файла с отзывами о банках
        """
        try:
            self.reviews_data = pd.read_excel(file_data)
            st.success(f"Загружено {len(self.reviews_data)} отзывов")

            # Проверка и нормализация колонок для формата:
            # rating - оценка, theme - тема, review - отзыв, categorie - категория
            column_mapping = {}

            # Маппинг review колонки
            if 'review' in self.reviews_data.columns:
                column_mapping['review'] = 'text'
            elif 'отзыв' in self.reviews_data.columns:
                column_mapping['отзыв'] = 'text'
            elif 'текст' in self.reviews_data.columns:
                column_mapping['текст'] = 'text'

            # Маппинг rating колонки
            if 'rating' in self.reviews_data.columns:
                column_mapping['rating'] = 'rating'
            elif 'оценка' in self.reviews_data.columns:
                column_mapping['оценка'] = 'rating'
            elif 'рейтинг' in self.reviews_data.columns:
                column_mapping['рейтинг'] = 'rating'

            # Используем theme или categorie в качестве замены для bank
            if 'theme' in self.reviews_data.columns:
                column_mapping['theme'] = 'bank'
            elif 'тема' in self.reviews_data.columns:
                column_mapping['тема'] = 'bank'
            elif 'categorie' in self.reviews_data.columns:
                column_mapping['categorie'] = 'bank'
            elif 'категория' in self.reviews_data.columns:
                column_mapping['категория'] = 'bank'

            # Применяем переименование, если необходимо
            if column_mapping:
                self.reviews_data = self.reviews_data.rename(columns=column_mapping)

            # Проверка наличия необходимых колонок
            required_columns = ['text', 'rating', 'bank']
            missing_columns = [col for col in required_columns if col not in self.reviews_data.columns]

            if missing_columns:
                st.warning(f"Внимание: отсутствуют следующие колонки: {missing_columns}")
                # Создаем синтетические колонки, если нужно
                if 'text' not in self.reviews_data.columns and 'review' in self.reviews_data.columns:
                    self.reviews_data['text'] = self.reviews_data['review']
                if 'rating' not in self.reviews_data.columns:
                    self.reviews_data['rating'] = 3  # Нейтральная оценка по умолчанию
                if 'bank' not in self.reviews_data.columns:
                    self.reviews_data['bank'] = 'Не указано'  # Значение по умолчанию

            # Получение списка тем/категорий
            if 'bank' in self.reviews_data.columns:
                self.banks = self.reviews_data['bank'].unique().tolist()
                st.info(f"Найдено {len(self.banks)} тем/категорий: {', '.join(self.banks[:5] if len(self.banks) > 5 else self.banks)}...")

            # Базовый анализ
            self._analyze_reviews()

        except Exception as e:
            raise ValueError(f"Ошибка при загрузке отзывов: {str(e)}")

    def _analyze_reviews(self) -> None:
        """Выполнение базового анализа загруженных отзывов"""
        if self.reviews_data is None:
            return

        # Анализ настроения по банкам
        if all(col in self.reviews_data.columns for col in ['bank', 'rating']):
            self.sentiment_by_bank = self.reviews_data.groupby('bank')['rating'].agg(
                ['mean', 'count', 'std']).sort_values(by='mean', ascending=False).to_dict('index')

            # Добавляем категории настроения (позитивное, нейтральное, негативное)
            for bank, stats in self.sentiment_by_bank.items():
                if stats['mean'] >= 4:
                    sentiment = "позитивное"
                elif stats['mean'] >= 3:
                    sentiment = "нейтральное"
                else:
                    sentiment = "негативное"
                self.sentiment_by_bank[bank]['sentiment'] = sentiment

        # Извлечение наиболее частых терминов и проблем из отзывов
        if 'text' in self.reviews_data.columns:
            try:
                # Получение частотности терминов для всех отзывов
                all_texts = ' '.join(self.reviews_data['text'].fillna('').astype(str).tolist())
                all_words = [word.lower() for word in word_tokenize(all_texts)
                           if word.isalpha() and word.lower() not in self.russian_stopwords and len(word) > 2]

                word_freq = Counter(all_words)
                self.frequent_terms = {word: count for word, count in word_freq.most_common(100)}

                # Извлечение тем с помощью LDA
                vectorizer = TfidfVectorizer(
                    max_df=0.7, min_df=2,
                    stop_words=list(self.russian_stopwords),
                    lowercase=True,
                    ngram_range=(1, 2)
                )

                # Проверяем, достаточно ли у нас отзывов для анализа
                if len(self.reviews_data) >= 20:
                    X = vectorizer.fit_transform(self.reviews_data['text'].fillna('').astype(str))

                    # Определяем оптимальное количество тем
                    n_topics = min(10, len(self.reviews_data) // 5)

                    lda = LatentDirichletAllocation(
                        n_components=n_topics,
                        max_iter=10,
                        learning_method='online',
                        random_state=42
                    )

                    lda.fit(X)

                    feature_names = vectorizer.get_feature_names_out()

                    # Сохраняем топ-10 слов для каждой темы
                    for topic_idx, topic in enumerate(lda.components_):
                        top_features_idx = topic.argsort()[:-11:-1]
                        top_features = [feature_names[i] for i in top_features_idx]
                        self.topics[f'Тема {topic_idx+1}'] = top_features

                # Анализ негативных отзывов для выявления проблем
                if 'rating' in self.reviews_data.columns:
                    negative_reviews = self.reviews_data[self.reviews_data['rating'] <= 3]

                    if len(negative_reviews) > 0:
                        neg_text = ' '.join(negative_reviews['text'].fillna('').astype(str))

                        # Ключевые фразы, указывающие на проблемы
                        problem_indicators = [
                            'проблем', 'ошибк', 'не работает', 'не могу', 'плох', 'ужас', 'отказ',
                            'не нравится', 'трудност', 'сложно', 'невозможно', 'долго', 'очеред',
                            'хамств', 'грубо', 'навязыва', 'скрыт', 'комисси', 'обман'
                        ]

                        # Поиск проблем в тексте
                        problems = []
                        for indicator in problem_indicators:
                            pattern = re.compile(r'.{0,30}' + indicator + r'.{0,50}', re.IGNORECASE)
                            matches = pattern.findall(neg_text)
                            problems.extend(matches)

                        # Группировка похожих проблем
                        self.common_issues = Counter(problems).most_common(20)

            except Exception as e:
                st.warning(f"Предупреждение: Ошибка при анализе текста отзывов: {str(e)}")

    def get_bank_info(self, bank_name: str = None) -> Dict:
        """
        Получение информации о конкретном банке или общей информации

        Args:
            bank_name: Название банка (опционально)

        Returns:
            Словарь с информацией о банке или общей информацией
        """
        if bank_name is not None and bank_name in self.sentiment_by_bank:
            # Информация о конкретном банке
            bank_reviews = self.reviews_data[self.reviews_data['bank'] == bank_name]

            # Выбираем несколько примеров отзывов
            positive_examples = bank_reviews[bank_reviews['rating'] >= 4]['text'].sample(
                min(3, len(bank_reviews[bank_reviews['rating'] >= 4]))).tolist()

            negative_examples = bank_reviews[bank_reviews['rating'] <= 2]['text'].sample(
                min(3, len(bank_reviews[bank_reviews['rating'] <= 2]))).tolist()

            return {
                'name': bank_name,
                'sentiment': self.sentiment_by_bank[bank_name],
                'positive_examples': positive_examples,
                'negative_examples': negative_examples
            }
        else:
            # Общая информация о банках
            top_banks = sorted(
                self.sentiment_by_bank.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]

            return {
                'total_reviews': len(self.reviews_data) if self.reviews_data is not None else 0,
                'top_banks': dict(top_banks),
                'common_issues': self.common_issues,
                'frequent_terms': dict(list(self.frequent_terms.items())[:30]),
                'topics': self.topics
            }

    def get_bank_list(self) -> List[str]:
        """Получение списка всех банков в данных"""
        return self.banks

    def extract_prompting_data(self) -> Dict:
        """
        Извлечение данных для улучшения промптов

        Returns:
            Словарь с данными для промптов
        """
        result = {
            'banking_terms': list(self.frequent_terms.keys())[:50],
            'common_issues': [issue for issue, _ in self.common_issues],
            'sentiment_by_bank': {
                bank: data['sentiment']
                for bank, data in self.sentiment_by_bank.items()
            },
            'topics': self.topics
        }

        # Категоризация терминов
        term_categories = {
            'кредиты': ['кредит', 'займ', 'ссуд', 'процент', 'ставк'],
            'карты': ['карт', 'кэшбэк', 'бонус', 'лимит'],
            'обслуживание': ['обслуживани', 'сервис', 'поддержк', 'оператор', 'офис', 'отделени'],
            'приложение': ['приложени', 'сайт', 'онлайн', 'личный кабинет', 'мобильн'],
            'выплаты': ['выплат', 'перевод', 'снят', 'комисси', 'деньги', 'плат']
        }

        # Распределение терминов по категориям
        categorized_terms = defaultdict(list)
        for term in self.frequent_terms:
            for category, patterns in term_categories.items():
                if any(pattern in term.lower() for pattern in patterns):
                    categorized_terms[category].append(term)
                    break

        result['categorized_terms'] = dict(categorized_terms)
        return result

class FinancialKnowledgeBase:
    """База знаний о финансовых продуктах, терминах и типичных заблуждениях"""

    def __init__(self):
        """Инициализация базы знаний"""
        # Уровни финансовой грамотности
        self.financial_literacy_levels = {
            "отсутствие знаний": {
                "description": "Практически не знаком с банковскими услугами и финансовыми инструментами",
                "vocabulary_complexity": 0.2,
                "accuracy": 0.3,
                "confidence": 0.5,
                "detail_level": 0.2
            },
            "начинающий": {
                "description": "Имеет базовые знания (банковские карты, простые вклады)",
                "vocabulary_complexity": 0.4,
                "accuracy": 0.5,
                "confidence": 0.6,
                "detail_level": 0.4
            },
            "средний": {
                "description": "Понимает основные финансовые инструменты, имеет опыт использования кредитов",
                "vocabulary_complexity": 0.6,
                "accuracy": 0.7,
                "confidence": 0.7,
                "detail_level": 0.6
            },
            "продвинутый": {
                "description": "Хорошо разбирается в банковских продуктах, имеет опыт инвестирования",
                "vocabulary_complexity": 0.8,
                "accuracy": 0.85,
                "confidence": 0.8,
                "detail_level": 0.8
            },
            "эксперт": {
                "description": "Глубоко понимает финансовые процессы, активно использует сложные финансовые инструменты",
                "vocabulary_complexity": 0.95,
                "accuracy": 0.95,
                "confidence": 0.9,
                "detail_level": 0.9
            }
        }

        # Словарь финансовых терминов по уровням
        self.financial_vocabulary = {
            "отсутствие знаний": [
                "деньги", "зарплата", "банкомат", "карточка", "счет в банке", "проценты", "кредит", "долг",
                "комиссия", "накопления", "сберкнижка", "пластиковая карта", "обналичить", "снять деньги",
                "положить деньги", "банк", "посчитать проценты", "переплата", "рассрочка", "пин-код"
            ],
            "начинающий": [
                "дебетовая карта", "кредитная карта", "вклад", "процентная ставка", "овердрафт",
                "банковский счет", "мобильный банк", "перевод", "снятие наличных", "пополнение счета",
                "кредитный лимит", "задолженность", "минимальный платеж", "льготный период", "смс-информирование",
                "интернет-банк", "мобильное приложение", "страховка", "комиссия за обслуживание", "остаток по счету"
            ],
            "средний": [
                "капитализация процентов", "льготный период", "кредитная история", "рефинансирование",
                "автоплатеж", "кешбэк", "задолженность", "кредитный лимит", "страховка", "депозит",
                "инвестиции", "накопительный счет", "потребительский кредит", "ипотека", "досрочное погашение",
                "аннуитетный платеж", "целевой кредит", "конвертация валют", "неснижаемый остаток",
                "овердрафт", "пролонгация вклада", "составление бюджета", "налоговый вычет"
            ],
            "продвинутый": [
                "диверсификация", "инвестиционный портфель", "облигации", "акции", "фондовый рынок",
                "аннуитетный платеж", "ипотечные каникулы", "брокерский счет", "ИИС", "налоговый вычет",
                "пассивный доход", "финансовое планирование", "страхование жизни", "НПФ", "пенсионные накопления",
                "валютный риск", "ключевая ставка", "биржевой курс", "срочный рынок", "индексный фонд",
                "реструктуризация кредита", "кредитный скоринг", "лизинг", "субсидирование ставки"
            ],
            "эксперт": [
                "волатильность", "ликвидность", "хеджирование рисков", "ETF", "фьючерсы", "облигации федерального займа",
                "дюрация", "аллокация активов", "доходность к погашению", "структурные продукты", "маржинальная торговля",
                "деривативы", "РЕПО", "своп", "субординированные облигации", "листинг", "интервальные ПИФы",
                "безотзывные депозиты", "эскроу счет", "кредитные дефолтные свопы", "опционы", "финансовые коэффициенты",
                "ранжирование активов", "первичное размещение", "торговля в шорт", "стоп-лосс"
            ]
        }

        # Типичные заблуждения о финансах по уровню знаний
        self.financial_misconceptions = {
            "отсутствие знаний": [
                "Все банки одинаковые, разницы нет",
                "Кредит - это всегда плохо, а долг - признак безответственности",
                "Все банки обманывают клиентов",
                "Хранить деньги дома надежнее, чем в банке",
                "Инвестиции - это только для богатых",
                "Наличные деньги всегда лучше безналичных",
                "Чем больше банк, тем он надежнее",
                "При оформлении кредита главное - низкая процентная ставка",
                "Банкоматы других банков всегда берут огромную комиссию",
                "Банковские карты небезопасны, с них легко украсть деньги",
                "Любую банковскую услугу можно отменить в течение 14 дней",
                "Страхование - это всегда переплата",
                "В интернет-банке легко могут украсть все деньги",
                "Все финансовые вопросы очень сложные, в них невозможно разобраться"
            ],
            "начинающий": [
                "Кредитная карта - это бесплатные деньги",
                "Чем выше процент по вкладу, тем надежнее банк",
                "Страхование - это всегда переплата",
                "Любой кредит можно погасить досрочно без последствий",
                "Если не снимать деньги с карты, комиссий не будет",
                "Перевыпуск карты всегда платный",
                "Всегда выгоднее брать кредит в том банке, где получаешь зарплату",
                "Если платить минимальный платеж по кредитной карте, долг не растет",
                "Ипотека - это всегда невыгодно, лучше копить на квартиру",
                "Все инвестиции очень рискованные",
                "Овердрафт - это дополнительная бесплатная услуга",
                "Комиссия зависит только от суммы перевода",
                "Дебетовая и кредитная карты работают одинаково"
            ],
            "средний": [
                "Инвестиции всегда приносят доход",
                "Кешбэк - это просто маркетинг без реальной выгоды",
                "Чем больше кредитных карт, тем лучше кредитная история",
                "Рефинансирование всегда выгодно",
                "Все страховки одинаковые по покрытию",
                "Золото - самая надежная инвестиция",
                "Чем выше кэшбэк, тем выгоднее карта",
                "Всегда лучше досрочно погашать кредит",
                "Инвестиционный счет (ИИС) выгоден только богатым",
                "Налоговый вычет можно получить только один раз",
                "ETF фонды всегда лучше ПИФов",
                "Для инвестиций нужны большие суммы денег",
                "При инфляции выгоднее всего хранить деньги в валюте"
            ]
        }

        # Типичные проблемные ситуации с банками
        self.banking_problems = {
            "общие": [
                "Долгое ожидание в очереди в отделении",
                "Сложный и запутанный интерфейс приложения",
                "Высокие комиссии за переводы",
                "Частые сбои в работе онлайн-банка",
                "Навязчивые звонки с предложением услуг",
                "Плохая работа службы поддержки",
                "Изменение условий обслуживания без предупреждения"
            ],
            "карты": [
                "Неожиданное списание средств за обслуживание карты",
                "Проблемы с начислением кэшбэка",
                "Блокировка карты по подозрению в мошенничестве",
                "Отказ в увеличении кредитного лимита",
                "Проблемы с использованием карты за границей",
                "Неожиданные комиссии при снятии наличных"
            ],
            "кредиты": [
                "Отказ в выдаче кредита без объяснения причин",
                "Скрытые комиссии при оформлении кредита",
                "Навязывание дополнительных услуг при оформлении кредита",
                "Проблемы с досрочным погашением",
                "Ошибочное начисление штрафов за просрочку",
                "Сложности с получением справки о погашении кредита"
            ],
            "вклады": [
                "Проблемы с закрытием вклада",
                "Некорректное начисление процентов",
                "Отказ в досрочном снятии средств",
                "Изменение процентной ставки в одностороннем порядке",
                "Проблемы с автоматической пролонгацией вклада"
            ],
            "онлайн-банкинг": [
                "Сложная процедура восстановления доступа",
                "Ошибки при проведении платежей",
                "Отсутствие нужных функций в приложении",
                "Некорректное отображение баланса",
                "Сбои при входе в приложение"
            ]
        }

        # Модели финансового поведения
        self.financial_behavior_patterns = {
            "избегающий риска": [
                "Я предпочитаю надежные способы сбережения, даже если они менее доходны",
                "Лучше иметь меньший, но гарантированный доход",
                "Я избегаю кредитов, если только они не крайне необходимы",
                "Перед любым финансовым решением я долго все изучаю",
                "Стараюсь всегда иметь финансовую подушку на случай непредвиденных расходов",
                "Предпочитаю консервативные финансовые инструменты",
                "Внимательно изучаю все условия договоров"
            ],
            "импульсивный": [
                "Я часто принимаю спонтанные финансовые решения",
                "Меня привлекают акции и спецпредложения",
                "Я могу взять кредит на крупную покупку без длительных раздумий",
                "Планирование бюджета не для меня",
                "Предпочитаю тратить, а не копить",
                "Часто поддаюсь на маркетинговые уловки",
                "Живу сегодняшним днем, не думая о завтрашнем"
            ],
            "прагматичный": [
                "Я всегда сравниваю условия разных банков",
                "Важно понимать все условия договора",
                "Я регулярно анализирую свои расходы",
                "Перед крупными тратами я обдумываю все за и против",
                "Веду учет доходов и расходов",
                "Пользуюсь финансовыми инструментами, которые реально приносят пользу",
                "Стараюсь находить баланс между тратами и сбережениями"
            ],
            "осознанный минималист": [
                "Стараюсь тщательно выбирать на что тратить деньги",
                "Предпочитаю качественные вещи, которые прослужат долго",
                "Считаю, что деньги должны приносить пользу и радость",
                "Не гонюсь за модой и брендами",
                "Избегаю импульсивных покупок",
                "Трачу на то, что действительно ценно для меня"
            ],
            "статусный": [
                "Для меня важен престиж банка и премиальное обслуживание",
                "Предпочитаю платиновые и премиальные карты",
                "Готов платить больше за статусные услуги и продукты",
                "Важно иметь лучшие условия обслуживания",
                "Обращаю внимание на бренд и имидж финансовой организации",
                "Пользуюсь дополнительными премиальными сервисами"
            ]
        }

        # Распространенные финансовые цели людей
        self.financial_goals = {
            "краткосрочные": [
                "накопить на отпуск",
                "купить новый телефон/гаджет",
                "сделать ремонт",
                "создать подушку безопасности",
                "погасить кредит",
                "накопить на обучение",
                "купить подарок близкому человеку"
            ],
            "среднесрочные": [
                "накопить на автомобиль",
                "первоначальный взнос по ипотеке",
                "оплатить образование",
                "открыть небольшой бизнес",
                "сделать капитальный ремонт в квартире",
                "накопить на свадьбу"
            ],
            "долгосрочные": [
                "накопить на пенсию",
                "купить недвижимость без ипотеки",
                "обеспечить образование детям",
                "достичь финансовой независимости",
                "создать пассивный доход",
                "накопить на дорогостоящее лечение"
            ]
        }

        # Банковские продукты и их особенности
        self.banking_products = {
            "дебетовые карты": {
                "назначение": "Для хранения денег и ежедневных расчетов",
                "функции": ["платежи", "переводы", "снятие наличных", "кэшбэк", "бесконтактная оплата"],
                "особенности": ["могут иметь плату за обслуживание", "разные условия кэшбэка и бонусов", "лимиты на снятие наличных"]
            },
            "кредитные карты": {
                "назначение": "Для заимствования денег у банка для покупок",
                "функции": ["льготный период", "кредитный лимит", "минимальный платеж", "кэшбэк", "бонусные программы"],
                "особенности": ["высокие проценты после льготного периода", "комиссии за снятие наличных", "плата за обслуживание"]
            },
            "потребительские кредиты": {
                "назначение": "Для крупных покупок или других целей",
                "функции": ["фиксированная сумма", "регулярные ежемесячные платежи", "фиксированный срок"],
                "особенности": ["требуется подтверждение дохода", "может требоваться залог или поручитель", "в случае просрочки начисляются штрафы"]
            },
            "ипотека": {
                "назначение": "Для покупки недвижимости",
                "функции": ["длительный срок (до 30 лет)", "залог недвижимости", "первоначальный взнос"],
                "особенности": ["строгая проверка платежеспособности", "обязательное страхование", "возможность использования материнского капитала"]
            },
            "вклады": {
                "назначение": "Для сбережения и приумножения денег",
                "функции": ["начисление процентов", "срочные и до востребования", "возможность пополнения", "капитализация процентов"],
                "особенности": ["защита вкладов до 1,4 млн рублей", "штрафы за досрочное снятие", "разные процентные ставки в зависимости от суммы и срока"]
            },
            "накопительные счета": {
                "назначение": "Для гибкого накопления",
                "функции": ["свободное пополнение и снятие", "начисление процентов на остаток", "нет срока"],
                "особенности": ["ставка обычно ниже, чем по вкладам", "проценты часто зависят от суммы на счете", "банк может менять условия"]
            },
            "инвестиционные продукты": {
                "назначение": "Для приумножения капитала",
                "функции": ["акции", "облигации", "ПИФы", "ИИС", "брокерский счет"],
                "особенности": ["нет гарантии доходности", "есть риски", "возможность налоговых вычетов", "долгосрочный характер"]
            }
        }

    def get_literacy_level_info(self, level: str) -> Dict:
        """
        Получение информации о конкретном уровне финансовой грамотности

        Args:
            level: Название уровня

        Returns:
            Словарь с информацией о уровне грамотности
        """
        if level in self.financial_literacy_levels:
            return self.financial_literacy_levels[level]
        else:
            # Возвращаем информацию о среднем уровне, если указанный не найден
            return self.financial_literacy_levels["средний"]

    def get_vocabulary_for_level(self, level: str, num_terms: int = 10) -> List[str]:
        """
        Получение словарного запаса для указанного уровня грамотности

        Args:
            level: Уровень финансовой грамотности
            num_terms: Количество терминов для возврата

        Returns:
            Список финансовых терминов соответствующего уровня
        """
        # Для каждого уровня включаем термины всех предыдущих уровней
        all_terms = []

        levels_order = ["отсутствие знаний", "начинающий", "средний", "продвинутый", "эксперт"]

        for l in levels_order:
            all_terms.extend(self.financial_vocabulary.get(l, []))
            if l == level:
                break

        # Возвращаем случайную выборку терминов
        return random.sample(all_terms, min(num_terms, len(all_terms)))

    def get_misconceptions_for_level(self, level: str, num_items: int = 3) -> List[str]:
        """
        Получение типичных заблуждений для указанного уровня грамотности

        Args:
            level: Уровень финансовой грамотности
            num_items: Количество заблуждений для возврата

        Returns:
            Список типичных финансовых заблуждений
        """
        # Для каждого уровня включаем заблуждения всех предыдущих уровней
        all_misconceptions = []

        levels_order = ["отсутствие знаний", "начинающий", "средний", "продвинутый", "эксперт"]
        level_index = levels_order.index(level) if level in levels_order else 2  # Используем "средний" уровень по умолчанию

        for i in range(level_index + 1):
            current_level = levels_order[i]
            if current_level in self.financial_misconceptions:
                all_misconceptions.extend(self.financial_misconceptions[current_level])

        # Чем выше уровень, тем меньше заблуждений
        max_misconceptions = max(1, 5 - level_index)

        return random.sample(all_misconceptions, min(num_items, max_misconceptions, len(all_misconceptions)))

    def get_behavior_patterns(self, behavior_type: str) -> List[str]:
        """
        Получение шаблонов финансового поведения

        Args:
            behavior_type: Тип поведения

        Returns:
            Список шаблонов поведения
        """
        if behavior_type in self.financial_behavior_patterns:
            return self.financial_behavior_patterns[behavior_type]
        else:
            # Если тип не найден, возвращаем случайный тип
            random_type = random.choice(list(self.financial_behavior_patterns.keys()))
            return self.financial_behavior_patterns[random_type]

    def get_random_financial_goals(self, num_goals: int = 2) -> List[str]:
        """
        Получение случайных финансовых целей

        Args:
            num_goals: Количество целей для возврата

        Returns:
            Список финансовых целей
        """
        all_goals = []
        for goals in self.financial_goals.values():
            all_goals.extend(goals)

        return random.sample(all_goals, min(num_goals, len(all_goals)))

    def get_product_info(self, product_type: str) -> Dict:
        """
        Получение информации о банковском продукте

        Args:
            product_type: Тип банковского продукта

        Returns:
            Словарь с информацией о продукте
        """
        if product_type in self.banking_products:
            return self.banking_products[product_type]
        else:
            # Возвращаем список всех продуктов
            return {k: v["назначение"] for k, v in self.banking_products.items()}

    def get_common_problems(self, category: str = None) -> List[str]:
        """
        Получение типичных проблем с банками

        Args:
            category: Категория проблем (опционально)

        Returns:
            Список типичных проблем
        """
        if category and category in self.banking_problems:
            return self.banking_problems[category]
        elif category is None:
            # Возвращаем все проблемы
            all_problems = []
            for problems in self.banking_problems.values():
                all_problems.extend(problems)
            return all_problems
        else:
            return self.banking_problems["общие"]

# НОВЫЕ КЛАССЫ ДЛЯ УЛУЧШЕНИЯ РЕАЛИСТИЧНОСТИ РЕСПОНДЕНТОВ

class CognitiveBiases:
    """Класс для моделирования когнитивных искажений в финансовом поведении"""

    def __init__(self):
        """Инициализация моделей когнитивных искажений"""
        # Основные финансовые когнитивные искажения
        self.financial_biases = {
            "эффект_якоря": {
                "description": "Тенденция чрезмерно полагаться на первую предоставленную информацию (якорь)",
                "examples": [
                    "Если первая увиденная цена кредита 10%, все остальные предложения сравниваются с ней",
                    "Первоначальная цена товара влияет на восприятие скидки, даже если она завышена",
                    "Зарплатные ожидания формируются вокруг первого полученного предложения"
                ],
                "trigger_words": ["первый", "изначально", "сначала", "начальный", "первоначальный"]
            },
            "избегание_потерь": {
                "description": "Потери воспринимаются сильнее, чем эквивалентные выигрыши",
                "examples": [
                    "Отказ продавать акции в минус, даже когда это рационально",
                    "Страх потерять накопления перевешивает потенциальную выгоду от инвестиций",
                    "Избегание финансовых решений от страха сделать ошибку"
                ],
                "trigger_words": ["потеря", "риск", "страх", "опасно", "минус", "убыток"]
            },
            "эффект_необратимых_затрат": {
                "description": "Продолжение инвестирования из-за уже вложенных средств",
                "examples": [
                    "Продолжение держать убыточные инвестиции, потому что 'уже столько вложил'",
                    "Отказ отказаться от ненужной подписки из-за предыдущих затрат",
                    "Удержание ненужных вещей из-за их стоимости"
                ],
                "trigger_words": ["уже вложил", "жалко бросать", "столько потрачено", "не пропадать же"]
            },
            "чрезмерная_самоуверенность": {
                "description": "Переоценка собственных знаний и способностей",
                "examples": [
                    "Уверенность в способности 'переиграть рынок' без специальных знаний",
                    "Игнорирование профессиональных финансовых советов",
                    "Недостаточная диверсификация из-за уверенности в конкретных активах"
                ],
                "trigger_words": ["я лучше знаю", "сам разберусь", "это очевидно", "я уверен"]
            },
            "стадное_поведение": {
                "description": "Следование финансовым решениям большинства",
                "examples": [
                    "Инвестирование в популярные активы без собственного анализа",
                    "Выбор банка, которым пользуются знакомые",
                    "Паника при падении рынка из-за общего настроения"
                ],
                "trigger_words": ["все так делают", "популярно", "тренд", "мои знакомые"]
            },
            "ментальный_учет": {
                "description": "Разделение денег на категории, изменяющее отношение к тратам",
                "examples": [
                    "Готовность тратить 'подарочные' деньги на роскошь, даже при наличии долгов",
                    "Разделение денег на 'можно тратить' и 'нельзя трогать'",
                    "Разное отношение к одинаковым суммам из разных источников"
                ],
                "trigger_words": ["это другие деньги", "эти деньги на", "специальные деньги", "особый случай"]
            },
            "эффект_текущего_момента": {
                "description": "Предпочтение немедленного вознаграждения перед долгосрочной выгодой",
                "examples": [
                    "Трата на сиюминутные желания вместо откладывания на важные цели",
                    "Импульсивные покупки вместо запланированных",
                    "Отказ от инвестирования в пользу трат на развлечения"
                ],
                "trigger_words": ["хочу сейчас", "зачем ждать", "живем один раз", "надо себя баловать"]
            }
        }

        # Уровни склонности к когнитивным искажениям
        self.bias_levels = {
            "слабый": 0.2,    # Редко проявляется, слабое влияние
            "средний": 0.5,   # Периодически проявляется, умеренное влияние
            "сильный": 0.8    # Часто проявляется, сильное влияние
        }

    def get_random_biases(self, num_biases: int = 2, literacy_level: str = "средний") -> Dict[str, float]:
        """
        Генерация случайного набора когнитивных искажений для персоны

        Args:
            num_biases: Количество искажений для генерации
            literacy_level: Уровень финансовой грамотности

        Returns:
            Словарь с когнитивными искажениями и их силой
        """
        # Корректируем количество искажений на основе уровня грамотности
        if literacy_level == "отсутствие знаний":
            num_biases = min(4, num_biases + 2)
        elif literacy_level == "начинающий":
            num_biases = min(3, num_biases + 1)
        elif literacy_level == "эксперт":
            num_biases = max(1, num_biases - 1)

        # Выбираем случайные искажения
        selected_biases = random.sample(list(self.financial_biases.keys()), k=min(num_biases, len(self.financial_biases)))

        # Определяем силу проявления каждого искажения
        bias_strengths = {}

        # Распределение вероятностей уровней искажений в зависимости от грамотности
        if literacy_level in ["отсутствие знаний", "начинающий"]:
            level_weights = {"слабый": 0.2, "средний": 0.3, "сильный": 0.5}
        elif literacy_level == "средний":
            level_weights = {"слабый": 0.3, "средний": 0.5, "сильный": 0.2}
        elif literacy_level in ["продвинутый", "эксперт"]:
            level_weights = {"слабый": 0.5, "средний": 0.4, "сильный": 0.1}
        else:
            level_weights = {"слабый": 0.33, "средний": 0.34, "сильный": 0.33}

        # Назначаем силу каждому искажению
        for bias in selected_biases:
            bias_level = random.choices(
                list(level_weights.keys()),
                weights=list(level_weights.values())
            )[0]

            # Добавляем случайную вариацию для реалистичности
            strength = self.bias_levels[bias_level] * random.uniform(0.8, 1.2)
            # Ограничиваем в диапазоне [0.1, 1.0]
            strength = max(0.1, min(1.0, strength))

            bias_strengths[bias] = strength

        return bias_strengths

    def apply_bias_to_prompt(self, prompt: str, bias_name: str, bias_strength: float) -> str:
        """
        Добавление инструкций по когнитивному искажению в промпт

        Args:
            prompt: Исходный промпт
            bias_name: Название когнитивного искажения
            bias_strength: Сила искажения (0.0-1.0)

        Returns:
            Модифицированный промпт
        """
        if bias_name not in self.financial_biases:
            return prompt

        bias_info = self.financial_biases[bias_name]
        bias_level = "заметно" if bias_strength > 0.65 else "умеренно" if bias_strength > 0.35 else "слегка"

        # Выбираем случайный пример проявления искажения
        example = random.choice(bias_info["examples"])

        # Формируем инструкцию по применению искажения
        bias_instruction = f"""
КОГНИТИВНОЕ ИСКАЖЕНИЕ "{bias_name}":
- {bias_info["description"]}
- Проявляется {bias_level} (сила: {bias_strength:.1f})
- Пример: {example}
- Это может отражаться в ответе фразами типа: "{', '.join(random.sample(bias_info["trigger_words"], k=min(3, len(bias_info["trigger_words"]))))}"
"""

        # Добавляем инструкцию в промпт
        if "КОГНИТИВНЫЕ ИСКАЖЕНИЯ:" in prompt:
            # Если раздел уже есть, добавляем в него
            prompt = prompt.replace("КОГНИТИВНЫЕ ИСКАЖЕНИЯ:", f"КОГНИТИВНЫЕ ИСКАЖЕНИЯ:\n{bias_instruction}")
        else:
            # Иначе добавляем новый раздел перед "ОБЩИЕ ПРАВИЛА ОТВЕТА"
            if "ОБЩИЕ ПРАВИЛА ОТВЕТА" in prompt:
                prompt = prompt.replace("ОБЩИЕ ПРАВИЛА ОТВЕТА", f"КОГНИТИВНЫЕ ИСКАЖЕНИЯ:\n{bias_instruction}\n\nОБЩИЕ ПРАВИЛА ОТВЕТА")
            else:
                prompt += f"\n\nКОГНИТИВНЫЕ ИСКАЖЕНИЯ:\n{bias_instruction}"

        return prompt


class EmotionalFactors:
    """Класс для моделирования эмоциональных факторов в финансовом поведении"""

    def __init__(self):
        """Инициализация моделей эмоциональных факторов"""
        # Основные эмоциональные факторы, влияющие на финансовое поведение
        self.financial_emotions = {
            "финансовая_тревога": {
                "description": "Беспокойство и страх по поводу финансового положения/будущего",
                "examples": [
                    "Постоянное беспокойство о нехватке денег",
                    "Страх потерять работу и доход",
                    "Избегание проверки банковского баланса",
                    "Ощущение, что денег всегда недостаточно, даже при объективно нормальном положении"
                ],
                "trigger_words": ["беспокоюсь", "страшно", "вдруг", "а если", "тревожно", "боюсь"],
                "common_topics": ["долги", "кредиты", "инвестиции", "сбережения", "пенсия"]
            },
            "финансовый_стыд": {
                "description": "Чувство стыда или неполноценности из-за финансовых проблем/решений",
                "examples": [
                    "Избегание обсуждения долгов даже с близкими",
                    "Сокрытие финансовых трудностей",
                    "Ощущение собственной безответственности из-за финансовых проблем",
                    "Сравнение своего положения с другими не в свою пользу"
                ],
                "trigger_words": ["стыдно признаться", "неудобно говорить", "не хочу, чтобы знали", "скрываю"],
                "common_topics": ["долги", "кредиты", "низкий доход", "неудачные инвестиции"]
            },
            "финансовая_гордость": {
                "description": "Гордость за финансовые достижения, умные решения",
                "examples": [
                    "Удовлетворение от накопленной суммы",
                    "Гордость за выгодные инвестиции",
                    "Удовольствие от статусных финансовых продуктов",
                    "Желание делиться успешным опытом"
                ],
                "trigger_words": ["горжусь", "доволен", "удалось", "смог достичь", "преуспел"],
                "common_topics": ["инвестиции", "накопления", "премиальные услуги", "финансовые цели"]
            },
            "финансовый_фатализм": {
                "description": "Вера в предопределенность финансового положения, отсутствие контроля",
                "examples": [
                    "Убеждение, что богатство - дело удачи или судьбы",
                    "Ощущение бессмысленности финансового планирования",
                    "Перекладывание ответственности на внешние обстоятельства",
                    "Отказ от активных действий по улучшению ситуации"
                ],
                "trigger_words": ["от меня не зависит", "как повезет", "судьба такая", "всё равно ничего не изменить"],
                "common_topics": ["инвестиции", "накопления", "карьера", "доходы"]
            },
            "финансовая_надежда": {
                "description": "Оптимизм относительно финансового будущего",
                "examples": [
                    "Вера в улучшение финансового положения",
                    "Готовность пробовать новые финансовые инструменты",
                    "Позитивное отношение к возможностям",
                    "Устойчивость перед временными трудностями"
                ],
                "trigger_words": ["верю", "надеюсь", "обязательно получится", "всё наладится", "перспективы"],
                "common_topics": ["инвестиции", "карьера", "развитие", "новые возможности"]
            },
            "финансовая_вина": {
                "description": "Чувство вины за финансовые решения или ситуацию",
                "examples": [
                    "Самообвинение за неправильные финансовые решения",
                    "Чувство вины за траты на себя",
                    "Вина за зависимость от финансовой поддержки других",
                    "Обвинение себя в жадности или расточительности"
                ],
                "trigger_words": ["виноват", "не должен был", "ошибся", "подвел", "жалею"],
                "common_topics": ["долги", "траты", "неудачные решения", "содержание близких"]
            },
            "финансовое_безразличие": {
                "description": "Апатия и отстраненность от финансовых вопросов",
                "examples": [
                    "Игнорирование финансового планирования",
                    "Отсутствие интереса к оптимизации трат/доходов",
                    "Делегирование финансовых решений другим",
                    "Жизнь сегодняшним днем без мыслей о будущем"
                ],
                "trigger_words": ["не интересно", "как-нибудь", "всё равно", "не заморачиваюсь", "не важно"],
                "common_topics": ["планирование", "инвестиции", "бюджет", "пенсия"]
            }
        }

        # Уровни склонности к эмоциональным факторам
        self.emotion_levels = {
            "слабый": 0.2,    # Редко проявляется, слабое влияние
            "средний": 0.5,   # Периодически проявляется, умеренное влияние
            "сильный": 0.8    # Часто проявляется, сильное влияние
        }

    def get_random_emotions(self, num_emotions: int = 2) -> Dict[str, float]:
        """
        Генерация случайного набора эмоциональных факторов для персоны

        Args:
            num_emotions: Количество эмоциональных факторов

        Returns:
            Словарь с эмоциональными факторами и их силой
        """
        # Выбираем случайные эмоциональные факторы
        selected_emotions = random.sample(list(self.financial_emotions.keys()), k=min(num_emotions, len(self.financial_emotions)))

        # Определяем силу проявления каждого фактора
        emotion_strengths = {}

        for emotion in selected_emotions:
            # Выбираем случайный уровень с равной вероятностью
            emotion_level = random.choice(list(self.emotion_levels.keys()))

            # Добавляем случайную вариацию для реалистичности
            strength = self.emotion_levels[emotion_level] * random.uniform(0.8, 1.2)
            # Ограничиваем в диапазоне [0.1, 1.0]
            strength = max(0.1, min(1.0, strength))

            emotion_strengths[emotion] = strength

        return emotion_strengths

    def apply_emotion_to_prompt(self, prompt: str, emotion_name: str, emotion_strength: float, topic: str = None) -> str:
        """
        Добавление инструкций по эмоциональному фактору в промпт

        Args:
            prompt: Исходный промпт
            emotion_name: Название эмоционального фактора
            emotion_strength: Сила фактора (0.0-1.0)
            topic: Тема вопроса

        Returns:
            Модифицированный промпт
        """
        if emotion_name not in self.financial_emotions:
            return prompt

        emotion_info = self.financial_emotions[emotion_name]
        emotion_level = "сильно" if emotion_strength > 0.65 else "умеренно" if emotion_strength > 0.35 else "слегка"

        # Определяем релевантность к теме
        relevant_to_topic = True
        if topic and emotion_info["common_topics"]:
            # Проверяем, релевантна ли эмоция к теме вопроса
            relevant_to_topic = any(t in topic.lower() for t in emotion_info["common_topics"])

            # Даже если нет прямого соответствия, с некоторой вероятностью всё равно применяем
            if not relevant_to_topic and random.random() < 0.3:
                relevant_to_topic = True

        # Если эмоция не релевантна теме и у нас есть тема, уменьшаем силу
        if not relevant_to_topic and topic:
            emotion_strength *= 0.5
            emotion_level = "слегка"

        # Если сила стала слишком мала, пропускаем
        if emotion_strength < 0.2:
            return prompt

        # Выбираем случайный пример проявления эмоции
        example = random.choice(emotion_info["examples"])

        # Формируем инструкцию по применению эмоционального фактора
        emotion_instruction = f"""
ЭМОЦИОНАЛЬНЫЙ ФАКТОР "{emotion_name}":
- {emotion_info["description"]}
- Проявляется {emotion_level} (сила: {emotion_strength:.1f})
- Пример: {example}
- Это может отражаться в ответе фразами типа: "{', '.join(random.sample(emotion_info["trigger_words"], k=min(3, len(emotion_info["trigger_words"]))))}"
"""

        # Добавляем инструкцию в промпт
        if "ЭМОЦИОНАЛЬНЫЕ ФАКТОРЫ:" in prompt:
            # Если раздел уже есть, добавляем в него
            prompt = prompt.replace("ЭМОЦИОНАЛЬНЫЕ ФАКТОРЫ:", f"ЭМОЦИОНАЛЬНЫЕ ФАКТОРЫ:\n{emotion_instruction}")
        else:
            # Иначе добавляем новый раздел перед "ОБЩИЕ ПРАВИЛА ОТВЕТА"
            if "ОБЩИЕ ПРАВИЛА ОТВЕТА" in prompt:
                prompt = prompt.replace("ОБЩИЕ ПРАВИЛА ОТВЕТА", f"ЭМОЦИОНАЛЬНЫЕ ФАКТОРЫ:\n{emotion_instruction}\n\nОБЩИЕ ПРАВИЛА ОТВЕТА")
            else:
                prompt += f"\n\nЭМОЦИОНАЛЬНЫЕ ФАКТОРЫ:\n{emotion_instruction}"

        return prompt


class LinguisticVariation:
    """Класс для моделирования лингвистических вариаций в речи"""

    def __init__(self):
        """Инициализация моделей лингвистических вариаций"""
        # Региональные особенности речи
        self.regional_speech_patterns = {
            "Москва": {
                "words": ["мкад", "кольцевая", "область", "замкадье", "столичный", "садовое", "выхино"],
                "expressions": ["на районе", "московские цены", "как в столице"]
            },
            "Санкт-Петербург": {
                "words": ["парадная", "поребрик", "кура", "шаверма", "культурная столица"],
                "expressions": ["на Петроградке", "у нас в Питере", "на Ваське"]
            },
            "Центральный": {
                "words": ["тульский", "воронежский", "областной центр"],
                "expressions": ["в центре России", "недалеко от Москвы"]
            },
            "Южный": {
                "words": ["хата", "станица", "кубанский", "краснодарский"],
                "expressions": ["у нас на юге", "по-кубански", "как на Дону"]
            },
            "Северо-Кавказский": {
                "words": ["джигит", "тейп", "аул", "лезгинка"],
                "expressions": ["у нас в горах", "на Кавказе так не принято"]
            },
            "Приволжский": {
                "words": ["татарстанский", "казанский", "приволжский"],
                "expressions": ["у нас на Волге", "по-волжски", "в Татарстане"]
            },
            "Уральский": {
                "words": ["заводской", "суровый", "уральский", "горнозаводской"],
                "expressions": ["у нас на Урале", "как на Урале говорят", "по-уральски"]
            },
            "Сибирский": {
                "words": ["тайга", "мороз", "сибирский", "шишка"],
                "expressions": ["у нас в Сибири", "по-сибирски", "не мороз, а дубак"]
            },
            "Дальневосточный": {
                "words": ["океан", "приморский", "сопка", "владивостокский"],
                "expressions": ["у нас на Дальнем", "во Владике", "дальневосточный"]
            }
        }

        # Слова-паразиты по возрастным группам
        self.filler_words_by_age = {
            "18-25": ["типа", "короче", "прикинь", "реально", "вообще", "капец", "блин", "походу", "имхо"],
            "26-35": ["собственно", "как бы", "в принципе", "фактически", "буквально", "объективно", "чисто"],
            "36-50": ["так сказать", "в общем-то", "собственно говоря", "по сути", "значит", "видите ли", "скажем так"],
            "51-65": ["знаете ли", "понимаете", "надо сказать", "откровенно говоря", "если позволите"],
            "66-80": ["стало быть", "вот", "значится", "видите как", "не побоюсь этого слова", "истинно"]
        }

        # Поколенческий сленг
        self.generational_slang = {
            "18-25": {
                "финансовый": ["крипта", "донатить", "скам", "застейкать", "холдить", "задонатить", "байнуть", "го на аирдроп", "изи", "хайпануть"],
                "общий": ["краш", "чилить", "кринж", "рофл", "зашквар", "чекать", "агриться", "токсик", "хейтить", "флексить", "рилток"]
            },
            "26-35": {
                "финансовый": ["профит", "кэшбек", "инвестить", "стартап", "венчур", "инфлуенсер", "монетизировать", "хакатон"],
                "общий": ["лайфхак", "хейтер", "топчик", "форсить", "зафейлить", "лол", "жиза", "хапнуть", "стартапер"]
            },
            "36-50": {
                "финансовый": ["откат", "обнал", "безнал", "аренда", "инвест-портфель", "пассивный доход", "недвижка"],
                "общий": ["продвинутый", "комп", "сетевой", "зыринг", "клёво", "фишка", "прикольно", "месседж"]
            },
            "51-65": {
                "финансовый": ["вклад", "сберкнижка", "пенсионные", "госзайм", "кредитка", "подорожание", "квитанция"],
                "общий": ["молодежь", "интернеты", "компьютерщик", "наркоманы", "мобильник", "клавиши"]
            },
            "66-80": {
                "финансовый": ["сбережения", "книжка", "пенсия", "накопления", "ссуда", "сотка", "пятак", "получка"],
                "общий": ["телевизер", "нонче", "намедни", "давеча", "милок", "антиресно", "покуда", "давненько"]
            }
        }

        # Типичные опечатки и ошибки
        self.common_errors = {
            "age": {  # Ошибки связанные с возрастом
                "18-25": {  # молодежь: быстрый набор, игнорирование знаков препинания и заглавных букв
                    "punctuation_omission": 0.7,  # частое опускание знаков препинания
                    "abbreviations": 0.6,         # сокращения слов
                    "letter_repetition": 0.4,     # повторение букв для эмфазы
                    "phoneticization": 0.5        # фонетическое написание (шо, чо)
                },
                "26-35": {
                    "typos": 0.4,                # обычные опечатки
                    "punctuation_omission": 0.5,  # иногда опускание знаков препинания
                    "autocompletion_errors": 0.6  # ошибки автозамены
                },
                "36-50": {
                    "typos": 0.3,                # меньше опечаток
                    "run_on_sentences": 0.4       # длинные предложения без знаков препинания
                },
                "51-65": {
                    "spacing_errors": 0.5,        # проблемы с пробелами
                    "caps_lock": 0.3,             # случайный КАПС
                    "punctuation_excess": 0.4     # избыток знаков препинания!!!!
                },
                "66-80": {
                    "spacing_errors": 0.7,        # серьезные проблемы с пробелами
                    "caps_lock": 0.6,             # частый КАПС
                    "punctuation_excess": 0.7,    # избыток знаков препинания!!!!!!!
                    "repetition": 0.5             # повторение фраз
                }
            },
            "device": {  # Ошибки связанные с устройством
                "mobile": {  # мобильная клавиатура
                    "typos": 0.6,                # больше опечаток
                    "autocorrect_fails": 0.7,     # ошибки автозамены
                    "abbreviations": 0.5,         # сокращения слов
                    "brevity": 0.8                # краткость сообщений
                },
                "desktop": {  # обычная клавиатура
                    "typos": 0.3,                # меньше опечаток
                    "autocorrect_fails": 0.2,     # меньше ошибок автозамены
                    "verbosity": 0.6              # более многословные ответы
                }
            },
            "education": {  # Ошибки связанные с образованием
                "Начальное образование": {
                    "grammar_errors": 0.8,         # грамматические ошибки
                    "spelling_errors": 0.8,        # орфографические ошибки
                    "syntax_errors": 0.7,          # синтаксические ошибки
                    "simple_vocabulary": 0.9       # простой словарный запас
                },
                "Среднее образование": {
                    "grammar_errors": 0.6,         # грамматические ошибки
                    "spelling_errors": 0.5,        # орфографические ошибки
                    "syntax_errors": 0.5           # синтаксические ошибки
                },
                "Среднее специальное": {
                    "grammar_errors": 0.5,         # грамматические ошибки
                    "spelling_errors": 0.4,        # орфографические ошибки
                    "jargon": 0.6                 # профессиональный жаргон
                },
                "Высшее": {  # общее для всех видов высшего
                    "grammar_errors": 0.3,         # меньше грамматических ошибок
                    "spelling_errors": 0.3,        # меньше орфографических ошибок
                    "complex_sentences": 0.6       # сложные предложения
                },
                "Ученая степень": {
                    "grammar_errors": 0.2,         # мало грамматических ошибок
                    "spelling_errors": 0.2,        # мало орфографических ошибок
                    "complex_vocabulary": 0.8,     # сложный словарный запас
                    "formality": 0.7               # формальный стиль
                }
            }
        }

        # Примеры грамматических ошибок
        self.grammar_error_patterns = {
            "case_errors": [  # ошибки в падежах
                (r'\b(о|об|при|в|на|за|под|над|перед|с) ([а-яА-Я]+)([^а-яА-Я]|$)', r'\1 \2е\3'),  # некорректный предложный падеж
                (r'\b(к|по|благодаря) ([а-яА-Я]+)([^а-яА-Я]|$)', r'\1 \2у\3')  # некорректный дательный падеж
            ],
            "verb_errors": [  # ошибки в глаголах
                (r'\b(я) ([а-яА-Я]+)(ешь|ете|ишь|ите)([^а-яА-Я]|$)', r'\1 \2у\4'),  # некорректное спряжение
                (r'\b(они) ([а-яА-Я]+)(у|ю|м)([^а-яА-Я]|$)', r'\1 \2ут\4')  # некорректное спряжение
            ],
            "gender_errors": [  # ошибки в согласовании по роду
                (r'\b(он) ([а-яА-Я]+)(ла|лась)([^а-яА-Я]|$)', r'\1 \2л\4'),
                (r'\b(она) ([а-яА-Я]+)(л|лся)([^а-яА-Я]|$)', r'\1 \2ла\4')
            ]
        }

        # Словарь исправлений орфографических ошибок (для применения)
        self.spelling_error_patterns = {
            # Типичные ошибки в русском языке
            "ться-тся": [(r'ться', 'тся'), (r'тся', 'ться')],
            "жи-ши": [(r'жы', 'жи'), (r'шы', 'ши')],
            "ча-ща": [(r'чя', 'ча'), (r'щя', 'ща')],
            "чу-щу": [(r'чю', 'чу'), (r'щю', 'щу')],
            "безударные гласные": [
                (r'изв[ие]ни', 'извини'), (r'к[ао]мпания', 'компания'), (r'инт[ие]ресно', 'интересно'),
                (r'инт[ие]ресует', 'интересует'), (r'выт[ие]рпеть', 'вытерпеть')
            ],
            "парные согласные": [
                (r'сколь[зс]кий', 'скользкий'), (r'ни[зс]кий', 'низкий'),
                (r'вла[сз]ть', 'власть'), (r'ло[шж]ка', 'ложка')
            ],
            "непроизносимые согласные": [
                (r'чу[вс]ств', 'чувств'), (r'сер[д]це', 'сердце'),
                (r'со[л]нце', 'солнце'), (r'праз[д]ник', 'праздник')
            ],
            "двойные согласные": [
                (r'ра[с]{1,2}каз', 'рассказ'), (r'ка[с]{1,2}а', 'касса'),
                (r'ко[л]{1,2}ектив', 'коллектив'), (r'ко[м]{1,2}ентарий', 'комментарий')
            ]
        }

    def get_age_group(self, age: int) -> str:
        """Определение возрастной группы по возрасту"""
        if age <= 25:
            return "18-25"
        elif age <= 35:
            return "26-35"
        elif age <= 50:
            return "36-50"
        elif age <= 65:
            return "51-65"
        else:
            return "66-80"

    def generate_linguistic_profile(self, persona: Dict) -> Dict:
        """
        Создание лингвистического профиля для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Словарь с лингвистическим профилем
        """
        age = persona.get('Возраст', 30)
        region = persona.get('Регион', 'Москва')
        education = persona.get('Образование', 'Высшее (бакалавр)')

        # Определяем возрастную группу
        age_group = self.get_age_group(age)

        # Формируем базовый профиль
        profile = {
            "age_group": age_group,
            "region": region,
            "education": education,

            # Региональные особенности речи
            "regional_words": self.regional_speech_patterns.get(region, {}).get("words", []),
            "regional_expressions": self.regional_speech_patterns.get(region, {}).get("expressions", []),

            # Слова-паразиты по возрасту
            "filler_words": self.filler_words_by_age.get(age_group, self.filler_words_by_age["36-50"]),

            # Поколенческий сленг
            "financial_slang": self.generational_slang.get(age_group, {}).get("финансовый", []),
            "general_slang": self.generational_slang.get(age_group, {}).get("общий", []),

            # Профиль ошибок
            "error_profile": {}
        }

        # Настройка профиля ошибок на основе демографии
        # Возрастные ошибки
        age_errors = self.common_errors["age"].get(age_group, self.common_errors["age"]["36-50"])

        # Образовательные ошибки
        # Упрощаем типы образования до базовых категорий
        if "Высшее" in education or "высшее" in education:
            edu_type = "Высшее"
        elif "Ученая степень" in education:
            edu_type = "Ученая степень"
        elif "специальное" in education:
            edu_type = "Среднее специальное"
        elif "Среднее" in education:
            edu_type = "Среднее образование"
        else:
            edu_type = "Начальное образование"

        edu_errors = self.common_errors["education"].get(edu_type, self.common_errors["education"]["Среднее образование"])

        # Ошибки устройства (здесь предполагаем случайно)
        device_type = random.choice(["mobile", "desktop"])
        device_errors = self.common_errors["device"].get(device_type, self.common_errors["device"]["desktop"])

        # Объединяем профили ошибок с приоритетом образовательных
        error_profile = {}
        error_profile.update(age_errors)
        error_profile.update(device_errors)
        # Образовательные ошибки имеют приоритет, так как более существенно влияют
        error_profile.update(edu_errors)

        profile["error_profile"] = error_profile
        profile["device_type"] = device_type

        # Общий уровень ошибок (0-1) - зависит от образования и возраста
        education_factor = {
            "Начальное образование": 0.8,
            "Среднее образование": 0.6,
            "Среднее специальное": 0.5,
            "Высшее": 0.3,
            "Ученая степень": 0.2
        }.get(edu_type, 0.5)

        # Возрастной фактор - U-образная кривая (больше у молодых и пожилых)
        if age_group in ["18-25", "66-80"]:
            age_factor = 0.6
        elif age_group in ["26-35", "51-65"]:
            age_factor = 0.4
        else:
            age_factor = 0.3

        # Вычисляем общий уровень ошибок с приоритетом образования
        total_error_level = (education_factor * 0.7 + age_factor * 0.3) * random.uniform(0.8, 1.2)
        profile["total_error_level"] = max(0.1, min(0.9, total_error_level))

        return profile

    def apply_linguistic_profile_to_prompt(self, prompt: str, linguistic_profile: Dict) -> str:
        """
        Добавление инструкций по лингвистическому профилю в промпт

        Args:
            prompt: Исходный промпт
            linguistic_profile: Словарь с лингвистическим профилем

        Returns:
            Модифицированный промпт
        """
        # Извлекаем данные из профиля
        region = linguistic_profile.get("region", "Москва")
        age_group = linguistic_profile.get("age_group", "36-50")
        regional_words = linguistic_profile.get("regional_words", [])
        regional_expressions = linguistic_profile.get("regional_expressions", [])
        filler_words = linguistic_profile.get("filler_words", [])
        financial_slang = linguistic_profile.get("financial_slang", [])
        general_slang = linguistic_profile.get("general_slang", [])
        error_profile = linguistic_profile.get("error_profile", {})
        total_error_level = linguistic_profile.get("total_error_level", 0.3)
        device_type = linguistic_profile.get("device_type", "desktop")

        # Формируем инструкцию по применению регионализмов
        regionalism_instruction = ""
        if regional_words or regional_expressions:
            regionalism_instruction = f"""
РЕГИОНАЛЬНЫЕ ОСОБЕННОСТИ РЕЧИ (Регион: {region}):
- Можешь иногда использовать региональные слова: {', '.join(random.sample(regional_words, k=min(3, len(regional_words))))}
- Можешь использовать региональные выражения: {', '.join(random.sample(regional_expressions, k=min(2, len(regional_expressions))))}
"""

        # Формируем инструкцию по словам-паразитам
        fillers_instruction = ""
        if filler_words:
            # Определяем рекомендуемую частоту использования
            filler_frequency = "часто" if total_error_level > 0.6 else "иногда" if total_error_level > 0.3 else "редко"
            fillers_instruction = f"""
СЛОВА-ПАРАЗИТЫ (Возрастная группа: {age_group}):
- {filler_frequency} используй слова-паразиты: {', '.join(random.sample(filler_words, k=min(4, len(filler_words))))}
"""

        # Формируем инструкцию по сленгу
        slang_instruction = ""
        if financial_slang or general_slang:
            slang_frequency = "часто" if age_group in ["18-25", "26-35"] else "иногда" if age_group == "36-50" else "редко"
            slang_samples = []
            if financial_slang:
                slang_samples.append(f"финансовый сленг: {', '.join(random.sample(financial_slang, k=min(3, len(financial_slang))))}")
            if general_slang:
                slang_samples.append(f"общий сленг: {', '.join(random.sample(general_slang, k=min(3, len(general_slang))))}")

            slang_instruction = f"""
ПОКОЛЕНЧЕСКИЙ СЛЕНГ (Возрастная группа: {age_group}):
- {slang_frequency} используй {" и ".join(slang_samples)}
"""

        # Формируем инструкцию по ошибкам и опечаткам
        errors_instruction = ""
        if error_profile:
            # Определяем рекомендации по ошибкам на основе общего уровня
            if total_error_level > 0.7:
                error_description = "много разных ошибок и опечаток"
            elif total_error_level > 0.4:
                error_description = "умеренное количество ошибок и опечаток"
            else:
                error_description = "редкие ошибки и опечатки"

            # Собираем конкретные типы ошибок
            error_types = []
            for error_type, probability in error_profile.items():
                if probability > 0.5:
                    if error_type == "punctuation_omission":
                        error_types.append("пропуск знаков препинания")
                    elif error_type == "abbreviations":
                        error_types.append("сокращения слов")
                    elif error_type == "letter_repetition":
                        error_types.append("повторение букв для эмфазы")
                    elif error_type == "typos":
                        error_types.append("опечатки")
                    elif error_type == "caps_lock":
                        error_types.append("капс в некоторых словах")
                    elif error_type == "punctuation_excess":
                        error_types.append("избыток знаков препинания")
                    elif error_type == "grammar_errors":
                        error_types.append("грамматические ошибки")
                    elif error_type == "spelling_errors":
                        error_types.append("орфографические ошибки")

            # Если есть конкретные типы ошибок, перечисляем их
            error_specifics = f"Особенно: {', '.join(error_types)}" if error_types else ""

            # Длина ответа в зависимости от устройства
            length_advice = "Пиши короче (как с телефона)" if device_type == "mobile" else "Можешь писать подробнее (как с компьютера)"

            errors_instruction = f"""
ОСОБЕННОСТИ ПИСЬМА:
- Используй {error_description}. {error_specifics}
- {length_advice}
- Общий уровень ошибок: {total_error_level:.1f} (где 0 - без ошибок, 1 - много ошибок)
"""

        # Собираем все инструкции
        linguistic_instructions = ""
        if regionalism_instruction or fillers_instruction or slang_instruction or errors_instruction:
            linguistic_instructions = f"""
ЛИНГВИСТИЧЕСКИЕ ОСОБЕННОСТИ:
{regionalism_instruction}
{fillers_instruction}
{slang_instruction}
{errors_instruction}
"""

        # Добавляем инструкции в промпт
        if "ОБЩИЕ ПРАВИЛА ОТВЕТА" in prompt:
            prompt = prompt.replace("ОБЩИЕ ПРАВИЛА ОТВЕТА", f"{linguistic_instructions}\nОБЩИЕ ПРАВИЛА ОТВЕТА")
        else:
            prompt += f"\n{linguistic_instructions}"

        return prompt


class LifeContextFactors:
    """Класс для моделирования жизненного контекста и событий, влияющих на финансовое поведение"""

    def __init__(self):
        """Инициализация моделей жизненного контекста"""
        # Жизненные события, влияющие на финансы
        self.life_events = {
            "свадьба": {
                "description": "Недавняя свадьба или подготовка к ней",
                "financial_impact": "Крупные расходы, возможно общий бюджет с партнером, изменение финансовых приоритетов",
                "relevant_topics": ["накопления", "кредиты", "планирование", "страхование"],
                "age_relevance": {"min": 18, "max": 65, "peak": [25, 35]},
                "family_status_relevance": ["Холост/Не замужем", "В отношениях", "Гражданский брак"]
            },
            "рождение_ребенка": {
                "description": "Недавнее рождение ребенка или ожидание рождения",
                "financial_impact": "Увеличение расходов, декретный отпуск, изменение бюджета, долгосрочное планирование",
                "relevant_topics": ["накопления", "страхование", "детские вклады", "ипотека", "материнский капитал"],
                "age_relevance": {"min": 20, "max": 45, "peak": [25, 35]},
                "family_status_relevance": ["Женат/Замужем", "Гражданский брак"]
            },
            "потеря_работы": {
                "description": "Недавняя потеря работы или риск ее потери",
                "financial_impact": "Снижение доходов, использование сбережений, поиск подработок, возможное реструктурирование кредитов",
                "relevant_topics": ["накопления", "кредиты", "рефинансирование", "социальные выплаты"],
                "age_relevance": {"min": 18, "max": 65, "peak": [30, 50]},
                "family_status_relevance": None  # релевантно для всех
            },
            "переезд": {
                "description": "Недавний переезд или планирование переезда в другой город/страну",
                "financial_impact": "Крупные расходы, изменение стоимости жизни, смена банков, вопросы с переводом денег",
                "relevant_topics": ["накопления", "ипотека", "переводы", "валюта"],
                "age_relevance": {"min": 18, "max": 45, "peak": [22, 35]},
                "family_status_relevance": None  # релевантно для всех
            },
            "получение_наследства": {
                "description": "Недавнее получение наследства или ожидание его получения",
                "financial_impact": "Увеличение капитала, вопросы инвестирования, налоговые вопросы",
                "relevant_topics": ["инвестиции", "налоги", "недвижимость", "вклады"],
                "age_relevance": {"min": 30, "max": 80, "peak": [40, 60]},
                "family_status_relevance": None  # релевантно для всех
            },
            "развод": {
                "description": "Недавний развод или процесс развода",
                "financial_impact": "Раздел имущества, изменение финансовых обязательств, отдельный бюджет, алименты",
                "relevant_topics": ["раздел имущества", "алименты", "кредиты", "ипотека"],
                "age_relevance": {"min": 25, "max": 60, "peak": [30, 45]},
                "family_status_relevance": ["Разведен/Разведена"]
            },
            "покупка_жилья": {
                "description": "Недавняя покупка жилья или активный поиск для покупки",
                "financial_impact": "Крупные расходы, ипотека, вопросы страхования жилья, коммунальные платежи",
                "relevant_topics": ["ипотека", "страхование", "налоги", "кредиты", "накопления"],
                "age_relevance": {"min": 25, "max": 60, "peak": [30, 45]},
                "family_status_relevance": None  # релевантно для всех
            },
            "старт_бизнеса": {
                "description": "Недавний старт собственного бизнеса или подготовка к нему",
                "financial_impact": "Инвестиции в бизнес, бизнес-кредиты, изменение структуры доходов и расходов",
                "relevant_topics": ["бизнес-кредиты", "инвестиции", "налоги", "расчетный счет"],
                "age_relevance": {"min": 25, "max": 55, "peak": [30, 45]},
                "family_status_relevance": None  # релевантно для всех
            },
            "болезнь": {
                "description": "Серьезное заболевание у себя или члена семьи",
                "financial_impact": "Расходы на лечение, потеря трудоспособности, вопросы страхования",
                "relevant_topics": ["медицинское страхование", "накопления", "кредиты", "социальные выплаты"],
                "age_relevance": {"min": 30, "max": 80, "peak": [50, 70]},
                "family_status_relevance": None  # релевантно для всех
            },
            "выход_на_пенсию": {
                "description": "Недавний выход на пенсию или подготовка к нему",
                "financial_impact": "Изменение структуры доходов, использование пенсионных накоплений, консервативный подход к инвестициям",
                "relevant_topics": ["пенсия", "накопления", "инвестиции", "социальные выплаты"],
                "age_relevance": {"min": 50, "max": 80, "peak": [55, 65]},
                "family_status_relevance": None  # релевантно для всех
            }
        }

        # Сезонные факторы, влияющие на финансы
        self.seasonal_factors = {
            "новый_год": {
                "description": "Период перед новогодними праздниками",
                "months": [11, 12],  # ноябрь-декабрь
                "financial_impact": "Увеличение трат на подарки и праздники, премии, планирование бюджета на следующий год",
                "relevant_topics": ["кредиты", "накопления", "акции", "бонусы", "скидки"]
            },
            "лето_отпуск": {
                "description": "Летний период отпусков",
                "months": [5, 6, 7, 8],  # май-август
                "financial_impact": "Траты на отпуск, путешествия, детский отдых, подготовка к школе в конце сезона",
                "relevant_topics": ["накопления", "карты", "валюта", "мобильный банк", "страхование"]
            },
            "черная_пятница": {
                "description": "Период распродаж 'Черная пятница'",
                "months": [11],  # ноябрь
                "financial_impact": "Увеличение импульсивных покупок, охота за скидками, возможность приобрести запланированные покупки дешевле",
                "relevant_topics": ["кредитные карты", "рассрочка", "кэшбэк", "акции", "бонусы"]
            },
            "начало_учебного_года": {
                "description": "Подготовка к учебному году",
                "months": [7, 8],  # июль-август
                "financial_impact": "Траты на подготовку детей к школе/вузу, оплата обучения, покупка техники и принадлежностей",
                "relevant_topics": ["накопления", "кредиты", "рассрочка", "образовательные кредиты"]
            },
            "отопительный_сезон": {
                "description": "Начало отопительного сезона",
                "months": [9, 10],  # сентябрь-октябрь
                "financial_impact": "Увеличение коммунальных платежей, возможная задолженность",
                "relevant_topics": ["коммунальные платежи", "субсидии", "автоплатежи"]
            },
            "дачный_сезон": {
                "description": "Дачный/садовый сезон",
                "months": [4, 5, 6, 7, 8, 9],  # апрель-сентябрь
                "financial_impact": "Траты на дачу/сад, сезонные работы, заготовки",
                "relevant_topics": ["накопления", "кредиты на строительство/ремонт", "страхование имущества"]
            },
            "налоговый_период": {
                "description": "Период уплаты налогов",
                "months": [10, 11],  # октябрь-ноябрь
                "financial_impact": "Уплата имущественных налогов, подача деклараций, налоговые вычеты",
                "relevant_topics": ["налоги", "налоговые вычеты", "страхование", "инвестиции"]
            }
        }

        # Текущая экономическая ситуация (обновляется извне)
        self.current_economic_situation = {
            "инфляция": {
                "level": "высокая",  # высокая/умеренная/низкая
                "description": "Высокий уровень инфляции влияет на стоимость товаров и услуг, обесценивает накопления без процентов",
                "financial_impact": "Поиск способов сохранения сбережений, инвестиции для защиты от инфляции"
            },
            "ключевая_ставка": {
                "level": "повышенная",  # повышенная/сниженная/стабильная
                "description": "Центральный банк поддерживает повышенную ключевую ставку",
                "financial_impact": "Высокие ставки по вкладам и кредитам, выгодность сбережений, дорогие кредиты"
            },
            "курс_валют": {
                "level": "нестабильный",  # растущий/падающий/стабильный/нестабильный
                "description": "Курс валют подвержен частым колебаниям",
                "financial_impact": "Риски при валютных операциях, вопросы сохранения сбережений в разных валютах"
            },
            "кредитная_доступность": {
                "level": "умеренная",  # высокая/умеренная/низкая
                "description": "Банки умеренно строги при выдаче кредитов, требуют хорошую кредитную историю",
                "financial_impact": "Более тщательная проверка заемщиков, потребность в хорошей кредитной истории"
            }
        }

        # Культурные особенности отношений к деньгам в разных поколениях
        self.generational_money_attitudes = {
            "18-25": {  # Поколение Z
                "key_values": ["Цифровая нативность", "Экологичность", "Индивидуализм", "Стартапы", "Фриланс"],
                "money_attitudes": [
                    "Предпочтение цифровых финансовых инструментов",
                    "Открытость к новым финансовым технологиям и криптовалютам",
                    "Стремление к пассивному доходу и финансовой независимости с ранних лет",
                    "Скептицизм к традиционным финансовым институтам",
                    "Приоритет финансовой свободы и опыта над материальными ценностями",
                    "Готовность инвестировать в экологичные/этичные проекты",
                    "Стремление к ранним инвестициям даже с небольшими суммами"
                ]
            },
            "26-35": {  # Миллениалы
                "key_values": ["Баланс работы и жизни", "Опыт vs Вещи", "Социальные сети", "Аренда vs Покупка"],
                "money_attitudes": [
                    "Высокая закредитованность, особенно образовательные кредиты",
                    "Откладывание крупных покупок (жилье, автомобиль) на более поздний срок",
                    "Предпочтение кредитных карт с бонусами/кешбэком",
                    "Готовность платить за уникальный опыт и впечатления",
                    "Ориентация на множественные источники дохода",
                    "Интерес к цифровым инвестициям и финтех-сервисам",
                    "Относительная финансовая грамотность при менее стабильной карьере"
                ]
            },
            "36-50": {  # Поколение X
                "key_values": ["Стабильность", "Карьера", "Семья", "Независимость"],
                "money_attitudes": [
                    "Серьезное отношение к финансовому планированию",
                    "Более традиционный подход к инвестициям (недвижимость, банки)",
                    "Сочетание цифровых и традиционных финансовых инструментов",
                    "Акцент на образовании детей и пенсионных накоплениях",
                    "Склонность к умеренному риску в инвестициях",
                    "Более высокая стоимость активов, но и больше финансовых обязательств",
                    "Стремление к финансовой независимости"
                ]
            },
            "51-65": {  # Бумеры
                "key_values": ["Стабильная карьера", "Материальное благополучие", "Отложенная награда"],
                "money_attitudes": [
                    "Осторожное отношение к кредитам и долгам",
                    "Предпочтение традиционных финансовых институтов (банки, брокеры)",
                    "Консервативный подход к инвестициям, ориентация на безопасность",
                    "Накопления для выхода на пенсию как важный приоритет",
                    "Ценность материальных активов (недвижимость, автомобили)",
                    "Меньший интерес к цифровым финансовым инструментам",
                    "Склонность хранить наличные 'на черный день'"
                ]
            },
            "66-80": {  # Старшее поколение
                "key_values": ["Экономность", "Традиции", "Стабильность", "Планирование"],
                "money_attitudes": [
                    "Высокое недоверие к финансовым институтам из-за исторического опыта",
                    "Предпочтение хранить сбережения 'под матрасом' или в виде материальных ценностей",
                    "Минимальное использование кредитов, ориентация на жизнь по средствам",
                    "Скептицизм к новым финансовым инструментам и цифровым технологиям",
                    "Приоритет финансовой безопасности над доходностью",
                    "Готовность помогать детям и внукам финансово",
                    "Режим экономии как устоявшаяся привычка"
                ]
            }
        }

        # Семейные финансовые традиции
        self.family_financial_traditions = {
            "традиционная_модель": {
                "description": "Традиционное распределение финансовых ролей в семье",
                "patterns": [
                    "Мужчина - основной добытчик, женщина распоряжается семейным бюджетом",
                    "Общий бюджет, совместное принятие крупных финансовых решений",
                    "Откладывание денег 'на черный день' как обязательная практика",
                    "Стремление избегать кредитов, жить по средствам",
                    "Стремление к покупке недвижимости как основы благосостояния"
                ]
            },
            "современная_модель": {
                "description": "Современное распределение финансовых ролей в семье",
                "patterns": [
                    "Равное участие партнеров в формировании бюджета",
                    "Раздельные и общие счета одновременно (личные расходы и общие траты)",
                    "Плановые инвестиции и осознанное использование кредитных продуктов",
                    "Долгосрочное финансовое планирование с использованием цифровых инструментов",
                    "Более гибкий подход к крупным приобретениям (могут предпочесть аренду покупке)"
                ]
            },
            "партнерская_модель": {
                "description": "Полностью раздельный подход к финансам в партнерстве",
                "patterns": [
                    "Полностью раздельные бюджеты, счета и финансовые решения",
                    "Пропорциональное или равное разделение общих расходов",
                    "Сохранение финансовой независимости каждого партнера",
                    "Формальные договоренности о совместном имуществе",
                    "Индивидуальные финансовые цели наряду с общими"
                ]
            },
            "расширенная_семья": {
                "description": "Финансовые отношения в расширенной семье (с участием старшего поколения)",
                "patterns": [
                    "Финансовая поддержка старшего поколения (родителей)",
                    "Финансовая помощь от старшего поколения (в крупных приобретениях)",
                    "Общие семейные активы и предприятия",
                    "Советы и финансовый опыт передаются от старших к младшим",
                    "Взаимная финансовая поддержка в кризисные периоды",
                    "Приоритет благосостояния всей семьи над личными финансовыми целями"
                ]
            }
        }

        # Специфические финансовые практики в России
        self.specific_financial_practices = {
            "национальные_особенности": [
                "Хранение сбережений в разных валютах для диверсификации",
                "Предпочтение наличных для ежедневных расходов и 'заначек'",
                "Инвестиции в недвижимость как основной способ сохранения капитала",
                "Культура одалживания денег у родственников и друзей вместо микрозаймов",
                "Практика 'занять до зарплаты' среди близких",
                "Традиция создания 'кубышки на черный день'",
                "Приоритет трат на образование детей над личными накоплениями",
                "Выбор банка по совету знакомых или 'где получают зарплату'",
                "Активное использование социальных льгот и налоговых вычетов",
                "Высокая чувствительность к банковским/валютным кризисам из-за исторического опыта"
            ],
            "региональные_особенности": {
                "Москва": [
                    "Активное использование инвестиционных инструментов",
                    "Высокая закредитованность для поддержания статуса",
                    "Привычка к безналичной оплате и цифровым сервисам",
                    "Финансовое планирование с учетом высокой стоимости жизни"
                ],
                "Санкт-Петербург": [
                    "Баланс между современными финансовыми инструментами и традиционными подходами",
                    "Более экономный подход по сравнению с Москвой при схожем уровне финансовой грамотности",
                    "Популярность банковских услуг с кэшбэком за культурные мероприятия"
                ],
                "Регионы": [
                    "Более консервативное отношение к финансовым инструментам",
                    "Меньшее проникновение цифровых финансовых сервисов",
                    "Более выраженная практика самообеспечения (подсобное хозяйство, заготовки)",
                    "Выше доля наличных расчетов и 'серых' доходов",
                    "Большее значение имеют социальные выплаты и льготы"
                ]
            },
            "возрастные_особенности": {
                "Молодежь": [
                    "Активное использование кешбэк-сервисов и бонусных программ",
                    "Интерес к инвестициям в криптовалюты и стартапы",
                    "Приоритет мобильности и впечатлений над накоплениями",
                    "Активное привлечение кредитов на образование и развитие"
                ],
                "Среднее поколение": [
                    "Балансирование между помощью родителям и вложениями в детей",
                    "Активное использование ипотечных продуктов",
                    "Формирование накоплений 'на пенсию' из-за недоверия к пенсионной системе",
                    "Диверсификация доходов через подработки и инвестиции"
                ],
                "Старшее поколение": [
                    "Хранение наличных дома и в банковских ячейках",
                    "Недоверие к банковской системе из-за опыта дефолтов",
                    "Минимизация использования цифровых финансовых услуг",
                    "Финансовая помощь детям и внукам как приоритет"
                ]
            }
        }

        # Модели социальной желательности в финансовых вопросах
        self.social_desirability_patterns = {
            "завышение_доходов": {
                "description": "Тенденция завышать свои доходы в разговоре",
                "examples": [
                    "Округление зарплаты вверх",
                    "Включение нерегулярных премий/бонусов в 'обычный доход'",
                    "Упоминание 'прошлых высоких доходов' как актуальных",
                    "Преувеличение размера инвестиций или их доходности"
                ]
            },
            "сокрытие_долгов": {
                "description": "Тенденция скрывать или преуменьшать долги",
                "examples": [
                    "Упоминание только одного кредита при наличии нескольких",
                    "Называние кредита 'временной мерой' вне зависимости от ситуации",
                    "Оправдание кредитов 'выгодными условиями' даже при высоких ставках",
                    "Преуменьшение суммы долга или срока кредита"
                ]
            },
            "демонстрация_финансовой_грамотности": {
                "description": "Стремление показать более высокий уровень финансовой грамотности",
                "examples": [
                    "Использование профессиональных терминов без полного понимания их значения",
                    "Утверждение об активном инвестировании при наличии лишь минимальных сбережений",
                    "Заявления о строгом финансовом планировании без фактической его реализации",
                    "Упоминание сложных финансовых инструментов для произведения впечатления"
                ]
            },
            "рационализация_импульсивных_трат": {
                "description": "Представление импульсивных трат как рациональных решений",
                "examples": [
                    "Объяснение дорогих покупок как 'инвестиций в качество'",
                    "Оправдание незапланированных трат 'уникальной возможностью' или 'огромной скидкой'",
                    "Представление эмоциональных покупок как 'заботы о себе' или 'заслуженной награды'",
                    "Преуменьшение частоты и объема импульсивных трат"
                ]
            },
            "скрытие_финансовой_помощи": {
                "description": "Сокрытие получаемой финансовой помощи от родителей/партнера",
                "examples": [
                    "Представление подарков от родителей как заработанных средств",
                    "Умалчивание о том, что родители помогли с первоначальным взносом по ипотеке",
                    "Приписывание себе единоличной оплаты крупных покупок при фактическом софинансировании",
                    "Представление помощи как 'временного возвратного займа'"
                ]
            },
            "преувеличение_финансовой_независимости": {
                "description": "Преувеличение степени своей финансовой независимости и успешности",
                "examples": [
                    "Заявления о полной финансовой независимости при фактической поддержке от родителей/партнера",
                    "Преувеличение своей роли в семейных финансовых решениях",
                    "Создание образа финансово успешного человека при наличии значительных долгов",
                    "Утверждения о том, что 'деньги не главное' при фактическом стремлении к высоким доходам"
                ]
            }
        }

    def get_age_group(self, age: int) -> str:
        """Определение возрастной группы по возрасту"""
        if age <= 25:
            return "18-25"
        elif age <= 35:
            return "26-35"
        elif age <= 50:
            return "36-50"
        elif age <= 65:
            return "51-65"
        else:
            return "66-80"

    def get_region_type(self, region: str) -> str:
        """Определение типа региона"""
        if region in ["Москва"]:
            return "Москва"
        elif region in ["Санкт-Петербург"]:
            return "Санкт-Петербург"
        else:
            return "Регионы"

    def get_relevant_life_events(self, persona: Dict) -> List[Dict]:
        """
        Определение релевантных жизненных событий для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Список словарей с релевантными жизненными событиями
        """
        age = persona.get('Возраст', 30)
        family_status = persona.get('Семейное положение', 'Не указано')

        # Вычисляем вероятность каждого жизненного события
        event_probabilities = {}

        for event_name, event_info in self.life_events.items():
            probability = 0.0

            # Возрастная релевантность
            age_range = event_info.get("age_relevance", {"min": 18, "max": 80, "peak": [30, 40]})

            # Базовая вероятность на основе возраста
            if age < age_range["min"] or age > age_range["max"]:
                # За пределами возрастного диапазона
                probability = 0.05
            else:
                # Внутри возрастного диапазона
                peak_min, peak_max = age_range["peak"]

                if peak_min <= age <= peak_max:
                    # В пиковом возрасте - высокая вероятность
                    probability = 0.6
                elif age < peak_min:
                    # До пикового возраста - растущая вероятность
                    probability = 0.3 + (0.3 * (age - age_range["min"]) / (peak_min - age_range["min"]))
                else:  # age > peak_max
                    # После пикового возраста - убывающая вероятность
                    probability = 0.3 + (0.3 * (age_range["max"] - age) / (age_range["max"] - peak_max))

            # Корректировка на основе семейного положения
            if event_info.get("family_status_relevance"):
                if family_status in event_info["family_status_relevance"]:
                    probability *= 2.0  # Увеличиваем вероятность для релевантного семейного положения
                else:
                    probability *= 0.5  # Уменьшаем для нерелевантного

            # Конкретные корректировки для разных событий
            if event_name == "свадьба" and "Женат" in family_status:
                probability = 0  # Исключаем для уже женатых/замужних

            if event_name == "рождение_ребенка":
                # Корректируем с учетом количества детей
                children = persona.get('Количество детей', 0)
                if children >= 3:
                    probability *= 0.2  # Существенно снижаем вероятность для многодетных
                elif children >= 1:
                    probability *= 0.7  # Немного снижаем для уже имеющих детей

            if event_name == "развод" and "Разведен" not in family_status and "Женат" not in family_status:
                probability = 0  # Исключаем для неженатых/незамужних

            # Сохраняем итоговую вероятность
            event_probabilities[event_name] = min(1.0, max(0.0, probability))

        # Определяем, какие события произошли, на основе вероятностей
        active_events = []

        for event_name, probability in event_probabilities.items():
            # С определенной вероятностью считаем событие активным
            if random.random() < probability:
                active_events.append({
                    "name": event_name,
                    "description": self.life_events[event_name]["description"],
                    "financial_impact": self.life_events[event_name]["financial_impact"],
                    "relevance": probability  # Сохраняем для оценки относительной важности
                })

        # Ограничиваем количество активных событий для реалистичности
        # Не более 2-3 значимых жизненных событий одновременно
        if len(active_events) > 3:
            # Сортируем по релевантности и берем топ-3
            active_events.sort(key=lambda x: x["relevance"], reverse=True)
            active_events = active_events[:3]

        return active_events

    def get_current_seasonal_factors(self) -> List[Dict]:
        """
        Определение текущих сезонных факторов

        Returns:
            Список словарей с текущими сезонными факторами
        """
        # Получаем текущий месяц (1-12)
        current_month = datetime.now().month

        # Определяем активные сезонные факторы
        active_factors = []

        for factor_name, factor_info in self.seasonal_factors.items():
            if current_month in factor_info.get("months", []):
                # Месяц соответствует сезонному фактору
                active_factors.append({
                    "name": factor_name,
                    "description": factor_info["description"],
                    "financial_impact": factor_info["financial_impact"],
                    "relevant_topics": factor_info.get("relevant_topics", [])
                })

        return active_factors

    def get_generational_money_attitudes(self, persona: Dict) -> Dict:
        """
        Получение характерных для поколения отношений к деньгам

        Args:
            persona: Словарь с данными персоны

        Returns:
            Словарь с отношением к деньгам для поколения
        """
        age = persona.get('Возраст', 30)
        age_group = self.get_age_group(age)

        return self.generational_money_attitudes.get(age_group, self.generational_money_attitudes["36-50"])

    def get_family_financial_tradition(self, persona: Dict) -> Dict:
        """
        Определение семейной финансовой традиции для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Словарь с семейной финансовой традицией
        """
        age = persona.get('Возраст', 30)
        family_status = persona.get('Семейное положение', 'Не указано')

        # Определяем вероятности различных моделей на основе возраста и семейного положения
        probabilities = {
            "традиционная_модель": 0.25,
            "современная_модель": 0.4,
            "партнерская_модель": 0.25,
            "расширенная_семья": 0.1
        }

        # Корректируем вероятности в зависимости от возраста
        age_group = self.get_age_group(age)

        if age_group in ["18-25", "26-35"]:
            # Молодое поколение более склонно к современным и партнерским моделям
            probabilities["традиционная_модель"] -= 0.15
            probabilities["современная_модель"] += 0.1
            probabilities["партнерская_модель"] += 0.1
            probabilities["расширенная_семья"] -= 0.05
        elif age_group in ["51-65", "66-80"]:
            # Старшее поколение более склонно к традиционным и расширенным моделям
            probabilities["традиционная_модель"] += 0.2
            probabilities["современная_модель"] -= 0.1
            probabilities["партнерская_модель"] -= 0.15
            probabilities["расширенная_семья"] += 0.05

        # Корректируем вероятности в зависимости от семейного положения
        if "Женат" in family_status or "Замужем" in family_status:
            # Женатые люди чаще следуют традиционной или современной модели
            probabilities["традиционная_модель"] += 0.1
            probabilities["современная_модель"] += 0.1
            probabilities["партнерская_модель"] -= 0.1
            probabilities["расширенная_семья"] -= 0.1
        elif "Гражданский брак" in family_status:
            # Люди в гражданском браке часто предпочитают партнерскую модель
            probabilities["традиционная_модель"] -= 0.15
            probabilities["современная_модель"] += 0.05
            probabilities["партнерская_модель"] += 0.15
            probabilities["расширенная_семья"] -= 0.05
        elif "Разведен" in family_status or "Вдов" in family_status:
            # Разведенные или овдовевшие могут быть частью расширенной семьи
            probabilities["расширенная_семья"] += 0.2
            probabilities["традиционная_модель"] -= 0.1
            probabilities["современная_модель"] -= 0.05
            probabilities["партнерская_модель"] -= 0.05

        # Нормализуем вероятности
        total = sum(probabilities.values())
        normalized_probabilities = {k: v/total for k, v in probabilities.items()}

        # Выбираем модель на основе вероятностей
        models = list(normalized_probabilities.keys())
        weights = list(normalized_probabilities.values())
        selected_model = random.choices(models, weights=weights, k=1)[0]

        return {
            "model": selected_model,
            "description": self.family_financial_traditions[selected_model]["description"],
            "patterns": self.family_financial_traditions[selected_model]["patterns"]
        }

    def get_specific_financial_practices(self, persona: Dict) -> Dict:
        """
        Получение специфических финансовых практик для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Словарь со специфическими финансовыми практиками
        """
        age = persona.get('Возраст', 30)
        region = persona.get('Регион', 'Москва')

        age_group = self.get_age_group(age)
        region_type = self.get_region_type(region)

        # Определяем, какие национальные особенности актуальны (выбираем случайные)
        national_practices = random.sample(
            self.specific_financial_practices["национальные_особенности"],
            k=min(3, len(self.specific_financial_practices["национальные_особенности"]))
        )

        # Определяем возрастные особенности
        if age_group in ["18-25", "26-35"]:
            age_category = "Молодежь"
        elif age_group in ["36-50", "51-65"]:
            age_category = "Среднее поколение"
        else:
            age_category = "Старшее поколение"

        age_practices = self.specific_financial_practices["возрастные_особенности"].get(age_category, [])
        age_practices = random.sample(age_practices, k=min(2, len(age_practices)))

        # Определяем региональные особенности
        regional_practices = self.specific_financial_practices["региональные_особенности"].get(region_type, [])
        regional_practices = random.sample(regional_practices, k=min(2, len(regional_practices)))

        return {
            "national": national_practices,
            "regional": regional_practices,
            "age_specific": age_practices
        }

    def get_social_desirability_biases(self, persona: Dict) -> List[Dict]:
        """
        Определение склонностей к социально желательным ответам для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Список словарей с патернами социальной желательности
        """
        age = persona.get('Возраст', 30)
        income = persona.get('Доход', 'Не указано')
        literacy_level = persona.get('Финансовый профиль', {}).get('Уровень финансовой грамотности', 'средний')

        # Базовая склонность к социально желательным ответам (0-1)
        base_probability = 0.5

        # Корректируем на основе возраста (U-образная зависимость)
        age_factor = 0.0
        if age < 25:
            # Молодые люди могут завышать свой статус
            age_factor = 0.2
        elif age > 60:
            # Пожилые люди могут приукрашивать прошлое или скрывать финансовые трудности
            age_factor = 0.15

        # Корректируем на основе дохода
        income_factor = 0.0
        low_income = ["Менее 15 000 ₽", "15 000 - 30 000 ₽", "30 000 - 60 000 ₽"]
        high_income = ["150 000 - 250 000 ₽", "250 000 - 500 000 ₽", "Более 500 000 ₽"]

        if income in low_income:
            # Люди с низким доходом могут его завышать
            income_factor = 0.2
        elif income in high_income:
            # Люди с высоким доходом могут скрывать детали расходов
            income_factor = 0.1

        # Корректируем на основе финансовой грамотности
        literacy_factor = 0.0
        if literacy_level in ["отсутствие знаний", "начинающий"]:
            # Люди с низкой грамотностью могут демонстрировать ложную уверенность
            literacy_factor = 0.15
        elif literacy_level == "продвинутый":
            # Люди с высокой грамотностью могут преувеличивать свои знания
            literacy_factor = 0.1

        # Итоговая вероятность
        social_desirability_probability = base_probability + age_factor + income_factor + literacy_factor
        social_desirability_probability = min(0.95, max(0.1, social_desirability_probability))

        # Выбираем паттерны социальной желательности
        selected_patterns = []

        for pattern_name, pattern_info in self.social_desirability_patterns.items():
            # Для каждого паттерна определяем, будет ли он применяться
            if random.random() < social_desirability_probability * 0.7:  # Немного снижаем для реалистичности
                # Выбираем примеры проявления паттерна
                examples = random.sample(
                    pattern_info["examples"],
                    k=min(2, len(pattern_info["examples"]))
                )

                selected_patterns.append({
                    "name": pattern_name,
                    "description": pattern_info["description"],
                    "examples": examples,
                    "strength": random.uniform(0.3, 0.8)  # Сила проявления
                })

        # Ограничиваем количество паттернов для реалистичности
        if len(selected_patterns) > 3:
            selected_patterns = random.sample(selected_patterns, k=3)

        return selected_patterns

    def apply_life_context_to_prompt(self, prompt: str, persona: Dict, question: Dict = None) -> str:
        """
        Добавление информации о жизненном контексте в промпт

        Args:
            prompt: Исходный промпт
            persona: Словарь с данными персоны
            question: Словарь с вопросом (опционально)

        Returns:
            Модифицированный промпт
        """
        # Определяем жизненные события
        life_events = self.get_relevant_life_events(persona)

        # Определяем сезонные факторы
        seasonal_factors = self.get_current_seasonal_factors()

        # Определяем культурные отношения к деньгам в зависимости от поколения
        generational_attitudes = self.get_generational_money_attitudes(persona)

        # Определяем семейную финансовую традицию
        family_tradition = self.get_family_financial_tradition(persona)

        # Определяем специфические финансовые практики
        specific_practices = self.get_specific_financial_practices(persona)

        # Определяем паттерны социальной желательности
        social_desirability = self.get_social_desirability_biases(persona)

        # Формируем блок с жизненным контекстом для промпта
        life_context_block = "\nЖИЗНЕННЫЙ КОНТЕКСТ И ФИНАНСОВЫЕ ОСОБЕННОСТИ:"

        # Добавляем информацию о жизненных событиях
        if life_events:
            life_context_block += "\n\nЖИЗНЕННЫЕ СОБЫТИЯ, влияющие на финансовое поведение:"
            for event in life_events:
                life_context_block += f"\n- {event['description']}: {event['financial_impact']}"

        # Добавляем информацию о сезонных факторах
        if seasonal_factors:
            life_context_block += "\n\nСЕЗОННЫЕ ФАКТОРЫ, влияющие на финансовое поведение:"
            for factor in seasonal_factors:
                life_context_block += f"\n- {factor['description']}: {factor['financial_impact']}"

        # Добавляем информацию о текущей экономической ситуации
        if self.current_economic_situation:
            life_context_block += "\n\nЭКОНОМИЧЕСКАЯ СИТУАЦИЯ:"
            for key, info in self.current_economic_situation.items():
                life_context_block += f"\n- {key.replace('_', ' ').capitalize()}: {info['level']} - {info['financial_impact']}"

        # Добавляем информацию о поколенческих отношениях к деньгам
        if generational_attitudes:
            age_group = self.get_age_group(persona.get('Возраст', 30))
            life_context_block += f"\n\nПОКОЛЕНЧЕСКИЕ ОСОБЕННОСТИ (группа {age_group} лет):"
            attitudes = random.sample(generational_attitudes.get("money_attitudes", []), k=min(3, len(generational_attitudes.get("money_attitudes", []))))
            for attitude in attitudes:
                life_context_block += f"\n- {attitude}"

        # Добавляем информацию о семейных финансовых традициях
        if family_tradition:
            life_context_block += f"\n\nСЕМЕЙНАЯ ФИНАНСОВАЯ МОДЕЛЬ: {family_tradition['description']}"
            patterns = random.sample(family_tradition['patterns'], k=min(2, len(family_tradition['patterns'])))
            for pattern in patterns:
                life_context_block += f"\n- {pattern}"

        # Добавляем информацию о специфических финансовых практиках
        if specific_practices:
            life_context_block += "\n\nСПЕЦИФИЧЕСКИЕ ФИНАНСОВЫЕ ПРАКТИКИ:"
            for practice in specific_practices.get("national", [])[:2]:
                life_context_block += f"\n- {practice}"
            for practice in specific_practices.get("regional", [])[:1]:
                life_context_block += f"\n- {practice}"
            for practice in specific_practices.get("age_specific", [])[:1]:
                life_context_block += f"\n- {practice}"

        # Добавляем информацию о социальной желательности
        if social_desirability:
            life_context_block += "\n\nТЕНДЕНЦИИ К СОЦИАЛЬНО ЖЕЛАТЕЛЬНЫМ ОТВЕТАМ:"
            for pattern in social_desirability:
                life_context_block += f"\n- {pattern['description']} (сила: {pattern['strength']:.1f})"
                if pattern['examples']:
                    life_context_block += f"\n  Пример: {pattern['examples'][0]}"

        # Добавляем блок в промпт перед общими правилами
        if "ОБЩИЕ ПРАВИЛА ОТВЕТА" in prompt:
            prompt = prompt.replace("ОБЩИЕ ПРАВИЛА ОТВЕТА", f"{life_context_block}\n\nОБЩИЕ ПРАВИЛА ОТВЕТА")
        else:
            prompt += life_context_block

        return prompt


class Inconsistency:
    """Класс для моделирования непоследовательности в ответах"""

    def __init__(self):
        """Инициализация параметров непоследовательности"""
        # Типы непоследовательностей
        self.inconsistency_types = {
            "изменение_уверенности": {
                "description": "Изменение степени уверенности в информации при переформулировке вопроса",
                "examples": [
                    "Изначально: 'Я точно знаю, что...' → После: 'Мне кажется, что...'",
                    "Изначально: 'Не уверен, но...' → После: 'Я абсолютно уверен, что...'"
                ]
            },
            "противоречивые_утверждения": {
                "description": "Противоречивые утверждения при обсуждении одной темы",
                "examples": [
                    "Изначально: 'Я никогда не беру кредиты' → После: 'У меня есть небольшой кредит'",
                    "Изначально: 'Я всегда сравниваю цены' → После: 'Обычно покупаю не задумываясь'"
                ]
            },
            "изменение_предпочтений": {
                "description": "Изменение предпочтений при смене контекста вопроса",
                "examples": [
                    "Изначально: 'Доходность важнее надежности' → После: 'Безопасность вклада для меня на первом месте'",
                    "Изначально: 'Я предпочитаю наличные' → После: 'Обычно расплачиваюсь картой'"
                ]
            },
            "разная_финансовая_грамотность": {
                "description": "Проявление разного уровня финансовой грамотности в разных темах",
                "examples": [
                    "Точное использование терминологии при обсуждении кредитов, но путаница в инвестиционных терминах",
                    "Уверенное рассуждение о банковских картах, но примитивное понимание страховых продуктов"
                ]
            },
            "противоречия_в_финансовом_поведении": {
                "description": "Заявленные принципы противоречат описанному поведению",
                "examples": [
                    "Изначально: 'Я строго контролирую расходы' → После: 'Часто не помню, на что потратил деньги'",
                    "Изначально: 'Всегда откладываю 10% дохода' → После: 'Никогда не получается накопить'"
                ]
            }
        }

        # Факторы, влияющие на уровень непоследовательности
        self.inconsistency_factors = {
            "усталость": {
                "description": "Снижение качества и последовательности ответов при длительном опросе",
                "effects": [
                    "Более короткие ответы в конце опроса",
                    "Рост противоречий при усталости",
                    "Снижение внимания к деталям вопроса"
                ]
            },
            "сложность_темы": {
                "description": "Более противоречивые ответы в сложных финансовых темах",
                "effects": [
                    "Больше противоречий в темах за пределами компетенции",
                    "Использование шаблонных фраз при непонимании вопроса",
                    "Выдача уверенных, но неточных суждений"
                ]
            },
            "формулировка_вопроса": {
                "description": "Различные ответы на схожие вопросы с разной формулировкой",
                "effects": [
                    "Разные ответы на положительно и отрицательно сформулированные вопросы",
                    "Влияние предложенных вариантов ответа на мнение",
                    "Противоречивые ответы при изменении контекста вопроса"
                ]
            }
        }

    def generate_inconsistency_profile(self, persona: Dict) -> Dict:
        """
        Создание профиля непоследовательности для персоны

        Args:
            persona: Словарь с данными персоны

        Returns:
            Словарь с профилем непоследовательности
        """
        # Извлекаем релевантные характеристики персоны
        age = persona.get('Возраст', 30)
        literacy_level = persona.get('Финансовый профиль', {}).get('Уровень финансовой грамотности', 'средний')

        # Базовый уровень непоследовательности (0-1)
        base_inconsistency = 0.4  # Средний уровень непоследовательности

        # Корректируем в зависимости от возраста (U-образная кривая)
        if age < 25 or age > 65:
            # Молодые и пожилые могут быть менее последовательны
            age_factor = 0.1
        else:
            # Средний возраст - более последовательны
            age_factor = -0.1

        # Корректируем в зависимости от финансовой грамотности
        if literacy_level in ["отсутствие знаний", "начинающий"]:
            # Низкая грамотность - выше непоследовательность
            literacy_factor = 0.2
        elif literacy_level == "средний":
            literacy_factor = 0.0
        else:
            # Высокая грамотность - ниже непоследовательность
            literacy_factor = -0.2

        # Рассчитываем итоговый уровень с некоторой случайностью
        inconsistency_level = base_inconsistency + age_factor + literacy_factor
        inconsistency_level = min(0.9, max(0.1, inconsistency_level)) * random.uniform(0.8, 1.2)

        # Выбираем типы непоследовательности, которые будут характерны для персоны
        # Вероятность выбора каждого типа зависит от общего уровня непоследовательности
        selected_types = {}

        for type_name, type_info in self.inconsistency_types.items():
            # Чем выше общий уровень, тем больше типов может быть выбрано
            if random.random() < inconsistency_level * 0.7:
                # Присваиваем каждому типу случайную силу
                strength = random.uniform(inconsistency_level * 0.5, inconsistency_level * 1.5)
                # Ограничиваем значение
                strength = min(0.9, max(0.1, strength))

                selected_types[type_name] = {
                    "description": type_info["description"],
                    "examples": type_info["examples"],
                    "strength": strength
                }

        # Убедимся, что хотя бы один тип выбран для реалистичности
        if not selected_types:
            random_type = random.choice(list(self.inconsistency_types.keys()))
            selected_types[random_type] = {
                "description": self.inconsistency_types[random_type]["description"],
                "examples": self.inconsistency_types[random_type]["examples"],
                "strength": inconsistency_level
            }

        # Создаем профиль усталости (для моделирования ухудшения качества ответов)
        fatigue_profile = {
            "fatigue_rate": random.uniform(0.05, 0.15),  # Скорость нарастания усталости
            "current_fatigue": 0.0,  # Текущий уровень усталости
            "max_fatigue": random.uniform(0.6, 0.9)  # Максимальный уровень усталости
        }

        return {
            "overall_level": inconsistency_level,
            "types": selected_types,
            "fatigue_profile": fatigue_profile
        }

    def update_fatigue(self, inconsistency_profile: Dict, question_index: int = 0) -> Dict:
        """
        Обновление уровня усталости на основе количества вопросов

        Args:
            inconsistency_profile: Профиль непоследовательности
            question_index: Индекс текущего вопроса

        Returns:
            Обновленный профиль непоследовательности
        """
        fatigue_profile = inconsistency_profile.get("fatigue_profile", {})

        if not fatigue_profile:
            return inconsistency_profile

        # Извлекаем параметры
        fatigue_rate = fatigue_profile.get("fatigue_rate", 0.1)
        current_fatigue = fatigue_profile.get("current_fatigue", 0.0)
        max_fatigue = fatigue_profile.get("max_fatigue", 0.8)

        # Увеличиваем усталость с каждым вопросом
        new_fatigue = min(max_fatigue, current_fatigue + fatigue_rate * (question_index + 1))

        # Обновляем профиль
        inconsistency_profile["fatigue_profile"]["current_fatigue"] = new_fatigue

        # Корректируем общий уровень непоследовательности с учетом усталости
        base_level = inconsistency_profile.get("overall_level", 0.4)
        fatigue_factor = new_fatigue * 0.5  # Влияние усталости на общий уровень

        inconsistency_profile["overall_level"] = min(0.9, base_level + fatigue_factor)

        return inconsistency_profile

    def apply_inconsistency_to_prompt(self, prompt: str, inconsistency_profile: Dict, question_index: int = 0) -> str:
        """
        Добавление инструкций по непоследовательности в промпт

        Args:
            prompt: Исходный промпт
            inconsistency_profile: Профиль непоследовательности
            question_index: Индекс вопроса в последовательности (для моделирования усталости)

        Returns:
            Модифицированный промпт
        """
        # Обновляем профиль с учетом усталости
        updated_profile = self.update_fatigue(inconsistency_profile, question_index)

        # Извлекаем параметры
        overall_level = updated_profile.get("overall_level", 0.4)
        types = updated_profile.get("types", {})
        fatigue = updated_profile.get("fatigue_profile", {}).get("current_fatigue", 0.0)

        # Формируем инструкцию по непоследовательности
        inconsistency_instruction = "\n\nНЕПОСЛЕДОВАТЕЛЬНОСТЬ В ОТВЕТАХ:"
        inconsistency_instruction += f"\n- Общий уровень противоречивости: {overall_level:.2f} (где 0 - полная последовательность, 1 - максимальная противоречивость)"

        # Добавляем информацию о типах непоследовательности
        if types:
            inconsistency_instruction += "\n- Характерные типы непоследовательности:"
            for type_name, type_info in types.items():
                inconsistency_instruction += f"\n  • {type_info['description']} (сила: {type_info['strength']:.2f})"
                if random.random() < 0.5 and type_info['examples']:  # Не всегда добавляем пример
                    example = random.choice(type_info['examples'])
                    inconsistency_instruction += f"\n    Пример: {example}"

        # Добавляем информацию об усталости, если она значительна
        if fatigue > 0.3:
            fatigue_level = "высокая" if fatigue > 0.6 else "умеренная"
            inconsistency_instruction += f"\n- Уровень усталости: {fatigue_level} ({fatigue:.2f})"
            inconsistency_instruction += "\n  • Это может проявляться в более коротких ответах, меньшем внимании к деталям вопроса"
            if fatigue > 0.5:
                inconsistency_instruction += ", повышенной противоречивости и раздражительности"

            # Рекомендации по длине ответа в зависимости от усталости
            if fatigue > 0.7:
                inconsistency_instruction += "\n  • Давай более короткие ответы из-за высокой усталости"
            elif fatigue > 0.4:
                inconsistency_instruction += "\n  • Ответы могут быть менее развернутыми из-за усталости"

        # Добавляем инструкцию в промпт
        if "ОБЩИЕ ПРАВИЛА ОТВЕТА" in prompt:
            prompt = prompt.replace("ОБЩИЕ ПРАВИЛА ОТВЕТА", f"{inconsistency_instruction}\n\nОБЩИЕ ПРАВИЛА ОТВЕТА")
        else:
            prompt += inconsistency_instruction

        return prompt


class EnhancedFinancialRespondent:
    """Расширенный класс для генерации реалистичных ответов с учетом всех дополнительных факторов"""

    def __init__(self, marketplace):
        """
        Инициализация с компонентами для создания реалистичных ответов

        Args:
            marketplace: Экземпляр RespondentsMarketplace
        """
        self.marketplace = marketplace
        self.cognitive_biases = CognitiveBiases()
        self.emotional_factors = EmotionalFactors()
        self.linguistic_variation = LinguisticVariation()
        self.life_context = LifeContextFactors()
        self.inconsistency = Inconsistency()

        # Хранение истории ответов для каждой персоны
        self.response_history = {}

    def enhance_persona(self, persona: Dict) -> Dict:
        """
        Расширение данных персоны дополнительными атрибутами

        Args:
            persona: Исходный словарь с персоной

        Returns:
            Расширенный словарь персоны
        """
        # Создаем копию, чтобы не модифицировать оригинал
        enhanced_persona = persona.copy()

        # Добавляем когнитивные искажения
        literacy_level = persona.get('Финансовый профиль', {}).get('Уровень финансовой грамотности', 'средний')
        cognitive_biases = self.cognitive_biases.get_random_biases(num_biases=3, literacy_level=literacy_level)

        # Добавляем эмоциональные факторы
        emotional_factors = self.emotional_factors.get_random_emotions(num_emotions=3)

        # Создаем лингвистический профиль
        linguistic_profile = self.linguistic_variation.generate_linguistic_profile(persona)

        # Создаем профиль непоследовательности
        inconsistency_profile = self.inconsistency.generate_inconsistency_profile(persona)

        # Расширяем финансовый профиль
        if 'Финансовый профиль' not in enhanced_persona:
            enhanced_persona['Финансовый профиль'] = {}

        enhanced_persona['Финансовый профиль']['Когнитивные искажения'] = cognitive_biases
        enhanced_persona['Финансовый профиль']['Эмоциональные факторы'] = emotional_factors
        enhanced_persona['Лингвистический профиль'] = linguistic_profile
        enhanced_persona['Профиль непоследовательности'] = inconsistency_profile

        return enhanced_persona

    def generate_enhanced_prompt(self, enhanced_persona: Dict, question: Dict, question_index: int = 0) -> str:
        """
        Генерация улучшенного промпта с учетом всех дополнительных факторов

        Args:
            enhanced_persona: Расширенный словарь персоны
            question: Словарь с вопросом
            question_index: Индекс вопроса в последовательности (для моделирования усталости)

        Returns:
            Улучшенный промпт
        """
        # Генерируем базовый промпт через стандартный метод маркетплейса
        base_prompt = self.marketplace._generate_enhanced_prompt(enhanced_persona, question)

        # Извлекаем дополнительные профили
        cognitive_biases = enhanced_persona.get('Финансовый профиль', {}).get('Когнитивные искажения', {})
        emotional_factors = enhanced_persona.get('Финансовый профиль', {}).get('Эмоциональные факторы', {})
        linguistic_profile = enhanced_persona.get('Лингвистический профиль', {})
        inconsistency_profile = enhanced_persona.get('Профиль непоследовательности', {})

        enhanced_prompt = base_prompt

        # Применяем когнитивные искажения
        for bias_name, bias_strength in cognitive_biases.items():
            enhanced_prompt = self.cognitive_biases.apply_bias_to_prompt(
                enhanced_prompt, bias_name, bias_strength
            )

        # Применяем эмоциональные факторы
        for emotion_name, emotion_strength in emotional_factors.items():
            enhanced_prompt = self.emotional_factors.apply_emotion_to_prompt(
                enhanced_prompt, emotion_name, emotion_strength, question.get('topic')
            )

        # Применяем лингвистические вариации
        if linguistic_profile:
            enhanced_prompt = self.linguistic_variation.apply_linguistic_profile_to_prompt(
                enhanced_prompt, linguistic_profile
            )

        # Применяем жизненный контекст
        enhanced_prompt = self.life_context.apply_life_context_to_prompt(
            enhanced_prompt, enhanced_persona, question
        )

        # Применяем непоследовательность с учетом истории ответов
        if inconsistency_profile:
            enhanced_prompt = self.inconsistency.apply_inconsistency_to_prompt(
                enhanced_prompt, inconsistency_profile, question_index
            )

        return enhanced_prompt

    def generate_realistic_answer(self, persona_id: str, persona: Dict, question: Dict,
                                 question_index: int = 0, **kwargs) -> str:
        """
        Генерация реалистичного ответа с учетом всех факторов

        Args:
            persona_id: Уникальный идентификатор персоны
            persona: Словарь с данными персоны
            question: Словарь с вопросом
            question_index: Индекс вопроса в последовательности
            **kwargs: Дополнительные параметры для метода generate_answer

        Returns:
            Сгенерированный ответ
        """
        # Проверяем, есть ли у нас уже расширенная версия персоны
        if not persona.get('Финансовый профиль', {}).get('Когнитивные искажения'):
            enhanced_persona = self.enhance_persona(persona)
        else:
            enhanced_persona = persona

        # Проверяем, есть ли история ответов для этой персоны
        if persona_id not in self.response_history:
            self.response_history[persona_id] = []

        # Генерируем улучшенный промпт
        enhanced_prompt = self.generate_enhanced_prompt(
            enhanced_persona,
            question,
            question_index
        )

        # Генерируем ответ с использованием улучшенного промпта
        answer = self.marketplace.generate_answer(
            enhanced_persona,
            question,
            **kwargs,
            _enhanced_prompt=enhanced_prompt  # Передаем готовый промпт
        )

        # Сохраняем ответ в историю для этой персоны
        self.response_history[persona_id].append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })

        return answer

    def get_persona_history(self, persona_id: str) -> List[Dict]:
        """
        Получение истории ответов персоны

        Args:
            persona_id: Уникальный идентификатор персоны

        Returns:
            Список словарей с историей вопросов и ответов
        """
        return self.response_history.get(persona_id, [])

    def reset_history(self, persona_id: str = None) -> None:
        """
        Сброс истории ответов персоны или всех персон

        Args:
            persona_id: Уникальный идентификатор персоны (если None, сбрасывается вся история)
        """
        if persona_id is None:
            self.response_history = {}
        elif persona_id in self.response_history:
            self.response_history[persona_id] = []


class RespondentsMarketplace:
    """Маркетплейс для генерации ответов респондентов с разным уровнем финансовой грамотности"""

    def __init__(self, api_key_claude: Optional[str] = None, api_key_openai: Optional[str] = None):
        """
        Инициализация маркетплейса респондентов

        Args:
            api_key_claude: API ключ для Anthropic Claude
            api_key_openai: API ключ для OpenAI (опционально)
        """
        # Проверяем, что хотя бы один ключ API предоставлен
        if not api_key_claude and not api_key_openai:
            raise ValueError("Необходим хотя бы один API ключ (Claude или OpenAI)")

        self.api_key_claude = api_key_claude
        self.api_key_openai = api_key_openai

        if api_key_claude:
            self.client_claude = anthropic.Anthropic(api_key=self.api_key_claude)
        else:
            self.client_claude = None

        if api_key_openai:
            self.client_openai = openai.OpenAI(api_key=self.api_key_openai)
        else:
            self.client_openai = None

        # Справочники для генерации общих демографических данных
        self.regions = [
            "Москва", "Санкт-Петербург", "Центральный", "Северо-Западный",
            "Южный", "Северо-Кавказский", "Приволжский", "Уральский",
            "Сибирский", "Дальневосточный"
        ]

        self.cities = {
            "Москва": ["Москва"],
            "Санкт-Петербург": ["Санкт-Петербург"],
            "Центральный": ["Воронеж", "Тула", "Ярославль", "Рязань", "Тверь", "Владимир", "Брянск"],
            "Северо-Западный": ["Калининград", "Псков", "Петрозаводск", "Мурманск", "Архангельск"],
            "Южный": ["Ростов-на-Дону", "Краснодар", "Волгоград", "Севастополь", "Симферополь"],
            "Северо-Кавказский": ["Ставрополь", "Махачкала", "Владикавказ", "Грозный", "Нальчик"],
            "Приволжский": ["Нижний Новгород", "Казань", "Самара", "Уфа", "Пермь", "Саратов"],
            "Уральский": ["Екатеринбург", "Челябинск", "Тюмень", "Сургут"],
            "Сибирский": ["Новосибирск", "Омск", "Красноярск", "Иркутск", "Томск", "Кемерово"],
            "Дальневосточный": ["Владивосток", "Хабаровск", "Якутск", "Благовещенск", "Южно-Сахалинск"]
        }

        self.professions = [
            "IT-специалист", "Аналитик/Data Scientist", "Менеджер среднего звена",
            "Руководитель высшего звена", "Врач/медработник", "Учитель/преподаватель",
            "Инженер", "Дизайнер/художник", "Предприниматель", "Маркетолог/PR",
            "Юрист/адвокат", "Бухгалтер/финансист", "Рабочий", "Государственный служащий",
            "Студент", "Пенсионер", "Временно безработный", "Фрилансер",
            "Военнослужащий", "Полицейский/охранник", "Научный сотрудник", "Продавец/кассир"
        ]

        self.education_levels = [
            "Среднее образование", "Среднее специальное", "Неоконченное высшее",
            "Высшее (бакалавр)", "Высшее (специалист)", "Высшее (магистр)",
            "Два и более высших образования", "Ученая степень", "Начальное образование"
        ]

        self.family_statuses = [
            "Холост/Не замужем", "Женат/Замужем", "Гражданский брак",
            "Разведен/Разведена", "Вдовец/Вдова", "В отношениях (не проживают вместе)"
        ]

        self.income_brackets = [
            "Менее 15 000 ₽", "15 000 - 30 000 ₽", "30 000 - 60 000 ₽",
            "60 000 - 100 000 ₽", "100 000 - 150 000 ₽", "150 000 - 250 000 ₽",
            "250 000 - 500 000 ₽", "Более 500 000 ₽", "Предпочитаю не отвечать"
        ]

        self.hobby_options = [
            "Спорт/фитнес", "Чтение", "Кино/сериалы", "Музыка", "Путешествия",
            "Кулинария", "Рыбалка/охота", "Рукоделие", "Компьютерные игры", "Садоводство",
            "Фотография", "Коллекционирование", "Танцы", "Рисование", "Волонтерство",
            "Домашние животные", "Настольные игры", "Активный отдых на природе",
            "Посещение театров/музеев", "Блогинг/влогинг", "Техническое творчество"
        ]

        # Уровни финансовой грамотности
        self.financial_literacy_levels = [
            "отсутствие знаний", "начинающий", "средний", "продвинутый", "эксперт"
        ]

        # Финансовое отношение к риску
        self.risk_attitudes = [
            "избегающий риска", "умеренный", "склонный к риску"
        ]

        # Отношение к банкам
        self.bank_trust_levels = [
            "низкое", "среднее", "высокое"
        ]

        # Отношение к кредитам
        self.loan_attitudes = [
            "негативное", "нейтральное", "позитивное"
        ]

        # Модели финансового поведения
        self.financial_behaviors = [
            "избегающий риска", "импульсивный", "прагматичный",
            "осознанный минималист", "статусный"
        ]

        # Банковские продукты
        self.bank_products = [
            "дебетовые карты", "кредитные карты", "потребительские кредиты",
            "ипотека", "вклады", "накопительные счета", "инвестиционные продукты"
        ]

        # База знаний о финансах
        self.knowledge_base = FinancialKnowledgeBase()

        # Анализатор отзывов о банках
        self.reviews_analyzer = BankReviewsAnalyzer()

        # Параметры для промптов
        self.prompting_params = {
            "temperature_min": 0.3,
            "temperature_max": 0.85,
            "max_tokens": 1500,
            "prompt_data": {},
            "use_reviews_data": False
        }

        # Доступные LLM модели
        self.claude_models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        self.openai_models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

        # Маппинг типов вопросов на аспекты финансов
        self.financial_topic_mapping = {
            "кредиты": ["кредит", "займ", "ипотек", "потребит", "рассрочк"],
            "карты": ["карт", "дебет", "кэшбэк", "кешбэк", "бонус", "лимит"],
            "вклады": ["вклад", "депозит", "накопи", "процент", "сбережени"],
            "инвестиции": ["инвест", "акци", "облигаци", "брокер", "фонд", "пиф", "бирж"],
            "общие": ["банк", "финанс", "деньг", "платеж", "перевод", "комисси"],
            "онлайн-сервисы": ["приложени", "сайт", "онлайн", "личный кабинет", "мобильн"]
        }

        # Кэш для API-ответов
        self.response_cache = {}

        # Счетчик использованных токенов
        self.tokens_used = {
            "claude": 0,
            "openai": 0
        }

        # Инициализация расширенного генератора респондентов
        self.enhanced_respondent = EnhancedFinancialRespondent(self)

    def generate_persona(self, weighted: bool = True) -> Dict:
        """
        Генерация случайной персоны с уровнем финансовой грамотности

        Args:
            weighted: Использовать взвешенное распределение для реалистичности

        Returns:
            Dictionary с атрибутами персоны
        """
        # Пол с реалистичным распределением
        gender = random.choices(
            ["Мужской", "Женский"],
            weights=[0.48, 0.52] if weighted else None
        )[0]

        # Возраст с реалистичным распределением по возрастным группам
        age_groups = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 65), (66, 80)]
        age_weights = [0.12, 0.22, 0.21, 0.18, 0.15, 0.12] if weighted else None

        age_group = random.choices(age_groups, weights=age_weights)[0]
        age = random.randint(age_group[0], age_group[1])

        # Регион с учетом распределения населения
        region_weights = [0.15, 0.10, 0.13, 0.05, 0.05, 0.05, 0.13, 0.12, 0.12, 0.10] if weighted else None
        region = random.choices(self.regions, weights=region_weights)[0]

        # Выбор города на основе региона
        city = random.choice(self.cities.get(region, ["Не указан"]))

        # Доход, коррелирующий с возрастом, с нормальным распределением
        if age < 25:
            income_idx = min(max(0, int(np.random.normal(1, 1))), len(self.income_brackets)-1)
        elif age < 35:
            income_idx = min(max(0, int(np.random.normal(3, 1.5))), len(self.income_brackets)-1)
        elif age < 45:
            income_idx = min(max(0, int(np.random.normal(4, 1.5))), len(self.income_brackets)-1)
        elif age < 55:
            income_idx = min(max(0, int(np.random.normal(3, 2))), len(self.income_brackets)-1)
        else:
            income_idx = min(max(0, int(np.random.normal(2, 1.5))), len(self.income_brackets)-1)

        income = self.income_brackets[income_idx]

        # Уровень образования, коррелирующий с возрастом
        if age < 22:
            edu_options = self.education_levels[:3]
            edu_weights = [0.4, 0.4, 0.2]
        elif age < 30:
            edu_options = self.education_levels[:6]
            edu_weights = [0.1, 0.2, 0.1, 0.3, 0.2, 0.1]
        else:
            edu_options = self.education_levels
            edu_weights = [0.10, 0.25, 0.05, 0.25, 0.20, 0.10, 0.03, 0.01, 0.01]

        education = random.choices(edu_options, weights=edu_weights[:len(edu_options)])[0]

        # Семейное положение, коррелирующее с возрастом
        if age < 25:
            family_weights = [0.7, 0.05, 0.2, 0.01, 0.01, 0.03]
        elif age < 35:
            family_weights = [0.3, 0.35, 0.25, 0.05, 0.01, 0.04]
        elif age < 55:
            family_weights = [0.15, 0.5, 0.15, 0.1, 0.05, 0.05]
        else:
            family_weights = [0.1, 0.4, 0.05, 0.2, 0.2, 0.05]

        family_status = random.choices(self.family_statuses, weights=family_weights)[0]

        # Количество детей - коррелирует с возрастом и семейным положением
        max_children = max(0, min(5, int((age - 18) / 5)))

        if "Холост" in family_status or age < 22:
            children_weights = [0.9] + [0.1/max(1, max_children)] * max_children
        elif "Гражданский брак" in family_status:
            children_weights = [0.6] + [0.4/max(1, max_children)] * max_children
        elif "Разведен" in family_status:
            children_weights = [0.3] + [0.7/max(1, max_children)] * max_children
        else:
            children_weights = [0.2] + [0.8/max(1, max_children)] * max_children

        num_children = random.choices(
            range(0, max_children + 1),
            weights=children_weights[:max_children+1]
        )[0]

        # Выбор 1-3 хобби
        num_hobbies = random.choices([1, 2, 3], weights=[0.2, 0.5, 0.3])[0]
        hobbies = random.sample(self.hobby_options, num_hobbies)

        # Финансовая грамотность - коррелирует с возрастом, образованием и доходом
        # Базовый показатель на основе образования
        education_factor = {
            "Начальное образование": 0.1,
            "Среднее образование": 0.3,
            "Среднее специальное": 0.4,
            "Неоконченное высшее": 0.5,
            "Высшее (бакалавр)": 0.6,
            "Высшее (специалист)": 0.7,
            "Высшее (магистр)": 0.8,
            "Два и более высших образования": 0.9,
            "Ученая степень": 0.95
        }.get(education, 0.5)

        # Фактор возраста (опыт)
        age_factor = min(1.0, max(0.1, (age - 18) / 40))

        # Фактор дохода
        income_factor = {
            "Менее 15 000 ₽": 0.2,
            "15 000 - 30 000 ₽": 0.3,
            "30 000 - 60 000 ₽": 0.5,
            "60 000 - 100 000 ₽": 0.7,
            "100 000 - 150 000 ₽": 0.8,
            "150 000 - 250 000 ₽": 0.9,
            "250 000 - 500 000 ₽": 0.95,
            "Более 500 000 ₽": 1.0,
            "Предпочитаю не отвечать": 0.5
        }.get(income, 0.5)

        # Расчет общего уровня с некоторой случайностью
        literacy_score = (education_factor * 0.4 + age_factor * 0.3 + income_factor * 0.3) * random.uniform(0.7, 1.3)

        # Определение уровня финансовой грамотности
        if literacy_score < 0.25:
            financial_literacy = "отсутствие знаний"
        elif literacy_score < 0.45:
            financial_literacy = "начинающий"
        elif literacy_score < 0.7:
            financial_literacy = "средний"
        elif literacy_score < 0.9:
            financial_literacy = "продвинутый"
        else:
            financial_literacy = "эксперт"

        # Опыт использования финансовых продуктов - зависит от уровня грамотности
        literacy_idx = self.financial_literacy_levels.index(financial_literacy)

        financial_products = {}

        # Дебетовая карта - есть почти у всех
        financial_products["Дебетовая карта"] = random.random() < (0.5 + literacy_idx * 0.1)

        # Кредитная карта - растет с уровнем грамотности
        financial_products["Кредитная карта"] = random.random() < (0.1 + literacy_idx * 0.15)

        # Потребительский кредит - умеренный рост с грамотностью
        financial_products["Потребительский кредит"] = random.random() < (0.15 + literacy_idx * 0.1)

        # Ипотека - зависит от возраста и дохода
        has_mortgage_chance = 0.01
        if 25 <= age <= 50:
            has_mortgage_chance += 0.15
        if income_idx >= 3:  # Доход от 60 000
            has_mortgage_chance += 0.15
        financial_products["Ипотека"] = random.random() < has_mortgage_chance

        # Вклад - растет с грамотностью
        financial_products["Вклад"] = random.random() < (0.05 + literacy_idx * 0.2)

        # Инвестиции - в основном у продвинутых и экспертов
        financial_products["Инвестиции"] = random.random() < (0.01 + (literacy_idx ** 2) * 0.05)

        # Страховые продукты - умеренный рост с грамотностью
        financial_products["Страхование"] = random.random() < (0.05 + literacy_idx * 0.15)

        # Отношение к финансам - коррелирует с уровнем грамотности

        # Доверие к банкам
        if financial_literacy in ["отсутствие знаний", "начинающий"]:
            trust_weights = [0.5, 0.3, 0.2]
        elif financial_literacy == "средний":
            trust_weights = [0.3, 0.5, 0.2]
        else:
            trust_weights = [0.2, 0.3, 0.5]

        bank_trust = random.choices(self.bank_trust_levels, weights=trust_weights)[0]

        # Отношение к кредитам
        if financial_literacy in ["отсутствие знаний"]:
            loan_weights = [0.6, 0.3, 0.1]
        elif financial_literacy == "начинающий":
            loan_weights = [0.4, 0.4, 0.2]
        elif financial_literacy == "средний":
            loan_weights = [0.3, 0.4, 0.3]
        else:
            loan_weights = [0.2, 0.4, 0.4]

        loan_attitude = random.choices(self.loan_attitudes, weights=loan_weights)[0]

        # Отношение к риску - коррелирует с возрастом и доходом
        if age > 60:
            risk_weights = [0.7, 0.2, 0.1]
        elif age > 40:
            risk_weights = [0.4, 0.4, 0.2]
        else:
            risk_weights = [0.3, 0.4, 0.3]

        # Корректировка на основе дохода
        if income_idx >= 5:  # Высокий доход
            risk_weights = [max(0.1, risk_weights[0] - 0.2), risk_weights[1], min(0.6, risk_weights[2] + 0.2)]

        risk_attitude = random.choices(self.risk_attitudes, weights=risk_weights)[0]

        # Модель финансового поведения
        if risk_attitude == "избегающий риска":
            behavior_weights = [0.5, 0.1, 0.2, 0.2, 0.0]
        elif risk_attitude == "умеренный":
            behavior_weights = [0.2, 0.2, 0.3, 0.2, 0.1]
        else:  # склонный к риску
            behavior_weights = [0.1, 0.3, 0.2, 0.1, 0.3]

        financial_behavior = random.choices(self.financial_behaviors, weights=behavior_weights)[0]

        # Используем базу знаний для обогащения данных
        financial_vocabulary = self.knowledge_base.get_vocabulary_for_level(financial_literacy, 15)
        financial_misconceptions = self.knowledge_base.get_misconceptions_for_level(financial_literacy)
        behavior_patterns = self.knowledge_base.get_behavior_patterns(financial_behavior)
        financial_goals = self.knowledge_base.get_random_financial_goals(2)

        # Сборка полной персоны
        persona = {
            "Пол": gender,
            "Возраст": age,
            "Регион": region,
            "Город": city,
            "Профессия": random.choice(self.professions),
            "Образование": education,
            "Семейное положение": family_status,
            "Количество детей": num_children,
            "Доход": income,
            "Увлечения": hobbies,
            "Финансовый профиль": {
                "Уровень финансовой грамотности": financial_literacy,
                "Используемые продукты": financial_products,
                "Отношение к финансам": {
                    "Доверие к банкам": bank_trust,
                    "Отношение к кредитам": loan_attitude,
                    "Отношение к риску": risk_attitude,
                    "Модель финансового поведения": financial_behavior
                },
                "Финансовые знания": {
                    "Словарный запас": financial_vocabulary,
                    "Заблуждения": financial_misconceptions
                },
                "Финансовые цели": financial_goals,
                "Поведенческие паттерны": behavior_patterns
            }
        }

        # Улучшаем персону дополнительными факторами
        enhanced_persona = self.enhanced_respondent.enhance_persona(persona)

        return enhanced_persona

    def load_questions(self, file_data) -> List[Dict]:
        """
        Загрузка вопросов из Excel файла

        Args:
            file_data: Данные Excel файла с вопросами

        Returns:
            Список словарей с вопросами
        """
        try:
            df = pd.read_excel(file_data)

            # Проверка наличия обязательного столбца
            if 'question' not in df.columns:
                raise ValueError("В файле отсутствует обязательный столбец 'question'")

            questions = []

            for idx, row in df.iterrows():
                # Определение финансовой темы вопроса
                question_text = row['question'].lower()
                financial_topic = "общие"  # По умолчанию

                for topic, keywords in self.financial_topic_mapping.items():
                    if any(keyword in question_text for keyword in keywords):
                        financial_topic = topic
                        break

                question = {
                    "id": row.get('id', idx + 1),
                    "text": row['question'],
                    "type": row.get('type', 'open'),
                    "topic": row.get('topic', financial_topic),
                    "options": str(row.get('options', '')).split(',') if pd.notna(row.get('options')) else [],
                    "context": row.get('context', '')
                }
                questions.append(question)

            return questions
        except Exception as e:
            raise ValueError(f"Ошибка при загрузке вопросов: {str(e)}")

    def load_bank_reviews(self, file_data) -> bool:
        """
        Загрузка и анализ отзывов о банках

        Args:
            file_data: Данные Excel файла с отзывами

        Returns:
            True если загрузка прошла успешно, иначе False
        """
        try:
            self.reviews_analyzer.load_reviews(file_data)

            # Извлекаем данные для улучшения промптов
            self.prompting_params["prompt_data"] = self.reviews_analyzer.extract_prompting_data()
            self.prompting_params["use_reviews_data"] = True

            st.success(f"Загружено и проанализировано {len(self.reviews_analyzer.reviews_data)} отзывов о банках")
            return True
        except Exception as e:
            st.error(f"Ошибка при загрузке отзывов о банках: {str(e)}")
            return False

    def _format_persona_for_prompt(self, persona: Dict) -> str:
        """
        Форматирование персоны для использования в промпте

        Args:
            persona: Словарь с данными персоны

        Returns:
            Строка с отформатированной информацией о персоне
        """
        # Базовая демографическая информация
        basic_info = [
            f"Пол: {persona['Пол']}",
            f"Возраст: {persona['Возраст']}",
            f"Город: {persona['Город']} ({persona['Регион']})",
            f"Профессия: {persona['Профессия']}",
            f"Образование: {persona['Образование']}",
            f"Семейное положение: {persona['Семейное положение']}",
            f"Количество детей: {persona['Количество детей']}",
            f"Доход: {persona['Доход']}"
        ]

        if 'Увлечения' in persona and persona['Увлечения']:
            basic_info.append(f"Увлечения: {', '.join(persona['Увлечения'])}")

        # Финансовый профиль
        financial_profile = []
        if 'Финансовый профиль' in persona:
            fp = persona['Финансовый профиль']

            financial_profile.append(f"Уровень финансовой грамотности: {fp.get('Уровень финансовой грамотности', 'средний')}")

            # Используемые продукты
            products_used = []
            for product, used in fp.get('Используемые продукты', {}).items():
                if used:
                    products_used.append(product)

            if products_used:
                financial_profile.append(f"Используемые финансовые продукты: {', '.join(products_used)}")
            else:
                financial_profile.append("Не использует банковские продукты")

            # Отношение к финансам
            if 'Отношение к финансам' in fp:
                for key, value in fp['Отношение к финансам'].items():
                    financial_profile.append(f"{key}: {value}")

            # Финансовые цели
            if 'Финансовые цели' in fp and fp['Финансовые цели']:
                financial_profile.append(f"Финансовые цели: {', '.join(fp['Финансовые цели'])}")

        # Собираем все вместе
        formatted_persona = "БАЗОВАЯ ИНФОРМАЦИЯ:\n" + "\n".join(basic_info)
        formatted_persona += "\n\nФИНАНСОВЫЙ ПРОФИЛЬ:\n" + "\n".join(financial_profile)

        # Добавляем поведенческие паттерны, если есть
        if 'Финансовый профиль' in persona and 'Поведенческие паттерны' in persona['Финансовый профиль']:
            patterns = persona['Финансовый профиль']['Поведенческие паттерны']
            if patterns:
                formatted_persona += "\n\nПОВЕДЕНЧЕСКИЕ ПАТТЕРНЫ:\n" + "\n".join([f"- {p}" for p in patterns])

        # Добавляем заблуждения, если необходимо
        if ('Финансовый профиль' in persona and 'Финансовые знания' in persona['Финансовый профиль'] and
            'Заблуждения' in persona['Финансовый профиль']['Финансовые знания']):

            misconceptions = persona['Финансовый профиль']['Финансовые знания']['Заблуждения']
            if misconceptions:
                formatted_persona += "\n\nВОЗМОЖНЫЕ ФИНАНСОВЫЕ ЗАБЛУЖДЕНИЯ:\n" + "\n".join([f"- {m}" for m in misconceptions])

        return formatted_persona

    def _generate_enhanced_prompt(self, persona: Dict, question: Dict) -> str:
        """
        Генерация базового промпта с учетом финансовой грамотности

        Args:
            persona: Словарь с данными персоны
            question: Словарь с вопросом

        Returns:
            Строка с подготовленным промптом
        """
        # Форматируем данные о персоне
        persona_str = self._format_persona_for_prompt(persona)

        # Получаем уровень финансовой грамотности
        literacy_level = persona.get('Финансовый профиль', {}).get('Уровень финансовой грамотности', 'средний')

        # Получаем параметры для уровня грамотности
        literacy_info = self.knowledge_base.get_literacy_level_info(literacy_level)

        # Словарный запас для уровня
        vocab_examples = persona.get('Финансовый профиль', {}).get('Финансовые знания', {}).get('Словарный запас', [])

        # Определяем тему вопроса
        question_topic = question.get('topic', 'общие')
        if question_topic not in self.financial_topic_mapping:
            question_topic = "общие"

        # Добавляем контекстную информацию из отзывов о банках, если доступно
        context_from_reviews = ""
        if self.prompting_params["use_reviews_data"]:
            prompt_data = self.prompting_params["prompt_data"]

            relevant_terms = []
            if question_topic in prompt_data.get("categorized_terms", {}):
                relevant_terms = prompt_data["categorized_terms"][question_topic][:5]
            else:
                relevant_terms = prompt_data.get("banking_terms", [])[:5]

            # Добавляем релевантные проблемы из отзывов
            relevant_issues = prompt_data.get("common_issues", [])[:3]

            if relevant_terms or relevant_issues:
                context_from_reviews = "\nКОНТЕКСТ ИЗ ОТЗЫВОВ КЛИЕНТОВ БАНКОВ:\n"

                if relevant_terms:
                    context_from_reviews += f"Часто упоминаемые термины: {', '.join(relevant_terms)}\n"

                if relevant_issues:
                    context_from_reviews += f"Типичные проблемы: {'; '.join(relevant_issues)}\n"

        # Вероятность точного ответа на основе уровня грамотности
        accuracy_level = literacy_info.get("accuracy", 0.7)
        confidence_level = literacy_info.get("confidence", 0.7)
        detail_level = literacy_info.get("detail_level", 0.5)

        # Составляем инструкции для разных уровней финансовой грамотности
        literacy_instructions = ""

        if literacy_level == "отсутствие знаний":
            literacy_instructions = """
            - Используй простой, бытовой язык без финансовых терминов
            - Можешь путать финансовые понятия и термины
            - Можешь демонстрировать финансовые заблуждения, указанные в профиле
            - Признавай незнание многих финансовых тем
            - Говори неуверенно, используй фразы типа "мне кажется", "насколько я знаю"
            - Можешь полагаться на слухи и мнения знакомых вместо фактов
            - Не вдавайся в детали финансовых продуктов
            """
        elif literacy_level == "начинающий":
            literacy_instructions = """
            - Используй простые финансовые термины, но можешь иногда их путать
            - Можешь иметь некоторые заблуждения о финансовых продуктах
            - Показывай базовое понимание дебетовых карт и вкладов
            - Можешь выражать неуверенность в сложных финансовых вопросах
            - Проявляй осторожность к новым финансовым инструментам
            - Опирайся больше на личный опыт, чем на знания
            - Интересуйся деталями, но не все понимай
            """
        elif literacy_level == "средний":
            literacy_instructions = """
            - Демонстрируй нормальное понимание распространенных финансовых продуктов
            - Можешь использовать базовую финансовую терминологию
            - Имеешь представление о кредитах, вкладах, дебетовых и кредитных картах
            - Проявляй разумную осторожность в финансовых решениях
            - Можешь задавать уточняющие вопросы по сложным продуктам
            - Говори с умеренной уверенностью в рамках своих знаний
            - Можешь делиться практическим опытом использования финансовых продуктов
            """
        elif literacy_level == "продвинутый":
            literacy_instructions = """
            - Используй грамотную финансовую терминологию
            - Демонстрируй хорошее понимание различных финансовых продуктов
            - Можешь сравнивать разные продукты и их характеристики
            - Говори уверенно в рамках своих знаний
            - Учитывай нюансы финансовых решений
            - Рассматривай долгосрочные последствия финансовых решений
            - Можешь упоминать различные банки и их продукты
            """
        elif literacy_level == "эксперт":
            literacy_instructions = """
            - Используй профессиональную финансовую терминологию
            - Демонстрируй глубокое понимание финансовых продуктов и рынков
            - Можешь давать детальный анализ условий и последствий
            - Учитывай тонкости и исключения в правилах
            - Говори уверенно и авторитетно
            - Можешь упоминать законодательство в финансовой сфере
            - Рассматривай комплексный подход к финансовым решениям
            """

        # Формируем основной промпт
        base_prompt = f"""Ты симулируешь обычного человека, отвечающего на вопрос о финансах или банковских услугах. Тебе нужно ответить максимально реалистично, с учетом своих характеристик и уровня финансовой грамотности.

ХАРАКТЕРИСТИКИ РЕСПОНДЕНТА:
{persona_str}
{context_from_reviews}

ВОПРОС:
{question["text"]}

ИНСТРУКЦИИ ПО ОТВЕТУ В СООТВЕТСТВИИ С ФИНАНСОВОЙ ГРАМОТНОСТЬЮ:
{literacy_instructions}

ОБЩИЕ ПРАВИЛА ОТВЕТА:
1. Отвечай от первого лица, как будто ты действительно этот человек
2. Учитывай все демографические характеристики и уровень финансовой грамотности
3. Используй стиль речи и словарный запас, соответствующие твоему образованию и уровню знаний
4. Будь максимально реалистичным в ответе
5. Не старайся отвечать как эксперт, даже если твой уровень грамотности "эксперт" - отвечай как обычный человек с хорошими знаниями
6. Твоя точность информации должна соответствовать твоему уровню знаний (точность ~{int(accuracy_level*100)}%)
7. Твоя уверенность в ответе должна соответствовать твоему профилю (уверенность ~{int(confidence_level*100)}%)
8. Уровень детализации ответа должен соответствовать твоему уровню знаний (детализация ~{int(detail_level*100)}%)
9. Используй свой жизненный опыт и финансовые паттерны поведения в ответе
"""

        # Добавляем примеры словарного запаса для подсказки
        if vocab_examples:
            base_prompt += f"\nПРИМЕРЫ ФИНАНСОВЫХ ТЕРМИНОВ, КОТОРЫЕ ТЫ МОЖЕШЬ ИСПОЛЬЗОВАТЬ:\n{', '.join(vocab_examples)}\n"

        # Добавляем подсказку для эмоционального окраса ответа
        behavior = persona.get('Финансовый профиль', {}).get('Отношение к финансам', {}).get('Модель финансового поведения', 'прагматичный')

        if behavior == "избегающий риска":
            base_prompt += "\nВ своем ответе проявляй осторожность и консервативный подход к финансовым вопросам."
        elif behavior == "импульсивный":
            base_prompt += "\nВ своем ответе можешь проявлять спонтанность и эмоциональность в отношении финансовых решений."
        elif behavior == "статусный":
            base_prompt += "\nВ своем ответе можешь упоминать престижные или премиальные аспекты банковского обслуживания."

        base_prompt += "\n\nОТВЕТ ОТ ЛИЦА РЕСПОНДЕНТА:"

        return base_prompt

    def generate_answer(self, persona: Dict, question: Dict,
                        model: str = None, api_preference: str = None,
                        temperature: Optional[float] = None,
                        _enhanced_prompt: Optional[str] = None) -> str:
        """
        Генерация ответа через выбранное API

        Args:
            persona: Словарь с данными персоны
            question: Словарь с вопросом
            model: Конкретная модель для использования (опционально)
            api_preference: Предпочтительное API ('claude' или 'openai')
            temperature: Температура для генерации (опционально)
            _enhanced_prompt: Готовый промпт (для внутреннего использования)

        Returns:
            Сгенерированный ответ
        """
        # Создаем уникальный ключ для кэша ответов
        cache_key = f"{json.dumps(persona, sort_keys=True)}_{json.dumps(question, sort_keys=True)}_{model}_{api_preference}_{temperature}"

        # Возвращаем кэшированный ответ, если доступен
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        # Используем предоставленный промпт или генерируем новый
        if _enhanced_prompt:
            prompt = _enhanced_prompt
        else:
            # Используем расширенную генерацию промпта через EnhancedFinancialRespondent
            prompt = self.enhanced_respondent.generate_enhanced_prompt(persona, question)

        # Определяем уровень финансовой грамотности для настройки температуры
        literacy_level = persona.get('Финансовый профиль', {}).get('Уровень финансовой грамотности', 'средний')

        # Устанавливаем температуру на основе уровня грамотности, если не указана явно
        if temperature is None:
            literacy_levels = ["отсутствие знаний", "начинающий", "средний", "продвинутый", "эксперт"]
            literacy_index = literacy_levels.index(literacy_level) if literacy_level in literacy_levels else 2

            # Более низкая температура для экспертов (более структурированные ответы)
            # Более высокая для низкой грамотности (более случайные ответы)
            temperature = self.prompting_params["temperature_max"] - (literacy_index * 0.1)

            # Добавляем немного случайности
            temperature = min(1.0, max(0.1, temperature + random.uniform(-0.1, 0.1)))

        # Ограничиваем температуру диапазоном 0.0-1.0 для совместимости с API
        temperature = min(1.0, max(0.0, temperature))

        # Определяем, какое API использовать
        use_claude = True  # По умолчанию используем Claude, если доступен

        if api_preference == "openai" and self.client_openai:
            use_claude = False
        elif api_preference == "claude" and self.client_claude:
            use_claude = True
        elif self.client_claude is None and self.client_openai:
            use_claude = False

        max_retries = 3
        result = None

        for retry in range(max_retries):
            try:
                if use_claude:
                    # Используем Claude API
                    # Определяем модель Claude
                    claude_model = model if model in self.claude_models else self.claude_models[0]

                    response = self.client_claude.messages.create(
                        model=claude_model,
                        max_tokens=self.prompting_params["max_tokens"],
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    result = response.content[0].text

                    # Обновляем счетчик токенов
                    if hasattr(response, 'usage') and response.usage:
                        self.tokens_used["claude"] += response.usage.input_tokens + response.usage.output_tokens
                else:
                    # Используем OpenAI API
                    # Определяем модель OpenAI
                    openai_model = model if model in self.openai_models else self.openai_models[0]

                    response = self.client_openai.chat.completions.create(
                        model=openai_model,
                        max_tokens=self.prompting_params["max_tokens"],
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    result = response.choices[0].message.content

                    # Обновляем счетчик токенов
                    if hasattr(response, 'usage') and response.usage:
                        self.tokens_used["openai"] += response.usage.prompt_tokens + response.usage.completion_tokens

                # Кэшируем ответ
                self.response_cache[cache_key] = result

                return result

            except Exception as e:
                if retry < max_retries - 1:
                    # Экспоненциальная задержка перед повторной попыткой
                    wait_time = 2 ** retry
                    st.warning(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)

                    # Если ошибка связана с API Claude, попробуем OpenAI, и наоборот
                    if use_claude and self.client_openai:
                        use_claude = False
                        st.warning(f"Ошибка с Claude API, переключаемся на OpenAI: {str(e)}")
                    elif not use_claude and self.client_claude:
                        use_claude = True
                        st.warning(f"Ошибка с OpenAI API, переключаемся на Claude: {str(e)}")
                else:
                    error_msg = f"""
                    Невозможно сгенерировать ответ после {max_retries} попыток.
                    Технические детали: {str(e)}

                    Возможные причины:
                    1. Неверный API-ключ
                    2. Проблемы с подключением
                    3. Временные ограничения сервиса

                    Пожалуйста, проверьте:
                    - Корректность API-ключа
                    - Наличие доступа к сервису
                    - Текущий статус сервиса API
                    """
                    return error_msg

        return "Не удалось сгенерировать ответ после нескольких попыток."

    def generate_realistic_answer(self, persona_id: str, persona: Dict, question: Dict,
                                 question_index: int = 0, **kwargs) -> str:
        """
        Генерация реалистичного ответа с учетом всех факторов

        Args:
            persona_id: Уникальный идентификатор персоны
            persona: Словарь с данными персоны
            question: Словарь с вопросом
            question_index: Индекс вопроса в последовательности
            **kwargs: Дополнительные параметры для метода generate_answer

        Returns:
            Сгенерированный ответ
        """
        return self.enhanced_respondent.generate_realistic_answer(
            persona_id, persona, question, question_index, **kwargs
        )

    def run_generation_batch(self, personas, questions, max_workers=3, api_preference=None, use_enhanced=True):
        """
        Обработка пакета персон и вопросов с параллельным выполнением

        Args:
            personas: Список словарей с персонами
            questions: Список словарей с вопросами
            max_workers: Максимальное количество параллельных рабочих процессов
            api_preference: Предпочтительное API ('claude' или 'openai')
            use_enhanced: Использовать ли улучшенное генерирование ответов

        Returns:
            Список словарей с ответами
        """
        all_answers = []
        total_items = len(personas) * len(questions)
        completed = 0

        # Настройка отображения прогресса через Streamlit
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Генерация ответов: 0%")

        # Функция для генерации одного ответа с обновлением прогресса
        def generate_one_answer(args):
            i, persona, j, question, question_idx = args
            try:
                # Используем улучшенную генерацию ответов, если запрошено
                if use_enhanced:
                    answer_text = self.generate_realistic_answer(
                        str(i), persona, question, question_idx,
                        api_preference=api_preference
                    )
                else:
                    answer_text = self.generate_answer(
                        persona, question, api_preference=api_preference
                    )

                answer = {
                    "id": i * len(questions) + j + 1,
                    "persona_id": i + 1,
                    "question": question,
                    "text": answer_text,
                    "timestamp": datetime.now().isoformat()
                }

                return answer, 1
            except Exception as e:
                error_answer = {
                    "id": i * len(questions) + j + 1,
                    "persona_id": i + 1,
                    "question": question,
                    "text": f"ОШИБКА: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "error": True
                }
                return error_answer, 1

        # Подготовка задач для параллельной обработки
        tasks = []
        for i, persona in enumerate(personas):
            for j, question in enumerate(questions):
                # Добавляем индекс вопроса для моделирования эффекта усталости
                question_idx = j
                tasks.append((i, persona, j, question, question_idx))

        # Запуск параллельной обработки
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(generate_one_answer, task): task for task in tasks}

            for future in concurrent.futures.as_completed(future_to_task):
                answer, progress_increment = future.result()
                all_answers.append(answer)

                # Обновление прогресса
                completed += progress_increment
                progress_percentage = completed/total_items
                progress_bar.progress(progress_percentage)
                status_text.text(f"Генерация ответов: {int(progress_percentage*100)}%")

        # Сортировка ответов по ID
        all_answers.sort(key=lambda x: x["id"])

        return all_answers

    def analyze_results(self, personas: List[Dict], questions: List[Dict], answers: List[Dict]) -> Dict:
        """
        Формирование аналитического отчета

        Args:
            personas: Список словарей с персонами
            questions: Список словарей с вопросами
            answers: Список словарей с ответами

        Returns:
            Словарь с аналитическим отчетом
        """
        try:
            # Базовая статистика
            report = {
                "Общая статистика": {
                    "Количество респондентов": len(personas),
                    "Количество вопросов": len(questions),
                    "Количество ответов": len(answers),
                    "API токенов использовано (Claude)": self.tokens_used["claude"],
                    "API токенов использовано (OpenAI)": self.tokens_used["openai"]
                },
                "Демографический состав": {
                    "Пол": {},
                    "Возраст": {
                        "Средний": float(np.mean([p["Возраст"] for p in personas])),
                        "Медианный": float(np.median([p["Возраст"] for p in personas])),
                        "Минимальный": int(min([p["Возраст"] for p in personas])),
                        "Максимальный": int(max([p["Возраст"] for p in personas]))
                    },
                    "Регионы": {},
                    "Города": {},
                    "Профессии": {},
                    "Образование": {},
                    "Семейное положение": {},
                    "Доход": {},
                    "Дети": {
                        "Среднее количество": float(np.mean([p.get("Количество детей", 0) for p in personas])),
                        "Распределение": {}
                    }
                },
                "Финансовые характеристики": {
                    "Уровни финансовой грамотности": {},
                    "Доверие к банкам": {},
                    "Отношение к кредитам": {},
                    "Отношение к риску": {},
                    "Модели финансового поведения": {},
                    "Используемые финансовые продукты": {}
                },
                "Аналитика ответов": [],
                "Качество данных": {
                    "Ошибки генерации": sum(1 for a in answers if a.get("error", False)),
                    "Успешность": float((len(answers) - sum(1 for a in answers if a.get("error", False))) / len(answers) * 100) if answers else 0
                }
            }

            # Подсчет демографических характеристик
            for key in ["Пол", "Регион", "Город", "Профессия", "Образование", "Семейное положение", "Доход"]:
                value_counts = pd.Series([p.get(key, "Не указано") for p in personas]).value_counts()
                report["Демографический состав"][key if key != "Город" else "Города"] = {
                    str(k): int(v) for k, v in value_counts.items()
                }

            # Распределение детей
            children_counts = pd.Series([p.get("Количество детей", 0) for p in personas]).value_counts()
            report["Демографический состав"]["Дети"]["Распределение"] = {
                str(k): int(v) for k, v in children_counts.items()
            }

            # Подсчет финансовых характеристик
            literacy_counts = pd.Series([
                p.get("Финансовый профиль", {}).get("Уровень финансовой грамотности", "средний")
                for p in personas
            ]).value_counts()

            report["Финансовые характеристики"]["Уровни финансовой грамотности"] = {
                str(k): int(v) for k, v in literacy_counts.items()
            }

            trust_counts = pd.Series([
                p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Доверие к банкам", "среднее")
                for p in personas
            ]).value_counts()

            report["Финансовые характеристики"]["Доверие к банкам"] = {
                str(k): int(v) for k, v in trust_counts.items()
            }

            loan_counts = pd.Series([
                p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Отношение к кредитам", "нейтральное")
                for p in personas
            ]).value_counts()

            report["Финансовые характеристики"]["Отношение к кредитам"] = {
                str(k): int(v) for k, v in loan_counts.items()
            }

            risk_counts = pd.Series([
                p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Отношение к риску", "умеренный")
                for p in personas
            ]).value_counts()

            report["Финансовые характеристики"]["Отношение к риску"] = {
                str(k): int(v) for k, v in risk_counts.items()
            }

            behavior_counts = pd.Series([
                p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Модель финансового поведения", "прагматичный")
                for p in personas
            ]).value_counts()

            report["Финансовые характеристики"]["Модели финансового поведения"] = {
                str(k): int(v) for k, v in behavior_counts.items()
            }

            # Подсчет используемых финансовых продуктов
            products_usage = {}
            for persona in personas:
                fp = persona.get("Финансовый профиль", {})
                products = fp.get("Используемые продукты", {})

                for product, used in products.items():
                    if product not in products_usage:
                        products_usage[product] = {"Используют": 0, "Не используют": 0}

                    if used:
                        products_usage[product]["Используют"] += 1
                    else:
                        products_usage[product]["Не используют"] += 1

            report["Финансовые характеристики"]["Используемые финансовые продукты"] = products_usage

            # Анализ ответов для каждого вопроса
            for question in questions:
                question_answers = [
                    ans for ans in answers
                    if ans["question"]["id"] == question["id"] and not ans.get("error", False)
                ]

                question_analysis = {
                    "Вопрос": question["text"],
                    "Тип вопроса": question["type"],
                    "Тема": question.get("topic", "общие"),
                    "Количество ответов": len(question_answers),
                    "Средняя длина ответа (символы)": int(np.mean([len(a["text"]) for a in question_answers]) if question_answers else 0),
                    "Медианная длина ответа": int(np.median([len(a["text"]) for a in question_answers]) if question_answers else 0)
                }

                # Анализ для вопросов с вариантами ответов
                if question["type"] in ["single", "multiple"] and question["options"]:
                    option_counts = {}
                    for option in question["options"]:
                        option = option.strip()
                        if not option:
                            continue
                        count = sum(1 for a in question_answers if option.lower() in a["text"].lower())
                        option_counts[option] = count

                    question_analysis["Распределение ответов"] = option_counts

                report["Аналитика ответов"].append(question_analysis)

            # Текстовый анализ - вычисление среднего настроения и сложности ответов
            if answers:
                try:
                    # Средняя длина слов в ответах
                    word_counts = [len(a["text"].split()) for a in answers if not a.get("error", False)]
                    report["Аналитика текста"] = {
                        "Средняя длина ответа (слова)": float(np.mean(word_counts)) if word_counts else 0,
                        "Медианная длина ответа (слова)": float(np.median(word_counts)) if word_counts else 0,
                        "Максимальная длина ответа (слова)": max(word_counts) if word_counts else 0,
                        "Минимальная длина ответа (слова)": min(word_counts) if word_counts else 0
                    }
                except Exception as e:
                    st.warning(f"Ошибка в текстовом анализе: {e}")

            return report
        except Exception as e:
            st.error(f"Ошибка при анализе результатов: {str(e)}")
            # Возвращаем базовый отчет в случае ошибки
            return {
                "Общая статистика": {
                    "Количество респондентов": len(personas),
                    "Количество вопросов": len(questions),
                    "Ошибка анализа": str(e)
                }
            }

    def export_to_excel(self, personas: List[Dict], questions: List[Dict], answers: List[Dict]) -> io.BytesIO:
        """
        Экспорт результатов в Excel файл

        Args:
            personas: Список словарей с персонами
            questions: Список словарей с вопросами
            answers: Список словарей с ответами

        Returns:
            io.BytesIO с Excel файлом
        """
        try:
            # Создаем DataFrame с ответами
            data = []

            for answer in answers:
                persona_id = answer["persona_id"]
                persona = personas[persona_id-1]
                question = answer["question"]

                row = {
                    "Респондент_ID": persona_id,
                    "Вопрос_ID": question["id"],
                    "Вопрос": question["text"],
                    "Тип_вопроса": question.get("type", "open"),
                    "Тема_вопроса": question.get("topic", "общие"),
                    "Ответ": answer["text"][:32767] if len(answer["text"]) > 32767 else answer["text"],
                    "Дата_время": answer["timestamp"],
                    "Ошибка": answer.get("error", False)
                }

                # Добавляем демографические характеристики из persona
                for key, value in persona.items():
                    if key != "Финансовый профиль" and key != "Лингвистический профиль" and key != "Профиль непоследовательности":
                        if isinstance(value, list):
                            row[f"Респондент_{key}"] = ", ".join(str(v) for v in value)
                        else:
                            row[f"Респондент_{key}"] = value

                # Добавляем финансовые характеристики
                if "Финансовый профиль" in persona:
                    fp = persona["Финансовый профиль"]

                    # Уровень финансовой грамотности
                    row["Финансовая_грамотность"] = fp.get("Уровень финансовой грамотности", "средний")

                    # Отношение к финансам
                    if "Отношение к финансам" in fp:
                        for key, value in fp["Отношение к финансам"].items():
                            row[f"Финансы_{key.replace(' ', '_')}"] = value

                data.append(row)

            # Создаем основной DataFrame с ответами
            answers_df = pd.DataFrame(data)

            # Создаем DataFrame для респондентов
            personas_data = []
            for i, p in enumerate(personas):
                row = {"ID": i+1}

                # Базовые демографические данные
                for key, value in p.items():
                    if key != "Финансовый профиль" and key != "Лингвистический профиль" and key != "Профиль непоследовательности":
                        if isinstance(value, list):
                            row[key] = ", ".join(str(v) for v in value)
                        else:
                            row[key] = value

                # Финансовый профиль
                if "Финансовый профиль" in p:
                    fp = p["Финансовый профиль"]

                    # Уровень финансовой грамотности
                    row["Уровень_финансовой_грамотности"] = fp.get("Уровень финансовой грамотности", "средний")

                    # Используемые продукты
                    if "Используемые продукты" in fp:
                        for product, used in fp["Используемые продукты"].items():
                            row[f"Продукт_{product.replace(' ', '_')}"] = "Да" if used else "Нет"

                    # Отношение к финансам
                    if "Отношение к финансам" in fp:
                        for key, value in fp["Отношение к финансам"].items():
                            row[f"Отношение_{key.replace(' ', '_')}"] = value

                personas_data.append(row)

            personas_df = pd.DataFrame(personas_data)

            # Создаем DataFrame для вопросов
            questions_df = pd.DataFrame([
                {
                    "ID": q["id"],
                    "Вопрос": q["text"],
                    "Тип": q["type"],
                    "Тема": q.get("topic", "общие"),
                    "Варианты_ответов": ", ".join(q["options"]) if q.get("options") else "",
                    "Контекст": q.get("context", "")
                } for q in questions
            ])

            # Создаем сводную таблицу ответов по респондентам и вопросам
            wide_data = []

            for i, persona in enumerate(personas):
                row = {"Респондент_ID": i+1}

                # Добавляем все характеристики респондента
                for key, value in persona.items():
                    if key != "Финансовый профиль" and key != "Лингвистический профиль" and key != "Профиль непоследовательности":
                        if isinstance(value, list):
                            row[key] = ", ".join(str(v) for v in value)
                        else:
                            row[key] = value

                # Добавляем финансовый профиль
                if "Финансовый профиль" in persona:
                    fp = persona["Финансовый профиль"]

                    # Уровень финансовой грамотности
                    row["Уровень_финансовой_грамотности"] = fp.get("Уровень финансовой грамотности", "средний")

                    # Отношение к финансам
                    if "Отношение к финансам" in fp:
                        for key, value in fp["Отношение к финансам"].items():
                            row[f"Отношение_{key.replace(' ', '_')}"] = value

                # Добавляем ответы на все вопросы
                for question in questions:
                    question_id = question["id"]

                    # Находим ответ этого респондента на этот вопрос
                    answer_obj = next(
                        (a for a in answers if a["persona_id"] == i+1 and a["question"]["id"] == question_id),
                        None
                    )

                    if answer_obj and not answer_obj.get("error", False):
                        # Ограничение для Excel на длину ячейки
                        answer_text = answer_obj["text"]
                        if len(answer_text) > 32767:
                            answer_text = answer_text[:32764] + "..."
                        row[f"Вопрос_{question_id}"] = answer_text
                    else:
                        row[f"Вопрос_{question_id}"] = ""

                wide_data.append(row)

            wide_df = pd.DataFrame(wide_data)

            # Генерируем отчет
            report = self.analyze_results(personas, questions, answers)

            # Создаем DataFrame для аналитики
            analytics_data = []

            # Общая статистика
            analytics_data.append(["ОБЩАЯ СТАТИСТИКА", "", ""])
            for key, value in report["Общая статистика"].items():
                analytics_data.append([key, value, ""])
            analytics_data.append(["", "", ""])

            # Демографический анализ
            analytics_data.append(["ДЕМОГРАФИЧЕСКИЙ СОСТАВ", "", ""])
            analytics_data.append(["", "", ""])

            # Пол
            analytics_data.append(["Распределение по полу", "", ""])
            for gender, count in report["Демографический состав"]["Пол"].items():
                analytics_data.append([gender, int(count), f"{float(count)/len(personas)*100:.1f}%"])
            analytics_data.append(["", "", ""])

            # Возраст
            analytics_data.append(["Возрастное распределение", "", ""])
            age_stats = report["Демографический состав"]["Возраст"]
            analytics_data.append(["Средний возраст", f"{age_stats['Средний']:.1f}", ""])
            analytics_data.append(["Медианный возраст", f"{age_stats['Медианный']:.1f}", ""])
            analytics_data.append(["Минимальный возраст", int(age_stats['Минимальный']), ""])
            analytics_data.append(["Максимальный возраст", int(age_stats['Максимальный']), ""])
            analytics_data.append(["", "", ""])

            # Финансовая грамотность
            analytics_data.append(["ФИНАНСОВЫЕ ХАРАКТЕРИСТИКИ", "", ""])
            analytics_data.append(["", "", ""])

            # Уровни финансовой грамотности
            analytics_data.append(["Распределение по уровню финансовой грамотности", "", ""])
            for level, count in report["Финансовые характеристики"]["Уровни финансовой грамотности"].items():
                analytics_data.append([level, int(count), f"{float(count)/len(personas)*100:.1f}%"])
            analytics_data.append(["", "", ""])

            # Доверие к банкам
            analytics_data.append(["Распределение по уровню доверия к банкам", "", ""])
            for trust, count in report["Финансовые характеристики"]["Доверие к банкам"].items():
                analytics_data.append([trust, int(count), f"{float(count)/len(personas)*100:.1f}%"])
            analytics_data.append(["", "", ""])

            # Отношение к кредитам
            analytics_data.append(["Распределение по отношению к кредитам", "", ""])
            for attitude, count in report["Финансовые характеристики"]["Отношение к кредитам"].items():
                analytics_data.append([attitude, int(count), f"{float(count)/len(personas)*100:.1f}%"])
            analytics_data.append(["", "", ""])

            # Создаем DataFrame для аналитики
            analytics_df = pd.DataFrame(analytics_data)

            # Подготовка сводки по вопросам
            question_analysis_data = []
            question_analysis_data.append(["АНАЛИЗ ОТВЕТОВ НА ВОПРОСЫ", "", "", ""])
            question_analysis_data.append(["Вопрос", "Тема", "Количество ответов", "Средняя длина (символы)"])

            for qa in report["Аналитика ответов"]:
                question_analysis_data.append([
                    qa["Вопрос"],
                    qa.get("Тема", "общие"),
                    qa["Количество ответов"],
                    qa.get("Средняя длина ответа (символы)", 0)
                ])

            question_analysis_df = pd.DataFrame(question_analysis_data)

            # Создаем объект BytesIO для сохранения Excel файла в памяти
            output = io.BytesIO()

            # Экспорт всех таблиц в один Excel файл
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                wide_df.to_excel(writer, sheet_name='Респонденты_и_ответы', index=False)
                answers_df.to_excel(writer, sheet_name='Все_ответы', index=False)
                personas_df.to_excel(writer, sheet_name='Респонденты', index=False)
                questions_df.to_excel(writer, sheet_name='Вопросы', index=False)
                analytics_df.to_excel(writer, sheet_name='Демография', index=False, header=False)
                question_analysis_df.to_excel(writer, sheet_name='Анализ_вопросов', index=False, header=False)

            # Сброс указателя на начало файла
            output.seek(0)
            return output
        except Exception as e:
            raise ValueError(f"Ошибка при экспорте в Excel: {str(e)}")

    def export_to_json(self, personas: List[Dict], questions: List[Dict], answers: List[Dict]) -> io.BytesIO:
        """
        Экспорт результатов в JSON файл

        Args:
            personas: Список словарей с персонами
            questions: Список словарей с вопросами
            answers: Список словарей с ответами

        Returns:
            io.BytesIO с JSON файлом
        """
        try:
            # Генерируем отчет
            report = self.analyze_results(personas, questions, answers)

            # Создаем структуру данных
            result = {
                "personas": personas,
                "questions": questions,
                "answers": answers,
                "report": report,
                "generated_at": datetime.now().isoformat(),
                "settings": {
                    "api_key_claude": "***РЕДАКТИРОВАНО***",
                    "api_key_openai": "***РЕДАКТИРОВАНО***" if self.api_key_openai else None,
                }
            }

            # Создаем объект BytesIO для сохранения JSON файла
            output = io.BytesIO()
            output.write(json.dumps(result, ensure_ascii=False, indent=2, cls=NumpyEncoder).encode('utf-8'))
            output.seek(0)
            return output
        except Exception as e:
            raise ValueError(f"Ошибка при экспорте в JSON: {str(e)}")

    def visualize_demographics(self, personas) -> plt.Figure:
        """
        Создание визуализаций демографических данных

        Args:
            personas: Список словарей с персонами

        Returns:
            matplotlib Figure с визуализацией
        """
        # Создаем DataFrame из персон
        persona_df = pd.DataFrame([
            {
                "Пол": p["Пол"],
                "Возраст": p["Возраст"],
                "Регион": p["Регион"],
                "Образование": p["Образование"],
                "Уровень финансовой грамотности": p.get("Финансовый профиль", {}).get("Уровень финансовой грамотности", "средний"),
                "Доверие к банкам": p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Доверие к банкам", "среднее"),
                "Отношение к кредитам": p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Отношение к кредитам", "нейтральное"),
                "Отношение к риску": p.get("Финансовый профиль", {}).get("Отношение к финансам", {}).get("Отношение к риску", "умеренный")
            }
            for p in personas
        ])

        # Настройка подграфиков
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Демографический и финансовый анализ респондентов', fontsize=16)

        # Распределение по полу
        gender_counts = persona_df['Пол'].value_counts()
        axes[0, 0].pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90)
        axes[0, 0].set_title('Распределение по полу')

        # Распределение по возрасту
        sns.histplot(persona_df['Возраст'], kde=True, ax=axes[0, 1])
        axes[0, 1].set_title('Распределение по возрасту')
        axes[0, 1].set_xlabel('Возраст')
        axes[0, 1].set_ylabel('Количество')

        # Распределение по регионам
        region_counts = persona_df['Регион'].value_counts().head(8)
        sns.barplot(x=region_counts.index, y=region_counts.values, ax=axes[0, 2])
        axes[0, 2].set_title('Распределение по регионам (топ 8)')
        axes[0, 2].set_xlabel('Регион')
        axes[0, 2].set_ylabel('Количество')
        axes[0, 2].tick_params(axis='x', rotation=45)

        # Распределение по уровню финансовой грамотности
        literacy_counts = persona_df['Уровень финансовой грамотности'].value_counts()
        sorted_literacy = pd.Series(
            [literacy_counts.get(level, 0) for level in ['отсутствие знаний', 'начинающий', 'средний', 'продвинутый', 'эксперт']],
            index=['отсутствие знаний', 'начинающий', 'средний', 'продвинутый', 'эксперт']
        )
        sns.barplot(x=sorted_literacy.index, y=sorted_literacy.values, ax=axes[1, 0])
        axes[1, 0].set_title('Уровень финансовой грамотности')
        axes[1, 0].set_xlabel('Уровень')
        axes[1, 0].set_ylabel('Количество')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # Доверие к банкам
        trust_counts = persona_df['Доверие к банкам'].value_counts()
        sorted_trust = pd.Series(
            [trust_counts.get(level, 0) for level in ['низкое', 'среднее', 'высокое']],
            index=['низкое', 'среднее', 'высокое']
        )
        sns.barplot(x=sorted_trust.index, y=sorted_trust.values, ax=axes[1, 1])
        axes[1, 1].set_title('Доверие к банкам')
        axes[1, 1].set_xlabel('Уровень доверия')
        axes[1, 1].set_ylabel('Количество')

        # Отношение к кредитам
        loan_counts = persona_df['Отношение к кредитам'].value_counts()
        sorted_loan = pd.Series(
            [loan_counts.get(level, 0) for level in ['негативное', 'нейтральное', 'позитивное']],
            index=['негативное', 'нейтральное', 'позитивное']
        )
        sns.barplot(x=sorted_loan.index, y=sorted_loan.values, ax=axes[1, 2])
        axes[1, 2].set_title('Отношение к кредитам')
        axes[1, 2].set_xlabel('Отношение')
        axes[1, 2].set_ylabel('Количество')

        # Настройка макета
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        return fig

def run_generation_pipeline(api_key_claude, api_key_openai, questions_file, personas, output_format='json',
                           max_workers=3, api_preference=None, visualize=True,
                           reviews_file=None, use_enhanced=True):
    """
    Основной пайплайн генерации данных с указанными персонами и поддержкой многопоточности

    Args:
        api_key_claude: API ключ для Anthropic Claude
        api_key_openai: API ключ для OpenAI (опционально)
        questions_file: Данные Excel файла с вопросами
        personas: Список словарей с персонами
        output_format: 'json' или 'excel'
        max_workers: Максимальное количество параллельных рабочих процессов
        api_preference: Предпочтительное API ('claude' или 'openai')
        visualize: Создавать ли визуализации
        reviews_file: Данные файла с отзывами о банках (опционально)
        use_enhanced: Использовать ли расширенную генерацию с поведенческими факторами

    Returns:
        Tuple (Результаты, Данные для загрузки)
    """
    try:
        # Создаем экземпляр маркетплейса
        marketplace = RespondentsMarketplace(api_key_claude, api_key_openai)

        # Загружаем вопросы
        questions = marketplace.load_questions(questions_file)

        # Если указан файл с отзывами о банках, загружаем его
        if reviews_file:
            marketplace.load_bank_reviews(reviews_file)

        # Генерируем ответы
        st.info(f"Генерация ответов для {len(personas)} респондентов на {len(questions)} вопросов...")
        all_answers = marketplace.run_generation_batch(
            personas, questions, max_workers=max_workers,
            api_preference=api_preference, use_enhanced=use_enhanced
        )

        # Генерируем отчет
        report = marketplace.analyze_results(personas, questions, all_answers)

        # Сохраняем результаты в соответствующем формате
        download_data = None
        if output_format == 'excel':
            download_data = marketplace.export_to_excel(personas, questions, all_answers)
            file_ext = '.xlsx'
        else:
            download_data = marketplace.export_to_json(personas, questions, all_answers)
            file_ext = '.json'

        # Визуализация
        fig = None
        if visualize:
            fig = marketplace.visualize_demographics(personas)

        results = {
            "personas": personas,
            "questions": questions,
            "answers": all_answers,
            "report": report,
            "fig": fig,
            "file_ext": file_ext
        }

        return results, download_data
    except Exception as e:
        st.error(f"Ошибка в процессе генерации: {str(e)}")
        raise e

def save_uploaded_config(config_data):
    """Сохранение конфигурации в сессии Streamlit"""
    st.session_state['saved_config'] = config_data

def load_saved_config():
    """Загрузка сохраненной конфигурации из сессии Streamlit"""
    if 'saved_config' in st.session_state:
        return st.session_state['saved_config']
    return None

def display_persona_editor(persona_id, marketplace, initial_persona=None):
    """
    Отображение редактора персоны в Streamlit

    Args:
        persona_id: Уникальный ID для персоны
        marketplace: Экземпляр RespondentsMarketplace
        initial_persona: Опциональные начальные значения персоны

    Returns:
        Словарь с данными персоны
    """
    # Ключи для хранения состояния в session_state
    persona_key = f"persona_state_{persona_id}"
    randomize_key = f"randomize_{persona_id}"
    
    # Инициализация состояния для кнопки рандомизации
    if randomize_key not in st.session_state:
        st.session_state[randomize_key] = False
    
    # Обработка состояния кнопки рандомизации
    if st.session_state.get(randomize_key):
        # Генерируем новую персону, если кнопка была нажата
        initial_persona = marketplace.generate_persona()
        st.session_state[persona_key] = initial_persona
        st.session_state[randomize_key] = False
    # Обработка начального состояния персоны
    elif initial_persona is None:
        if persona_key in st.session_state:
            initial_persona = st.session_state[persona_key]
        else:
            initial_persona = marketplace.generate_persona()
            st.session_state[persona_key] = initial_persona
    
    st.markdown(f"### Респондент #{persona_id}")

    cols_main = st.columns(2)

    with cols_main[0]:
        with st.expander("Демография", expanded=True):
            gender = st.selectbox(
                "Пол:",
                options=['Мужской', 'Женский'],
                index=0 if initial_persona['Пол'] == 'Мужской' else 1,
                key=f"gender_{persona_id}"
            )

            age = st.slider(
                "Возраст:",
                min_value=18,
                max_value=80,
                value=initial_persona['Возраст'],
                key=f"age_{persona_id}"
            )

            region = st.selectbox(
                "Регион:",
                options=marketplace.regions,
                index=marketplace.regions.index(initial_persona['Регион']) if initial_persona['Регион'] in marketplace.regions else 0,
                key=f"region_{persona_id}"
            )

            # Динамический выбор города на основе региона
            cities = marketplace.cities.get(region, ["Не указан"])
            city_index = cities.index(initial_persona['Город']) if initial_persona['Город'] in cities else 0
            city = st.selectbox(
                "Город:",
                options=cities,
                index=city_index,
                key=f"city_{persona_id}"
            )

            profession = st.selectbox(
                "Профессия:",
                options=marketplace.professions,
                index=marketplace.professions.index(initial_persona['Профессия']) if initial_persona['Профессия'] in marketplace.professions else 0,
                key=f"profession_{persona_id}"
            )

            education = st.selectbox(
                "Образование:",
                options=marketplace.education_levels,
                index=marketplace.education_levels.index(initial_persona['Образование']) if initial_persona['Образование'] in marketplace.education_levels else 0,
                key=f"education_{persona_id}"
            )

            family_status = st.selectbox(
                "Семейное положение:",
                options=marketplace.family_statuses,
                index=marketplace.family_statuses.index(initial_persona['Семейное положение']) if initial_persona['Семейное положение'] in marketplace.family_statuses else 0,
                key=f"family_status_{persona_id}"
            )

            income = st.selectbox(
                "Доход:",
                options=marketplace.income_brackets,
                index=marketplace.income_brackets.index(initial_persona['Доход']) if initial_persona['Доход'] in marketplace.income_brackets else 0,
                key=f"income_{persona_id}"
            )

            children = st.slider(
                "Количество детей:",
                min_value=0,
                max_value=8,
                value=initial_persona['Количество детей'],
                key=f"children_{persona_id}"
            )

            hobbies = st.multiselect(
                "Увлечения:",
                options=marketplace.hobby_options,
                default=initial_persona['Увлечения'],
                key=f"hobbies_{persona_id}"
            )

    with cols_main[1]:
        with st.expander("Финансовый профиль", expanded=True):
            fin_profile = initial_persona.get('Финансовый профиль', {})

            literacy_level = st.selectbox(
                "Уровень финансовой грамотности:",
                options=marketplace.financial_literacy_levels,
                index=marketplace.financial_literacy_levels.index(fin_profile.get('Уровень финансовой грамотности', 'средний')) if fin_profile.get('Уровень финансовой грамотности', 'средний') in marketplace.financial_literacy_levels else 2,
                key=f"literacy_{persona_id}"
            )

            st.markdown("**Используемые финансовые продукты:**")

            used_products = fin_profile.get('Используемые продукты', {})
            fin_products = {}

            cols_products = st.columns(2)
            with cols_products[0]:
                fin_products["Дебетовая карта"] = st.checkbox(
                    "Дебетовая карта",
                    value=used_products.get("Дебетовая карта", False),
                    key=f"debit_card_{persona_id}"
                )
                fin_products["Кредитная карта"] = st.checkbox(
                    "Кредитная карта",
                    value=used_products.get("Кредитная карта", False),
                    key=f"credit_card_{persona_id}"
                )
                fin_products["Потребительский кредит"] = st.checkbox(
                    "Потребительский кредит",
                    value=used_products.get("Потребительский кредит", False),
                    key=f"loan_{persona_id}"
                )
                fin_products["Ипотека"] = st.checkbox(
                    "Ипотека",
                    value=used_products.get("Ипотека", False),
                    key=f"mortgage_{persona_id}"
                )

            with cols_products[1]:
                fin_products["Вклад"] = st.checkbox(
                    "Вклад",
                    value=used_products.get("Вклад", False),
                    key=f"deposit_{persona_id}"
                )
                fin_products["Инвестиции"] = st.checkbox(
                    "Инвестиции",
                    value=used_products.get("Инвестиции", False),
                    key=f"investments_{persona_id}"
                )
                fin_products["Страхование"] = st.checkbox(
                    "Страхование",
                    value=used_products.get("Страхование", False),
                    key=f"insurance_{persona_id}"
                )

            st.markdown("**Отношение к финансам:**")

            fin_attitudes = fin_profile.get('Отношение к финансам', {})

            bank_trust = st.selectbox(
                "Доверие к банкам:",
                options=marketplace.bank_trust_levels,
                index=marketplace.bank_trust_levels.index(fin_attitudes.get('Доверие к банкам', 'среднее')) if fin_attitudes.get('Доверие к банкам', 'среднее') in marketplace.bank_trust_levels else 1,
                key=f"trust_{persona_id}"
            )

            loan_attitude = st.selectbox(
                "Отношение к кредитам:",
                options=marketplace.loan_attitudes,
                index=marketplace.loan_attitudes.index(fin_attitudes.get('Отношение к кредитам', 'нейтральное')) if fin_attitudes.get('Отношение к кредитам', 'нейтральное') in marketplace.loan_attitudes else 1,
                key=f"loan_attitude_{persona_id}"
            )

            risk_attitude = st.selectbox(
                "Отношение к риску:",
                options=marketplace.risk_attitudes,
                index=marketplace.risk_attitudes.index(fin_attitudes.get('Отношение к риску', 'умеренный')) if fin_attitudes.get('Отношение к риску', 'умеренный') in marketplace.risk_attitudes else 1,
                key=f"risk_{persona_id}"
            )

            financial_behavior = st.selectbox(
                "Модель финансового поведения:",
                options=marketplace.financial_behaviors,
                index=marketplace.financial_behaviors.index(fin_attitudes.get('Модель финансового поведения', 'прагматичный')) if fin_attitudes.get('Модель финансового поведения', 'прагматичный') in marketplace.financial_behaviors else 2,
                key=f"behavior_{persona_id}"
            )

    # Кнопка для генерации случайных значений с использованием session_state
    if st.button("🎲 Случайные значения", key=f"randomize_button_{persona_id}"):
        # Устанавливаем флаг в session_state, что нужно сгенерировать новую персону
        st.session_state[randomize_key] = True
        # Возвращаем текущую персону, новая будет создана при следующей перерисовке
        return st.session_state[persona_key]

    # Собираем данные персоны
    persona = {
        "Пол": gender,
        "Возраст": age,
        "Регион": region,
        "Город": city,
        "Профессия": profession,
        "Образование": education,
        "Семейное положение": family_status,
        "Количество детей": children,
        "Доход": income,
        "Увлечения": hobbies,
        "Финансовый профиль": {
            "Уровень финансовой грамотности": literacy_level,
            "Используемые продукты": fin_products,
            "Отношение к финансам": {
                "Доверие к банкам": bank_trust,
                "Отношение к кредитам": loan_attitude,
                "Отношение к риску": risk_attitude,
                "Модель финансового поведения": financial_behavior
            }
        }
    }

    # Дополняем финансовый профиль при необходимости
    if 'Финансовые знания' in fin_profile:
        persona['Финансовый профиль']['Финансовые знания'] = fin_profile['Финансовые знания']
    else:
        # Если нет, создаем новые
        persona['Финансовый профиль']['Финансовые знания'] = {
            "Словарный запас": marketplace.knowledge_base.get_vocabulary_for_level(literacy_level, 15),
            "Заблуждения": marketplace.knowledge_base.get_misconceptions_for_level(literacy_level, 3)
        }

    if 'Финансовые цели' in fin_profile:
        persona['Финансовый профиль']['Финансовые цели'] = fin_profile['Финансовые цели']
    else:
        persona['Финансовый профиль']['Финансовые цели'] = marketplace.knowledge_base.get_random_financial_goals(2)

    if 'Поведенческие паттерны' in fin_profile:
        persona['Финансовый профиль']['Поведенческие паттерны'] = fin_profile['Поведенческие паттерны']
    else:
        persona['Финансовый профиль']['Поведенческие паттерны'] = marketplace.knowledge_base.get_behavior_patterns(financial_behavior)

    # Применяем расширение через EnhancedFinancialRespondent
    enhanced_persona = marketplace.enhanced_respondent.enhance_persona(persona)
    
    # Сохраняем финальную версию персоны в session_state
    st.session_state[persona_key] = enhanced_persona

    return enhanced_persona

def display_results(results):
    """
    Отображение результатов генерации

    Args:
        results: Словарь с результатами генерации
    """
    report = results["report"]

    st.markdown("## Результаты генерации синтетических ответов")

    # Отображаем основную статистику
    with st.expander("Общая статистика", expanded=True):
        stats = report["Общая статистика"]

        cols = st.columns(3)
        with cols[0]:
            st.metric("Количество респондентов", stats["Количество респондентов"])
        with cols[1]:
            st.metric("Количество вопросов", stats["Количество вопросов"])
        with cols[2]:
            st.metric("Количество ответов", stats["Количество ответов"])

        st.subheader("Использованные токены")
        cols_tokens = st.columns(2)
        with cols_tokens[0]:
            st.metric("Claude", stats["API токенов использовано (Claude)"])
        with cols_tokens[1]:
            st.metric("OpenAI", stats["API токенов использовано (OpenAI)"])

    # Демографические визуализации
    if results.get("fig"):
        with st.expander("Визуализация данных", expanded=True):
            st.pyplot(results["fig"])

    # Примеры ответов
    with st.expander("Примеры ответов", expanded=True):
        if results["answers"]:
            # Выбираем случайные ответы для отображения
            sample_answers = random.sample(results["answers"], min(3, len(results["answers"])))

            for answer in sample_answers:
                persona_id = answer["persona_id"]
                persona = next((p for p in results["personas"] if p.get("ID", persona_id) == persona_id), results["personas"][persona_id-1])
                literacy_level = persona.get("Финансовый профиль", {}).get("Уровень финансовой грамотности", "средний")

                st.markdown(f"### Респондент #{persona_id}")
                st.markdown(f"**Профиль:** {persona['Пол']}, {persona['Возраст']} лет, {persona['Город']} ({persona['Регион']})")
                st.markdown(f"**Финансовая грамотность:** {literacy_level}")
                st.markdown(f"**Вопрос:** {answer['question']['text']}")
                st.markdown("**Ответ:**")
                st.markdown(f"> {answer['text']}")
                st.markdown("---")

    # Статистика финансовой грамотности
    with st.expander("Распределение по уровню финансовой грамотности", expanded=True):
        literacy_stats = report["Финансовые характеристики"]["Уровни финансовой грамотности"]
        literacy_df = pd.DataFrame([
            {"Уровень": level, "Количество": count}
            for level, count in literacy_stats.items()
        ])

        st.dataframe(literacy_df)

def main():
    # Заголовок и описание
    st.title("Synthetica Financial: Симулятор финансовых респондентов")
    st.markdown("Генерация реалистичных ответов респондентов с разным уровнем финансовой грамотности")

    # Инициализация переменных сессии
    if 'marketplace' not in st.session_state:
        st.session_state.marketplace = None
    if 'personas' not in st.session_state:
        st.session_state.personas = []
    if 'questions' not in st.session_state:
        st.session_state.questions = None
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False

    # Боковая панель для настройки
    with st.sidebar:
        st.header("Настройки")

        # API ключи
        api_key_claude = st.text_input(
            "API ключ Claude:",
            type="password",
            value=st.session_state.get('api_key_claude', ''),
            help="Необходимо указать API ключ для Anthropic Claude"
        )

        api_key_openai = st.text_input(
            "API ключ OpenAI (опционально):",
            type="password",
            value=st.session_state.get('api_key_openai', ''),
            help="Опциональный API ключ для OpenAI"
        )

        # Сохранение API ключей в сессии
        st.session_state.api_key_claude = api_key_claude
        st.session_state.api_key_openai = api_key_openai

        # Файлы с вопросами
        questions_file = st.file_uploader(
            "Загрузить Excel с вопросами",
            type=["xlsx", "xls"],
            help="Выберите файл Excel с вопросами"
        )

        if questions_file is not None:
            try:
                # Создаем временный экземпляр маркетплейса для загрузки вопросов,
                # используя текущие API ключи из интерфейса
                temp_marketplace = RespondentsMarketplace(
                    api_key_claude=api_key_claude,
                    api_key_openai=api_key_openai if api_key_openai else None
                )
                questions = temp_marketplace.load_questions(questions_file)
                st.session_state.questions = questions
                st.success(f"Загружено {len(questions)} вопросов")
            except Exception as e:
                st.error(f"Ошибка при загрузке вопросов: {str(e)}")
                st.session_state.questions = None

        # Файл с отзывами о банках (опционально)
        reviews_file = st.file_uploader(
            "Загрузить Excel с отзывами о банках (опционально)",
            type=["xlsx", "xls"],
            help="Опционально: выберите файл Excel с отзывами о банках для обогащения контекста"
        )

        # Количество респондентов
        num_respondents = st.slider(
            "Количество респондентов:",
            min_value=1,
            max_value=30,
            value=5
        )

        # Предпочтительное API
        api_preference = st.radio(
            "Предпочтительное API:",
            options=[("Claude (по умолчанию)", "claude"), ("OpenAI", "openai"), ("Оба API", None)],
            format_func=lambda x: x[0]
        )[1]

        # Количество потоков
        num_threads = st.slider(
            "Количество потоков:",
            min_value=1,
            max_value=10,
            value=3,
            help="Количество одновременных запросов к API"
        )

        # Расширенные настройки
        with st.expander("Расширенные настройки"):
            visualize_data = st.checkbox(
                "Генерировать визуализации",
                value=True
            )

            use_enhanced = st.checkbox(
                "Использовать расширенную генерацию",
                value=True,
                help="Включает когнитивные, эмоциональные и лингвистические факторы для большей реалистичности"
            )

            output_format = st.radio(
                "Формат вывода:",
                options=[("Excel таблица", "excel"), ("JSON", "json")]
            )[1]

            if st.button("Сохранить настройки"):
                config = {
                    'api_key_claude': api_key_claude,
                    'api_key_openai': api_key_openai,
                    'num_respondents': num_respondents,
                    'api_preference': api_preference,
                    'num_threads': num_threads,
                    'visualize': visualize_data,
                    'use_enhanced': use_enhanced,
                    'output_format': output_format
                }
                save_uploaded_config(config)
                st.success("Настройки сохранены")

            # Загрузка сохраненных настроек
            if st.button("Загрузить сохраненные настройки"):
                config = load_saved_config()
                if config:
                    st.success("Настройки загружены")
                    st.rerun()
                else:
                    st.warning("Сохраненные настройки не найдены")

        # Кнопка для генерации редакторов персон
        if st.button("Настроить респондентов", disabled=(not api_key_claude and not api_key_openai)):
            if not api_key_claude and not api_key_openai:
                st.error("Необходим хотя бы один API ключ (Claude или OpenAI)")
            else:
                # Создаем экземпляр маркетплейса
                st.session_state.marketplace = RespondentsMarketplace(
                    api_key_claude=api_key_claude,
                    api_key_openai=api_key_openai if api_key_openai else None
                )

                # Генерируем персоны
                st.session_state.personas = [
                    st.session_state.marketplace.generate_persona() for _ in range(num_respondents)
                ]
                st.session_state.show_results = False

    # Основная область
    if st.session_state.marketplace and st.session_state.personas:
        if not st.session_state.show_results:
            st.header("Настройка респондентов")

            # Отображаем редакторы персон
            updated_personas = []
            for i, persona in enumerate(st.session_state.personas):
                updated_persona = display_persona_editor(i+1, st.session_state.marketplace, persona)
                updated_personas.append(updated_persona)
                st.markdown("---")

            # Обновляем персоны
            st.session_state.personas = updated_personas

            # Кнопка запуска генерации
            if st.button("Запустить генерацию", disabled=st.session_state.questions is None):
                if st.session_state.questions is None:
                    st.error("Необходимо загрузить файл с вопросами")
                else:
                    with st.spinner("Генерация ответов..."):
                        try:
                            results, download_data = run_generation_pipeline(
                                api_key_claude=api_key_claude,
                                api_key_openai=api_key_openai if api_key_openai else None,
                                questions_file=questions_file,
                                personas=st.session_state.personas,
                                output_format=output_format,
                                max_workers=num_threads,
                                api_preference=api_preference,
                                visualize=visualize_data,
                                reviews_file=reviews_file,
                                use_enhanced=use_enhanced
                            )

                            st.session_state.results = results
                            st.session_state.download_data = download_data
                            st.session_state.show_results = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при генерации: {str(e)}")
        else:
            # Отображение результатов
            display_results(st.session_state.results)

            # Кнопка загрузки файла
            if hasattr(st.session_state, 'download_data') and st.session_state.download_data is not None:
                file_ext = st.session_state.results.get("file_ext", ".xlsx")
                st.download_button(
                    label=f"Скачать результаты ({file_ext})",
                    data=st.session_state.download_data,
                    file_name=f"financial_responses{file_ext}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_ext == ".xlsx" else "application/json"
                )

            # Кнопка для возврата к настройкам
            if st.button("Вернуться к настройкам"):
                st.session_state.show_results = False
                st.rerun()
    else:
        # Информация о форматах файлов
        st.header("Информация о форматах файлов")

        st.markdown("""
        ### Формат Excel файла с вопросами:
        Файл должен содержать следующие колонки:
        - **id** - уникальный идентификатор вопроса (опционально)
        - **question** - текст вопроса (обязательно)
        - **type** - тип вопроса: 'open', 'single', 'multiple' (опционально, по умолчанию 'open')
        - **topic** - тема вопроса: 'кредиты', 'карты', 'вклады', 'инвестиции', 'общие', 'онлайн-сервисы' (опционально)
        - **options** - варианты ответов через запятую (для типов 'single' и 'multiple')
        - **context** - дополнительный контекст для вопроса (опционально)
        """)

        st.markdown("""
        ### Формат Excel файла с отзывами о банках (опционально):
        Файл должен содержать следующие колонки:
        - **bank** или **банк** - название банка
        - **text**, **текст** или **отзыв** - текст отзыва
        - **rating**, **оценка** или **рейтинг** - оценка (обычно от 1 до 5)
        - **date** или **дата** - дата отзыва (опционально)

        Загрузка и анализ отзывов о банках позволит обогатить ответы респондентов более реалистичной информацией.
        """)

        st.markdown("""
        ### Уровни финансовой грамотности:
        - **отсутствие знаний** - практически не знаком с банковскими услугами и финансовыми инструментами
        - **начинающий** - имеет базовые знания (банковские карты, простые вклады)
        - **средний** - понимает основные финансовые инструменты, имеет опыт использования кредитов
        - **продвинутый** - хорошо разбирается в банковских продуктах, имеет опыт инвестирования
        - **эксперт** - глубоко понимает финансовые процессы, активно использует сложные финансовые инструменты
        """)

        st.markdown("""
        ### Модели финансового поведения:
        - **избегающий риска** - консервативный подход к финансам, предпочитает надежность
        - **импульсивный** - спонтанные финансовые решения, часто без детального анализа
        - **прагматичный** - взвешенный подход, тщательно сравнивает условия перед принятием решений
        - **осознанный минималист** - тщательно выбирает на что тратить деньги, избегает лишних трат
        - **статусный** - важен престиж и премиальность финансовых услуг
        """)

        st.markdown("""
        ### Расширенные психологические и лингвистические факторы:
        При использовании расширенной генерации система учитывает следующие дополнительные факторы:
        - **Когнитивные искажения** - эффект якоря, избегание потерь, эффект необратимых затрат и т.д.
        - **Эмоциональные факторы** - финансовая тревога, стыд, гордость, фатализм и т.д.
        - **Лингвистические особенности** - региональная лексика, слова-паразиты, сленг, типичные ошибки
        - **Жизненный контекст** - жизненные события, сезонные факторы, экономическая ситуация
        - **Непоследовательность** - модель усталости, изменение точки зрения, противоречивые утверждения
        - **Социальная желательность** - преувеличение доходов, сокрытие долгов, рационализация трат
        """)

if __name__ == "__main__":
    main()
