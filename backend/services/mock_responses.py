"""
Мок-ответы для работы без API ключей
"""
import random
import re
from typing import List


# Примеры вопросов для разных тем
MOCK_QUESTIONS = {
    "programming": [
        "Реализуйте функцию для поиска максимального элемента в массиве.",
        "Напишите функцию для проверки, является ли строка палиндромом.",
        "Реализуйте алгоритм бинарного поиска.",
        "Напишите функцию для вычисления факториала числа.",
        "Реализуйте функцию для сортировки массива методом пузырька.",
    ],
    "algorithms": [
        "Объясните разницу между временной сложностью O(n) и O(n²).",
        "Что такое рекурсия и когда её стоит использовать?",
        "Опишите алгоритм быстрой сортировки (quicksort).",
        "Что такое динамическое программирование?",
        "Объясните принцип работы хеш-таблицы.",
    ],
    "data_structures": [
        "В чем разница между массивом и связным списком?",
        "Объясните принцип работы стека и очереди.",
        "Что такое бинарное дерево поиска?",
        "Опишите структуру данных 'хеш-таблица'.",
        "Когда использовать массив, а когда связный список?",
    ],
    "python": [
        "Что такое генераторы в Python и зачем они нужны?",
        "Объясните разницу между list и tuple.",
        "Что такое декораторы в Python?",
        "Объясните концепцию GIL (Global Interpreter Lock).",
        "В чем разница между методами append() и extend() для списков?",
    ],
}

# Паттерны prompt injection для детекции
INJECTION_PATTERNS = [
    # Прямые просьбы (с вариантами слов)
    r"объясн",        # объясни, объяснить, объяснение
    r"расскаж",       # расскажи, рассказать
    r"помог",         # помоги, помогите, помочь
    r"подскаж",       # подскажи, подсказать
    r"скажи.{0,10}ответ",
    r"правильн.{0,5}ответ",
    r"не\s*знаю",
    r"explain",
    r"tell\s*me",
    r"help",
    r"what\s+is",
    r"how\s+to",
    r"can\s+you",
    
    # Смена роли
    r"забуд",         # забудь, забудьте
    r"ignore",
    r"forget",
    r"ты\s*(теперь|сейчас)",
    r"you\s*(are|will)",
    r"нов.{0,5}роль",
    r"new\s*role",
    r"system",
    r"\[system\]",
    r"<\|",
    r"im_start",
    
    # Манипуляции
    r"разработчик",
    r"developer",
    r"тест.{0,10}режим",
    r"test.{0,5}mode",
    r"проверк.{0,5}систем",
    r"экзаменатор",
    r"учител",
    r"teacher",
    r"professor",
    r"профессор",
    r"ассистент",
    r"assistant",
    r"tutor",
    r"mentor",
    
    # Эмоциональные манипуляции
    r"пожалуйста",
    r"please",
    r"очень\s*нужно",
    r"потерял",
    r"жалоб",
    r"complaint",
    r"умоляю",
    r"поделись",
    r"share",
    r"умн",  # умный, умная
    
    # Технические атаки
    r"системн.{0,5}промпт",
    r"system\s*prompt",
    r"инструкци",
    r"instructions",
    r"override",
    r"command",
    r"prompt",
    r"role",
]

COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in INJECTION_PATTERNS]


