"""Реализации специализированных RAG-агентов."""

from __future__ import annotations

import json
import logging
import random
from typing import List, Optional

from agents.base import (
    AGENT_FOLLOWUPS,
    AGENT_HINTS,
    AGENT_LABELS,
    AgentType,
    AIResponse,
    AISource,
    STRICT_POLICY_SNIPPET,
)
from faq_data import get_faq_questions, get_topic_seed_questions
from llm.openrouter_client import OpenRouterClient
from rag.rag_service import RAGChunk, RAGService


logger = logging.getLogger(__name__)


class BaseRAGAgent:
    """Базовая реализация агента, использующего RAG + OpenRouter."""

    def __init__(
        self,
        agent_type: AgentType,
        rag_service: RAGService,
        client: OpenRouterClient,
        *,
        answer_style: str,
    ) -> None:
        self.agent_type = agent_type
        self.rag_service = rag_service
        self.client = client
        self.answer_style = answer_style

    def _build_system_prompt(self) -> str:
        return (
            f"Ты консультант по вопросам ЧС в Тюменской области и РФ. "
            f"{self.answer_style.strip()} "
            "Отвечай уверенно, чётко и по делу. "
            "НЕ пиши откуда взята информация, НЕ упоминай 'документы', 'фрагменты', 'общая информация' и подобное. "
            "Просто давай полезный ответ пользователю как эксперт. "
            "Оформляй ответ на русском языке в формате Markdown."
        )

    def _build_user_prompt(self, question: str, chunks: List[RAGChunk], history: Optional[str]) -> str:
        context_blocks = []
        for idx, chunk in enumerate(chunks, start=1):
            context_blocks.append(f"---\n{chunk.text}")
        history_block = f"Контекст беседы:\n{history.strip()}\n\n" if history else ""
        context_section = "\n\n".join(context_blocks) if context_blocks else ""
        
        prompt = f"{history_block}Вопрос: {question.strip()}"
        if context_section:
            prompt += f"\n\nСправочная информация:\n{context_section}"
        
        return prompt

    def _to_sources(self, chunks: List[RAGChunk]) -> List[AISource]:
        sources: List[AISource] = []
        seen_docs = set()
        for chunk in chunks:
            # Убираем дубликаты по документу
            doc_key = (chunk.document, chunk.location)
            if doc_key in seen_docs:
                continue
            seen_docs.add(doc_key)
            
            # Короткая выдержка
            excerpt = chunk.text.strip()
            if len(excerpt) > 150:
                excerpt = excerpt[:147] + "…"
            sources.append(AISource(document=chunk.document, location=chunk.location, excerpt=excerpt))
        return sources

    def run(self, question: str, *, history: Optional[str] = None) -> AIResponse:
        chunks = self.rag_service.retrieve(question, agent_hint=AGENT_HINTS[self.agent_type])
        
        user_prompt = self._build_user_prompt(question, chunks, history)
        
        if chunks:
            needs_context, reason = self._needs_more_context(question, chunks)
            if needs_context:
                hint = self._build_clarification_hint(reason)
                user_prompt += (
                    "\n\nЕсли данных недостаточно, в конце ответа мягко попроси пользователя предоставить: "
                    f"{hint}. Оформи это как один уточняющий вопрос."
                )
        
        answer = self.client.complete(
            [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        suggestions = self._generate_followups(question, answer)
        return AIResponse(
            answer=answer.strip(),
            agent_types=[self.agent_type],
            sources=[],
            suggested_questions=suggestions,
        )

    def _needs_more_context(self, question: str, chunks: List[RAGChunk]) -> tuple[bool, str]:
        if not chunks:
            return True, "documents_missing"
        total_chars = sum(len(chunk.text) for chunk in chunks)
        unique_docs = len({chunk.document for chunk in chunks})
        has_attributes = self._has_key_attributes(question)
        short_question = len(question.strip()) < 80

        if len(chunks) == 1 and total_chars < 600:
            return True, "single_small_chunk"
        if unique_docs == 1 and total_chars < 700:
            return True, "not_enough_sources"
        if not has_attributes and short_question:
            return True, "need_details"
        if total_chars < 400:
            return True, "low_volume"
        return False, ""

    def _has_key_attributes(self, question: str) -> bool:
        normalized = question.lower()
        keywords = [
            "район",
            "город",
            "посел",
            "село",
            "улиц",
            "дом",
            "квартира",
            "семья",
            "пенсион",
            "инвалид",
            "ип",
            "ферм",
            "акт",
            "справк",
            "документ",
        ]
        return any(token in normalized for token in keywords)

    def _clarification_response(self, reason: str) -> AIResponse:
        message_map = {
            "documents_missing": "Подскажите, пожалуйста, где произошла ЧС, кто пострадал и какой документ нужен — так смогу открыть нужные материалы.",
            "single_small_chunk": "Чтобы подсказать точнее, напишите район, дату ЧС и есть ли уже акт обследования.",
            "not_enough_sources": "Расскажите подробнее: какой населённый пункт, кого затронула ситуация и какая помощь требуется.",
            "need_details": "Уточните, где именно произошла ЧС и кого она затронула — тогда смогу подобрать конкретные выплаты и действия.",
            "low_volume": "Добавьте ключевые факты (район, статус пострадавшего, вид ущерба), чтобы подобрать верный алгоритм.",
        }
        message = message_map.get(reason, message_map["need_details"])
        return AIResponse(
            answer=message,
            agent_types=[self.agent_type],
            sources=[],
            suggested_questions=self._build_clarification_questions(),
        )

    def _build_clarification_hint(self, reason: str) -> str:
        mapping = {
            "single_small_chunk": "район ЧС, дату, кто пострадал и какой документ нужен",
            "not_enough_sources": "название населённого пункта, статус пострадавших и вид помощи",
            "need_details": "район, тип ЧС, кого затронула ситуация и какие документы уже есть",
            "low_volume": "район/город, статус пострадавшего (семья, пенсионер, ИП) и вид ущерба",
            "documents_missing": "место ЧС, тип ущерба и какие выплаты/документы хотите оформить",
        }
        return mapping.get(reason, mapping["need_details"])

    def _build_clarification_questions(self) -> List[str]:
        pool = get_faq_questions(tags=[self.agent_type.value], limit=3)
        if not pool:
            pool = get_faq_questions(limit=3)
        random.shuffle(pool)
        selected = pool[:3]
        return [self._format_question_text(q) for q in selected]

    def _build_followup_questions(self) -> List[str]:
        faq = get_faq_questions(tags=[self.agent_type.value], limit=5)
        random.shuffle(faq)
        return [self._format_question_text(q) for q in faq[:3]]

    def _format_question_text(self, text: str) -> str:
        return text.strip()

    def _generate_followups(self, question: str, answer: str) -> List[str]:
        prompt = (
            "Предложи 3 новых вопроса (5-10 слов каждый), которые пользователь может задать консультанту дальше. "
            "Вопросы должны ДОПОЛНЯТЬ тему, а НЕ повторять исходный вопрос. "
            "Формулируй от первого лица: 'Какие...', 'Куда...', 'Как...', 'Сколько...'. "
            "Верни только JSON-массив строк."
        )
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Пользователь спросил: {question.strip()[:150]}\n\n"
                    "Предложи 3 ДРУГИХ вопроса по теме ЧС/выплат/документов (JSON-массив). "
                    "Вопросы должны отличаться от исходного!"
                ),
            },
        ]
        try:
            raw = self.client.complete(messages, temperature=0.5, max_tokens=200)
            parsed = self._parse_question_list(raw)
            if parsed:
                # Фильтруем похожие на исходный вопрос
                question_lower = question.lower()
                filtered = []
                for q in parsed:
                    q_lower = q.lower()
                    # Пропускаем если слишком похож на исходный
                    if self._is_similar(question_lower, q_lower):
                        continue
                    filtered.append(q)
                if filtered:
                    return [self._format_question_text(q) for q in filtered[:3]]
        except Exception as exc:
            logger.warning("Не удалось сгенерировать follow-up через LLM: %s", exc)
        return self._build_followup_questions()

    def _is_similar(self, text1: str, text2: str) -> bool:
        """Проверяет, похожи ли два текста."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return False
        common = words1 & words2
        # Если больше 60% слов совпадает - считаем похожими
        similarity = len(common) / min(len(words1), len(words2))
        return similarity > 0.6

    def _parse_question_list(self, raw: str) -> List[str]:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            pass
        questions = []
        for line in raw.splitlines():
            cleaned = line.strip().lstrip("-•").strip()
            if cleaned:
                questions.append(cleaned)
        return questions


class PayoutsAgent(BaseRAGAgent):
    def __init__(self, rag_service: RAGService, client: OpenRouterClient) -> None:
        super().__init__(
            agent_type=AgentType.PAYOUTS,
            rag_service=rag_service,
            client=client,
            answer_style=(
                "Твоя специализация — выплаты, компенсации, порядок оформления материальной помощи. "
                "Структурируй ответ по блокам «Что положено», «Куда обращаться», «Документы», «Сроки», "
                "если это уместно."
            ),
        )


class ActionsAgent(BaseRAGAgent):
    def __init__(self, rag_service: RAGService, client: OpenRouterClient) -> None:
        super().__init__(
            agent_type=AgentType.ACTIONS,
            rag_service=rag_service,
            client=client,
            answer_style=(
                "Ты отвечаешь за немедленные инструкции. Начинай с краткого плана действий, "
                "далее давай пошаговый алгоритм и телефоны экстренных служб, если они есть в документах."
            ),
        )


class LawAgent(BaseRAGAgent):
    def __init__(self, rag_service: RAGService, client: OpenRouterClient) -> None:
        super().__init__(
            agent_type=AgentType.LAW,
            rag_service=rag_service,
            client=client,
            answer_style=(
                "Ты специализируешься на разъяснении норм права и ссылках на статьи законов. "
                "Сначала дай краткое резюме, затем перечисли нормативные акты с точными пунктами."
            ),
        )


class DocsAgent(BaseRAGAgent):
    def __init__(self, rag_service: RAGService, client: OpenRouterClient) -> None:
        super().__init__(
            agent_type=AgentType.DOCS,
            rag_service=rag_service,
            client=client,
            answer_style=(
                "Ты помогаешь готовить тексты заявлений, актов и жалоб. "
                "Объясни, какие разделы должны быть в документе, и предложи черновик шаблона на основе контекста."
            ),
        )


SMALLTALK_RESPONSES = {
    "greeting": [
        "Здравствуйте! Я рядом, чтобы помочь по любым вопросам ЧС в Тюменской области. Расскажите, что случилось или что хотите уточнить.",
        "Добрый день! Готов подсказать по выплатам, действиям при угрозе и документам. Что вас сейчас волнует?",
    ],
    "thanks": [
        "Всегда рад помочь. Если появятся новые вопросы или нужна будет детализация — просто напишите.",
        "Спасибо за обратную связь! Могу подсказать что-то ещё: выплаты, эвакуация, документы?",
    ],
    "about": [
        "Я виртуальный консультант, который отвечает только по документам Тюменской области. Подскажу, какие меры положены и куда обращаться.",
        "Работаю как справочник по ЧС: рассказываю про компенсации, алгоритмы действий и подготовку документов. Что интересует?",
    ],
    "default": [
        "Я здесь, чтобы помочь с вопросами по ЧС. Можете описать ситуацию, и мы вместе найдём решение.",
        "Если нужна помощь по выплатам, эвакуации или оформлению документов — напишите детали, и я подскажу порядок действий.",
    ],
}

SMALLTALK_PATTERNS = {
    "greeting": ["привет", "здравствуй", "добрый день", "добрый вечер", "доброго"],
    "thanks": ["спасибо", "благодарю", "выручил"],
    "about": ["кто ты", "что умеешь", "расскажи о себе", "как работаешь"],
}


class SmallTalkAgent:
    """Агент для приветствий и общих вопросов — генерирует ответы через LLM."""

    SYSTEM_PROMPT = (
        "Ты дружелюбный консультант по вопросам чрезвычайных ситуаций в Тюменской области. "
        "Отвечай кратко, тепло и по-человечески. Если пользователь здоровается — поздоровайся в ответ. "
        "Если спрашивает как дела — ответь что всё хорошо и ты готов помочь. "
        "Если благодарит — поблагодари в ответ. Если спрашивает кто ты — представься как цифровой консультант. "
        "В конце мягко предложи задать вопрос по теме ЧС: выплаты, эвакуация, документы, компенсации. "
        "Отвечай на русском языке, 2-3 предложения максимум."
    )

    def __init__(self, client: Optional[OpenRouterClient] = None) -> None:
        self.agent_type = AgentType.SMALLTALK
        self.client = client

    def run(self, question: str, history: Optional[str] = None) -> AIResponse:
        answer = self._generate_response(question, history)
        if self._is_first_turn(history):
            suggestions = get_topic_seed_questions()
        else:
            suggestions = self._generate_dynamic_suggestions(question, answer)
        return AIResponse(
            answer=answer,
            agent_types=[self.agent_type],
            sources=[],
            notes=None,
            suggested_questions=suggestions,
        )

    def _generate_response(self, question: str, history: Optional[str]) -> str:
        if not self.client:
            return self._fallback_response(question)
        
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        if history:
            messages.append({"role": "user", "content": f"История диалога:\n{history}"})
        messages.append({"role": "user", "content": question.strip()})
        
        try:
            answer = self.client.complete(messages, temperature=0.7, max_tokens=200)
            return answer.strip()
        except Exception as exc:
            logger.warning("SmallTalkAgent LLM error: %s", exc)
            return self._fallback_response(question)

    def _fallback_response(self, question: str) -> str:
        category = self._classify(question)
        responses = SMALLTALK_RESPONSES.get(category, SMALLTALK_RESPONSES["default"])
        return random.choice(responses)

    def _classify(self, question: str) -> str:
        text = question.lower().strip()
        for category, tokens in SMALLTALK_PATTERNS.items():
            if any(token in text for token in tokens):
                return category
        return "default"

    def _is_first_turn(self, history: Optional[str]) -> bool:
        if not history:
            return True
        normalized = history.lower()
        return "консультант:" not in normalized

    def _generate_dynamic_suggestions(self, question: str, answer: str) -> List[str]:
        if not self.client:
            return get_topic_seed_questions()
        prompt = (
            "Предложи до трёх коротких вопросов о ЧС, выплатах, действиях или документах. "
            "Формат — JSON-массив строк, никаких пояснений."
        )
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Вопрос пользователя:\n{question.strip()}\n\n"
                    f"Твой ответ:\n{answer.strip()}\n\n"
                    "Верни JSON-массив строк с дальнейшими вопросами."
                ),
            },
        ]
        try:
            raw = self.client.complete(messages, temperature=0.4, max_tokens=160)
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()][:3]
        except Exception as exc:
            logger.warning("SmallTalkAgent follow-ups fallback: %s", exc)
        return get_topic_seed_questions()


