"""Базовые сущности для мультиагентной системы."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AgentType(str, Enum):
    PAYOUTS = "payouts"
    ACTIONS = "actions_now"
    LAW = "law_explanations"
    DOCS = "docs_help"
    SMALLTALK = "small_talk"


AGENT_LABELS = {
    AgentType.PAYOUTS: "Выплаты и компенсации",
    AgentType.ACTIONS: "Действия прямо сейчас",
    AgentType.LAW: "Нормативные разъяснения",
    AgentType.DOCS: "Подготовка документов",
    AgentType.SMALLTALK: "Поддерживающий диалог",
}


AGENT_HINTS = {
    AgentType.PAYOUTS: "выплаты, компенсации, материальная помощь, критерии и порядок получения",
    AgentType.ACTIONS: "инструкции немедленных действий, эвакуация, телефоны горячих линий, меры безопасности",
    AgentType.LAW: "толкование нормативных актов, ссылки на законы и постановления",
    AgentType.DOCS: "шаблоны заявлений, жалоб, актов обследования, структура документов",
    AgentType.SMALLTALK: "неформальное приветствие, благодарность, просьба рассказать о сервисе",
}

AGENT_FOLLOWUPS = {
    AgentType.PAYOUTS: [
        "Какой статус у пострадавшего (семья, одинокий пенсионер, ИП)?",
        "Есть ли акт обследования жилья или справка от администрации?",
        "В каком районе/населённом пункте произошла ЧС?",
        "Нужна компенсация за жильё, имущество или временное размещение?",
    ],
    AgentType.ACTIONS: [
        "Где именно происходит ЧС (район, населённый пункт)?",
        "Нужно помочь с эвакуацией людей, животных или техники?",
        "Угроза затопления только прогнозируется или вода уже идёт?",
        "Нужны телефоны экстренных служб или алгоритм эвакуации?",
    ],
    AgentType.LAW: [
        "Какой документ или статью хотите уточнить?",
        "Вопрос касается федеральных норм или региональных актов Тюменской области?",
        "Это касается граждан, организаций или органов власти?",
        "Нужны сроки рассмотрения или порядок обжалования?",
    ],
    AgentType.DOCS: [
        "Какой документ требуется: заявление, жалоба, акт, служебная записка?",
        "Для какой организации или ведомства готовите документ?",
        "Есть ли исходные данные (ФИО, адрес, реквизиты ЧС)?",
        "Нужно ли включить ссылки на акты обследования или фотофиксацию?",
    ],
}


STRICT_POLICY_SNIPPET = (
    "Ты обязан опираться исключительно на предоставленные фрагменты документов. "
    "Если нужной информации нет в фрагментах, прямо скажи об этом и предложи уточнить вопрос после "
    "обращения к официальным источникам. Категорически запрещено придумывать данные или ссылаться на внешние источники."
)


@dataclass
class AISource:
    document: str
    excerpt: str
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "document": self.document,
            "excerpt": self.excerpt,
            "location": self.location,
        }


@dataclass
class AIResponse:
    answer: str
    agent_types: List[AgentType] = field(default_factory=list)
    sources: List[AISource] = field(default_factory=list)
    notes: Optional[str] = None
    suggested_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "agentTypes": [agent.value for agent in self.agent_types],
            "agentLabels": [AGENT_LABELS.get(agent, agent.value) for agent in self.agent_types],
            "sources": [source.to_dict() for source in self.sources],
            "notes": self.notes,
            "suggestedQuestions": self.suggested_questions,
        }