def detect_injection(text: str) -> bool:
    """Детектирует prompt injection в тексте"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(text_lower):
            return True
    
    return False


def get_mock_question(topic: str = "programming") -> str:
    """Получить случайный мок-вопрос"""
    questions = MOCK_QUESTIONS.get(topic.lower(), MOCK_QUESTIONS["programming"])
    return random.choice(questions)


def get_mock_answer(question: str) -> str:
    """Получить мок-ответ на вопрос"""
    question_lower = question.lower()
    
    # Ответы на основе типа вопроса
    if "готов" in question_lower or "ready" in question_lower:
        return "Да, готов начать собеседование!"
    
    if "опыт" in question_lower or "experience" in question_lower:
        return "Я работаю с Python уже более 3 лет. Основной опыт связан с разработкой веб-приложений на Django и Flask. Реализовал несколько проектов, включая систему управления задачами с REST API."
    
    if "декоратор" in question_lower or "decorator" in question_lower:
        return "Декораторы в Python - это функции, которые принимают другую функцию в качестве аргумента и расширяют или изменяют её поведение без явного изменения самой функции. Пример: @decorator_function def my_function(): pass"
    
    if "палиндром" in question_lower or "palindrome" in question_lower:
        return "def is_palindrome(s):\n    cleaned = ''.join(s.split()).lower()\n    return cleaned == cleaned[::-1]"
    
    if "список" in question_lower and "кортеж" in question_lower or "list" in question_lower and "tuple" in question_lower:
        return "Основные различия: списки изменяемы (mutable), кортежи неизменяемы (immutable). Списки используют квадратные скобки [], кортежи - круглые (). Списки занимают больше памяти, кортежи быстрее для итерации."
    
    if "two_sum" in question_lower or "два числа" in question_lower:
        return "def two_sum(nums, target):\n    num_map = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in num_map:\n            return [num_map[complement], i]\n        num_map[num] = i\n    return []"
    
    if "реализуйте" in question_lower or "напишите" in question_lower or "implement" in question_lower:
        # Для coding вопросов возвращаем код
        return "def solution():\n    # Решение задачи\n    pass"
    
    # Общий ответ для теоретических вопросов
    return "Это интересный вопрос. Основные моменты: концепция важна для понимания принципов работы системы. Можно рассмотреть различные подходы и их преимущества."


def get_mock_technical_question(topic: str = "python", difficulty: int = 5) -> dict:
    """Получить мок технический вопрос с учетом сложности"""
    
    TECHNICAL_QUESTIONS = {
        "python": {
            1: {"question": "Что такое переменная в Python?", "expected_keywords": ["переменная", "значение", "имя"], "subtopic": "basics"},
            2: {"question": "Какие базовые типы данных есть в Python?", "expected_keywords": ["int", "str", "list", "dict", "bool"], "subtopic": "types"},
            3: {"question": "Чем отличается list от tuple?", "expected_keywords": ["изменяемый", "неизменяемый", "mutable"], "subtopic": "collections"},
            4: {"question": "Что такое генераторы в Python?", "expected_keywords": ["yield", "итератор", "ленивый"], "subtopic": "generators"},
            5: {"question": "Объясните концепцию декораторов в Python.", "expected_keywords": ["функция", "обертка", "wrapper", "@"], "subtopic": "decorators"},
            6: {"question": "Как работает GIL и какие проблемы он создает?", "expected_keywords": ["Global Interpreter Lock", "многопоточность", "CPU"], "subtopic": "concurrency"},
            7: {"question": "Объясните разницу между __new__ и __init__.", "expected_keywords": ["создание", "инициализация", "metaclass"], "subtopic": "oop"},
            8: {"question": "Как работает сборщик мусора в Python?", "expected_keywords": ["reference counting", "gc", "циклы"], "subtopic": "memory"},
            9: {"question": "Что такое метаклассы и когда их использовать?", "expected_keywords": ["type", "класс классов", "создание классов"], "subtopic": "metaclasses"},
            10: {"question": "Как реализовать паттерн синглтон с потокобезопасностью в Python?", "expected_keywords": ["threading", "Lock", "__new__", "decorator"], "subtopic": "patterns"},
        },
        "javascript": {
            1: {"question": "Что такое переменная в JavaScript?", "expected_keywords": ["var", "let", "const"], "subtopic": "basics"},
            5: {"question": "Объясните концепцию замыканий в JavaScript.", "expected_keywords": ["closure", "область видимости", "функция"], "subtopic": "closures"},
            7: {"question": "Как работает Event Loop в JavaScript?", "expected_keywords": ["call stack", "callback queue", "микротаски"], "subtopic": "async"},
            10: {"question": "Объясните прототипное наследование и его отличие от классического.", "expected_keywords": ["prototype", "__proto__", "Object.create"], "subtopic": "oop"},
        },
        "databases": {
            5: {"question": "Что такое индексы в базах данных и как они работают?", "expected_keywords": ["B-tree", "поиск", "производительность"], "subtopic": "indexes"},
            7: {"question": "Объясните принципы ACID в транзакциях.", "expected_keywords": ["Atomicity", "Consistency", "Isolation", "Durability"], "subtopic": "transactions"},
            10: {"question": "Как спроектировать масштабируемую систему с шардированием?", "expected_keywords": ["shard key", "репликация", "консистентность"], "subtopic": "scaling"},
        },
    }
    
    topic_questions = TECHNICAL_QUESTIONS.get(topic, TECHNICAL_QUESTIONS["python"])
    
    # Находим ближайший уровень сложности
    available_difficulties = sorted(topic_questions.keys())
    closest_difficulty = min(available_difficulties, key=lambda x: abs(x - difficulty))
    
    question_data = topic_questions[closest_difficulty]
    
    return {
        "question": question_data["question"],
        "topic": topic,
        "subtopic": question_data["subtopic"],
        "difficulty": closest_difficulty,
        "expected_keywords": question_data["expected_keywords"],
        "hints": [],
        "reference_answer_points": question_data["expected_keywords"]
    }


def get_mock_evaluation(question: str, answer: str) -> dict:
    """Получить мок-оценку ответа"""
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    # КРИТИЧНО: Проверка на prompt injection
    if detect_injection(answer):
        return {
            "score": 0,
            "correctness": 0,
            "completeness": 0,
            "quality": 0,
            "optimality": 0,
            "feedback": "",  # Пустой feedback - не даем подсказок
            "strengths": [],
            "improvements": [],
            "is_injection": True,
        }
    
    # Проверка на пустой/короткий ответ
    if len(answer.strip()) < 10:
        return {
            "score": 0,
            "correctness": 0,
            "completeness": 0,
            "quality": 0,
            "optimality": 0,
            "feedback": "",
            "strengths": [],
            "improvements": [],
        }
    
    # Проверка на skip-ответы
    skip_keywords = ["не знаю", "дальше", "пропустить", "skip", "next", "pass", "idk"]
    if any(kw in answer_lower for kw in skip_keywords):
        return {
            "score": 0,
            "correctness": 0,
            "completeness": 0,
            "quality": 0,
            "optimality": 0,
            "feedback": "",
            "strengths": [],
            "improvements": [],
            "is_skip": True,
        }
    
    # Базовые проверки для нормальных ответов
    has_code = "def " in answer or "function" in answer_lower or "return" in answer_lower
    has_explanation = len(answer) > 50
    has_keywords = any(keyword in answer_lower for keyword in ["массив", "функция", "алгоритм", "array", "function"])
    
    # Подсчет оценки
    score = 50  # Базовая оценка
    if has_code:
        score += 20
    if has_explanation:
        score += 15
    if has_keywords:
        score += 15
    
    score = min(100, max(40, score + random.randint(-10, 10)))  # Добавляем немного случайности
    
    correctness = min(10, score // 10)
    completeness = min(10, (score + 10) // 10)
    quality = min(10, (score + 5) // 10)
    optimality = min(10, (score - 5) // 10)
    
    # Убираем feedback - интервьюер не дает подсказок
    feedback = ""
    
    strengths = []
    improvements = []
    
    return {
        "score": score,
        "correctness": correctness,
        "completeness": completeness,
        "quality": quality,
        "optimality": optimality,
        "feedback": feedback,  # Всегда пустой
        "strengths": strengths,
        "improvements": improvements,
    }
