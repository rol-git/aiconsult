"""
Набор часто задаваемых вопросов по ЧС и помощь вспомогательными подсказками.
"""

from __future__ import annotations

import random
from typing import List, Optional

FAQ_ITEMS = [
    {"question": "Какие выплаты положены пострадавшим от паводка?", "tags": ["payouts"]},
    {"question": "Куда обращаться за компенсацией ущерба?", "tags": ["payouts"]},
    {"question": "Какие документы нужны для получения выплаты?", "tags": ["docs", "payouts"]},
    {"question": "Что делать если вода подходит к дому?", "tags": ["actions"]},
    {"question": "Какие телефоны экстренных служб в Тюмени?", "tags": ["actions"]},
    {"question": "Как получить временное жильё при эвакуации?", "tags": ["actions", "payouts"]},
    {"question": "Как правильно написать заявление на помощь?", "tags": ["docs"]},
    {"question": "Как обжаловать отказ в компенсации?", "tags": ["docs", "law"]},
    {"question": "Какие законы регулируют выплаты при ЧС?", "tags": ["law"]},
    {"question": "Какой размер компенсации при затоплении?", "tags": ["payouts"]},
    {"question": "Нужен ли акт обследования для выплат?", "tags": ["payouts", "law"]},
    {"question": "Куда жаловаться если отказали в помощи?", "tags": ["actions", "docs"]},
    {"question": "Сколько ждать выплату после подачи заявления?", "tags": ["payouts"]},
    {"question": "Кто имеет право на материальную помощь?", "tags": ["payouts", "law"]},
]

TOPIC_SEED_QUESTIONS = [
    {"label": "Выплаты", "question": "Какие выплаты положены при затоплении?", "tags": ["payouts"]},
    {"label": "Действия", "question": "Что делать при угрозе подтопления?", "tags": ["actions"]},
    {"label": "Законы", "question": "Какие законы регулируют компенсации?", "tags": ["law"]},
    {"label": "Документы", "question": "Какие документы нужны для выплаты?", "tags": ["docs"]},
]


def get_faq_questions(tags: Optional[List[str]] = None, limit: int = 3) -> List[str]:
    items = FAQ_ITEMS
    if tags:
        normalized_tags = set(tags)
        items = [item for item in FAQ_ITEMS if normalized_tags.intersection(item["tags"])]
    if not items:
        items = FAQ_ITEMS
    items = items.copy()
    random.shuffle(items)
    return [item["question"] for item in items[:limit]]


def get_topic_seed_questions() -> List[str]:
    # В UI кнопок-подсказок показываем только сам вопрос (без префиксов "тема: ...").
    return [item["question"] for item in TOPIC_SEED_QUESTIONS]

