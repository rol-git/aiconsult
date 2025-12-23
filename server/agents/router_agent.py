"""Агент-классификатор запросов."""

from __future__ import annotations

import json
import re
from typing import List, Optional

from agents.base import AGENT_LABELS, AgentType
from llm.openrouter_client import OpenRouterClient


KEYWORDS = {
    AgentType.PAYOUTS: [
        "выплат",
        "компенсац",
        "пособ",
        "материальн",
        "денег",
        "финансов",
    ],
    AgentType.ACTIONS: [
        "что делать",
        "эваку",
        "немедлен",
        "прямо сейчас",
        "инструкц",
        "куда звонить",
        "телефон",
    ],
    AgentType.LAW: [
        "закон",
        "постанов",
        "приказ",
        "норматив",
        "статья",
        "право",
    ],
    AgentType.DOCS: [
        "заявлен",
        "жалоб",
        "акт",
        "образец",
        "шаблон",
        "как написать",
    ],
}

SMALLTALK_PATTERNS = [
    r"^привет",
    r"^здравствуй",
    r"^добрый\s*(день|вечер|утро)",
    r"^доброго",
    r"^хай\b",
    r"^хелло",
    r"^hello",
    r"^hi\b",
    r"как дела",
    r"как ты",
    r"как поживаешь",
    r"что нового",
    r"спасибо",
    r"благодарю",
    r"что умеешь",
    r"кто ты",
    r"расскажи о себе",
    r"ты бот",
    r"ты робот",
    r"ты человек",
    r"^пока\b",
    r"до свидания",
    r"^окей\b",
    r"^ок\b",
    r"^понял",
    r"^ясно",
    r"^хорошо\b",
]


class RouterAgent:
    """Сочетает эвристики и LLM-классификацию (нелинейный подход)."""

    def __init__(self, client: OpenRouterClient) -> None:
        self.client = client

    def is_valid_question(self, question: str) -> bool:
        """
        Быстрая фильтрация мусора/оф-топа через LLM.
        Возвращает True, если запрос осмысленный и относится к ЧС/выплатам/действиям/законам/документам.
        """
        normalized = question.strip()
        if len(normalized) < 6:
            return False

        # LLM-проверка
        system_prompt = (
            "Определи, является ли ввод осмысленным вопросом по теме ЧС/выплат/эвакуации/документов/законов "
            "Тюменской области. Ответь строго JSON: {\"ok\": true|false} без текста."
        )
        user_prompt = (
            f"Текст: {normalized}\n\n"
            "Если это бессвязный ввод, набор символов, рекламу или оффтоп (не про ЧС/выплаты/право/документы), "
            "верни ok:false."
        )
        try:
            raw = self.client.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=32,
            )
            data = json.loads(raw)
            return bool(data.get("ok") is True)
        except Exception:
            # В случае ошибки не блокируем пользователя, считаем валидным.
            return True

    def route(self, question: str, history: Optional[str] = None) -> List[AgentType]:
        normalized = question.lower()
        if self._is_smalltalk(normalized):
            return [AgentType.SMALLTALK]
        matches = []
        for agent, tokens in KEYWORDS.items():
            if any(token in normalized for token in tokens):
                matches.append(agent)
        if matches:
            return matches[:2]
        return self._route_with_llm(question, history)

    def _is_smalltalk(self, text: str) -> bool:
        # Сначала проверяем паттерны smalltalk
        matches_smalltalk = any(re.search(pattern, text) for pattern in SMALLTALK_PATTERNS)
        if not matches_smalltalk:
            return False
        
        # Если сообщение длинное или содержит вопросы по теме ЧС - это не просто smalltalk
        topic_indicators = ["выплат", "компенсац", "эвакуац", "затопил", "паводок", "чс", "ущерб", "помощь", "документ", "закон"]
        has_topic_question = any(indicator in text for indicator in topic_indicators)
        is_long = len(text.split()) > 6
        
        # Если есть вопрос по теме или длинное сообщение - не считаем smalltalk
        if has_topic_question or is_long:
            return False
        
        return True

    def _route_with_llm(self, question: str, history: Optional[str]) -> List[AgentType]:
        user_prompt = {
            "role": "user",
            "content": (
                "Тебе нужно определить, каким специализированным консультантам передать запрос.\n"
                f"История (может отсутствовать): {history or 'нет'}\n"
                f"Запрос: {question.strip()}\n\n"
                "Доступные категории: "
                + ", ".join(f"{agent.value}:{AGENT_LABELS[agent]}" for agent in AgentType)
                + ". Верни JSON вида {\"categories\": [\"payouts\", ...]} только по списку."
            ),
        }
        response = self.client.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "Ты маршрутизатор запросов для ИИ консультанта по ЧС. "
                        "Выбирай 1-2 категории из списка и отвечай строго валидным JSON."
                    ),
                },
                user_prompt,
            ],
            temperature=0.0,
        )
        return self._parse_categories(response)

    def _parse_categories(self, raw: str) -> List[AgentType]:
        categories: List[AgentType] = []
        try:
            data = json.loads(raw)
            values = data.get("categories", [])
            if isinstance(values, list):
                categories = self._normalize_list(values)
        except json.JSONDecodeError:
            pattern = re.compile(r"(payouts|actions_now|law_explanations|docs_help)", re.IGNORECASE)
            categories = self._normalize_list(pattern.findall(raw))

        if not categories:
            categories = [AgentType.LAW]
        return categories[:2]

    def _normalize_list(self, values) -> List[AgentType]:
        normalized: List[AgentType] = []
        for value in values:
            if not isinstance(value, str):
                continue
            key = value.strip().lower()
            try:
                normalized.append(AgentType(key))
            except ValueError:
                mapping = {
                    "law": AgentType.LAW,
                    "actions": AgentType.ACTIONS,
                    "docs": AgentType.DOCS,
                    "payments": AgentType.PAYOUTS,
                    "smalltalk": AgentType.SMALLTALK,
                    "small_talk": AgentType.SMALLTALK,
                }
                if key in mapping:
                    normalized.append(mapping[key])
        seen = set()
        result: List[AgentType] = []
        for agent in normalized:
            if agent not in seen:
                seen.add(agent)
                result.append(agent)
        return result


