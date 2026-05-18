"""Контракт ответа от rag-svc, доступный в монолите без зависимости от LlamaIndex.

В rag-svc эти же модели живут в `agents/base.py`. Здесь — урезанная версия
с from_dict для парсинга HTTP-ответа.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentType(str, Enum):
    PAYOUTS = "payouts"
    ACTIONS = "actions_now"
    LAW = "law_explanations"
    DOCS = "docs_help"
    SMALLTALK = "small_talk"
    GEO = "geo"


AGENT_LABELS = {
    AgentType.PAYOUTS: "Выплаты и компенсации",
    AgentType.ACTIONS: "Действия прямо сейчас",
    AgentType.LAW: "Нормативные разъяснения",
    AgentType.DOCS: "Подготовка документов",
    AgentType.SMALLTALK: "Поддерживающий диалог",
    AgentType.GEO: "Карта и местоположение",
}


@dataclass
class AISource:
    document: str
    excerpt: str
    location: str = ""

    def to_dict(self) -> dict:
        return {"document": self.document, "excerpt": self.excerpt, "location": self.location}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AISource":
        return cls(
            document=str(data.get("document") or ""),
            excerpt=str(data.get("excerpt") or ""),
            location=str(data.get("location") or ""),
        )


@dataclass
class AIResponse:
    answer: str
    agent_types: List[AgentType] = field(default_factory=list)
    sources: List[AISource] = field(default_factory=list)
    notes: Optional[str] = None
    suggested_questions: List[str] = field(default_factory=list)
    suggest_operator: bool = False

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "agentTypes": [a.value for a in self.agent_types],
            "agentLabels": [AGENT_LABELS.get(a, a.value) for a in self.agent_types],
            "sources": [s.to_dict() for s in self.sources],
            "notes": self.notes,
            "suggestedQuestions": self.suggested_questions,
            "suggestOperator": self.suggest_operator,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIResponse":
        agent_types: List[AgentType] = []
        for raw in data.get("agentTypes") or []:
            try:
                agent_types.append(AgentType(raw))
            except ValueError:
                continue
        return cls(
            answer=str(data.get("answer") or ""),
            agent_types=agent_types,
            sources=[AISource.from_dict(s) for s in (data.get("sources") or [])],
            notes=data.get("notes"),
            suggested_questions=list(data.get("suggestedQuestions") or []),
            suggest_operator=bool(data.get("suggestOperator")),
        )
