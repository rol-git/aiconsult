"""Мультиагентный AI сервис на базе RAG, OpenRouter и GeoService."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Union

from agents.base import AGENT_LABELS, AgentType, AIResponse
from agents.geo_agent import GeoAgent
from agents.rag_agents import BaseRAGAgent, ActionsAgent, DocsAgent, LawAgent, PayoutsAgent, SmallTalkAgent
from agents.router_agent import RouterAgent
from faq_data import get_topic_seed_questions
from config import Config
from geo import UserContext, UserLocation
from geo_client import GeoHttpClient
from interfaces import IAIService
from llm.openrouter_client import OpenRouterClient
from rag.rag_service import RAGService


logger = logging.getLogger(__name__)


class MultiAgentConsultantService(IAIService):
    """Оркестратор мультиагентной системы."""

    def __init__(
        self,
        config: Config,
        rag_service: RAGService,
        openrouter_client: OpenRouterClient,
        geo_client: GeoHttpClient,
    ) -> None:
        self.config = config
        self.rag_service = rag_service
        self.openrouter_client = openrouter_client
        self.geo_client = geo_client
        self.router = RouterAgent(openrouter_client)
        self.agents: Dict[AgentType, Union[BaseRAGAgent, SmallTalkAgent, GeoAgent]] = {
            AgentType.PAYOUTS: PayoutsAgent(rag_service, openrouter_client),
            AgentType.ACTIONS: ActionsAgent(rag_service, openrouter_client),
            AgentType.LAW: LawAgent(rag_service, openrouter_client),
            AgentType.DOCS: DocsAgent(rag_service, openrouter_client),
            AgentType.SMALLTALK: SmallTalkAgent(openrouter_client),
            AgentType.GEO: GeoAgent(self.geo_client, openrouter_client),
        }

    def validate_configuration(self) -> bool:
        return self.config.validate()

    def generate_answer(
        self,
        question: str,
        context: Optional[str] = None,
        user_context: Optional[UserContext] = None,
    ) -> AIResponse:
        """
        Определяет подходящих агентов, собирает их ответы и возвращает объединённый результат.
        """
        # Гарантируем UserContext и подгружаем гео-карточку, если есть координаты
        user_context = self._prepare_user_context(user_context)

        selected_agents = self.router.route(question, context)

        if AgentType.SMALLTALK not in selected_agents and not self.router.is_valid_question(question):
            seeds = get_topic_seed_questions()
            return AIResponse(
                answer="Не совсем понял запрос. Опишите, что произошло, где случилась ЧС и чем помочь: выплаты, действия, законы или документы.",
                agent_types=[],
                sources=[],
                suggested_questions=seeds[:4],
            )
        if not selected_agents:
            selected_agents = [AgentType.LAW]
        logger.info("Маршрутизатор выбрал агентов: %s", [agent.value for agent in selected_agents])

        results: List[AIResponse] = []
        for agent_type in selected_agents:
            agent = self.agents.get(agent_type)
            if not agent:
                logger.warning("Агент %s не найден в конфигурации", agent_type)
                continue
            try:
                results.append(self._run_agent(agent, agent_type, question, context, user_context))
            except Exception as exc:
                logger.exception("Агент %s упал: %s", agent_type, exc)

        if not results:
            raise RuntimeError("Не удалось подобрать подходящего агента для обработки запроса")

        merged_response = self._merge_results(results, question)
        merged_response.suggest_operator = self._should_suggest_operator(question, context, merged_response)
        return merged_response

    # ---------- внутренности ----------

    def _prepare_user_context(self, user_context: Optional[UserContext]) -> UserContext:
        if user_context is None:
            user_context = UserContext()
        if user_context.location and user_context.geo_card is None:
            try:
                user_context.geo_card = self.geo_client.build_geo_card(user_context.location)
            except Exception as exc:
                logger.warning("build_geo_card failed: %s", exc)
        return user_context

    def _run_agent(
        self,
        agent,
        agent_type: AgentType,
        question: str,
        context: Optional[str],
        user_context: UserContext,
    ) -> AIResponse:
        if agent_type == AgentType.SMALLTALK:
            return agent.run(question, context, user_context=user_context)
        if agent_type == AgentType.GEO:
            return agent.run(question, history=context, user_context=user_context)
        return agent.run(question, history=context, user_context=user_context)

    def _should_suggest_operator(self, question: str, context: Optional[str], response: AIResponse) -> bool:
        operator_keywords = [
            "не могу найти", "не понимаю", "не получается", "помогите", "срочно",
            "жалоба", "не отвечают", "не помогают", "обман", "мошенничество",
            "нарушение", "незаконно", "требую", "прокуратура", "суд",
            "оператор", "человек", "живой человек", "специалист",
        ]
        question_lower = question.lower()
        has_operator_keywords = any(keyword in question_lower for keyword in operator_keywords)

        repeated_questions = False
        if context:
            question_count = context.lower().count("?")
            repeated_questions = question_count >= 3

        needs_clarification = response.notes == "need_more_context"

        if "оператор" in question_lower or "человек" in question_lower or "специалист" in question_lower:
            return True
        if has_operator_keywords and needs_clarification:
            return True
        if repeated_questions and needs_clarification:
            return True
        return False

    def _merge_results(self, responses: Iterable[AIResponse], question: str) -> AIResponse:
        responses = list(responses)
        if len(responses) == 1:
            return responses[0]

        agent_types: List[AgentType] = []
        for response in responses:
            agent_types.extend(response.agent_types)
        unique_agent_types = list(dict.fromkeys(agent_types))

        suggestions = self._merge_suggestions(responses)
        merged_sources = self._merge_sources(responses)
        any_suggest_operator = any(r.suggest_operator for r in responses)

        if all(response.notes == "need_more_context" for response in responses):
            combined = self._merge_clarification_answers(responses)
            return AIResponse(
                answer=combined,
                agent_types=unique_agent_types,
                sources=[],
                notes="need_more_context",
                suggested_questions=suggestions,
            )

        combined_answer = self._synthesize_answers(question, responses)

        return AIResponse(
            answer=combined_answer,
            agent_types=unique_agent_types,
            sources=merged_sources,
            suggested_questions=suggestions,
            suggest_operator=any_suggest_operator,
        )

    def _synthesize_answers(self, question: str, responses: List[AIResponse]) -> str:
        """LLM-синтез: сшиваем ответы нескольких агентов в один связный текст."""
        try:
            sections = []
            for r in responses:
                labels = ", ".join(AGENT_LABELS.get(t, t.value) for t in r.agent_types) or "консультант"
                sections.append(f"### Ответ агента «{labels}»\n{r.answer.strip()}")
            joined = "\n\n".join(sections)
            system = (
                "Ты — финальный редактор ответов мультиагентной системы для жителей Тюменской области. "
                "Тебе дают несколько фрагментов ответа от разных агентов (выплаты, действия, документы, гео и т.п.). "
                "Сшей их в ОДИН связный ответ на русском в Markdown:\n"
                "  - Убери дубли и противоречия (выбирай более конкретное утверждение).\n"
                "  - Сохрани все маршрутные ссылки и контакты ДОСЛОВНО (Яндекс.Карты / 2ГИС / телефоны).\n"
                "  - Структура свободная, но без меток вроде «Агент X сказал».\n"
                "  - Если в фрагментах есть просьба разрешить геолокацию — мягко повтори её в финале.\n"
                "  - Объём — не больше 12 абзацев, без лишней воды."
            )
            user_msg = (
                f"Исходный вопрос пользователя:\n{question.strip()}\n\n"
                f"Фрагменты ответов агентов:\n{joined}\n\n"
                "Верни единый итоговый ответ."
            )
            return self.openrouter_client.complete(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
            ).strip()
        except Exception as exc:
            logger.warning("LLM-синтез не удался, делаю простой merge: %s", exc)
            return "\n\n".join(r.answer.strip() for r in responses)

    def _merge_sources(self, responses: Iterable[AIResponse]):
        seen = set()
        merged = []
        for response in responses:
            for source in response.sources:
                key = (source.document, source.location, source.excerpt)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(source)
        return merged

    def _merge_clarification_answers(self, responses: Iterable[AIResponse]) -> str:
        seen = set()
        parts = []
        for response in responses:
            text = response.answer.strip()
            if text and text not in seen:
                seen.add(text)
                parts.append(text)
        return "\n\n".join(parts)

    def _merge_suggestions(self, responses: Iterable[AIResponse]) -> List[str]:
        seen = set()
        collected: List[str] = []
        for response in responses:
            for question in response.suggested_questions:
                if question and question not in seen:
                    seen.add(question)
                    collected.append(question)
                if len(collected) >= 4:
                    return collected
        return collected
