"""Мультиагентный AI сервис на базе RAG и OpenRouter."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Union

from agents.base import AgentType, AIResponse
from agents.rag_agents import BaseRAGAgent, ActionsAgent, DocsAgent, LawAgent, PayoutsAgent, SmallTalkAgent
from agents.router_agent import RouterAgent
from faq_data import get_topic_seed_questions
from config import Config
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
    ) -> None:
        self.config = config
        self.rag_service = rag_service
        self.openrouter_client = openrouter_client
        self.router = RouterAgent(openrouter_client)
        self.agents: Dict[AgentType, Union[BaseRAGAgent, SmallTalkAgent]] = {
            AgentType.PAYOUTS: PayoutsAgent(rag_service, openrouter_client),
            AgentType.ACTIONS: ActionsAgent(rag_service, openrouter_client),
            AgentType.LAW: LawAgent(rag_service, openrouter_client),
            AgentType.DOCS: DocsAgent(rag_service, openrouter_client),
            AgentType.SMALLTALK: SmallTalkAgent(openrouter_client),
        }

    def validate_configuration(self) -> bool:
        """Проверяем, что все ключи заданы."""
        return self.config.validate()

    def generate_answer(self, question: str, context: Optional[str] = None) -> AIResponse:
        """
        Определяет подходящих агентов, собирает их ответы и возвращает объединённый результат.
        """
        # Сначала проверяем маршрут - smalltalk не требует валидации
        selected_agents = self.router.route(question, context)
        
        # Если это не smalltalk, проверяем валидность вопроса
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
            results.append(agent.run(question, history=context))

        if not results:
            raise RuntimeError("Не удалось подобрать подходящего агента для обработки запроса")

        return self._merge_results(results)

    def _merge_results(self, responses: Iterable[AIResponse]) -> AIResponse:
        responses = list(responses)
        if len(responses) == 1:
            return responses[0]

        agent_types: List[AgentType] = []
        for response in responses:
            agent_types.extend(response.agent_types)
        unique_agent_types = list(dict.fromkeys(agent_types))

        suggestions = self._merge_suggestions(responses)

        if all(response.notes == "need_more_context" for response in responses):
            combined = self._merge_clarification_answers(responses)
            return AIResponse(
                answer=combined,
                agent_types=unique_agent_types,
                sources=[],
                notes="need_more_context",
                suggested_questions=suggestions,
            )

        merged_sources = self._merge_sources(responses)
        combined_answer = "\n\n".join(response.answer.strip() for response in responses)
        return AIResponse(
            answer=combined_answer,
            agent_types=unique_agent_types,
            sources=merged_sources,
            suggested_questions=suggestions,
        )

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


