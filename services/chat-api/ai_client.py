"""HTTP-клиент к rag-svc. Реализует IAIService."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from ai_models import AIResponse
from geo import UserContext
from interfaces import IAIService

logger = logging.getLogger(__name__)


class RemoteAIService(IAIService):
    """Тонкий клиент в rag-svc, отдающий объект AIResponse."""

    def __init__(self, base_url: str, *, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def validate_configuration(self) -> bool:
        # На уровне монолита нам важно только, что URL задан.
        # Проверка живости rag-svc — через периодический healthcheck в compose.
        return bool(self._base)

    def generate_answer(
        self,
        question: str,
        context: Optional[str] = None,
        user_context: Optional[UserContext] = None,
    ) -> AIResponse:
        payload: dict = {"question": question}
        if context:
            payload["history"] = context
        if user_context and user_context.location:
            payload["userContext"] = {
                "location": user_context.location.to_dict(),
                "addressText": user_context.address_text,
            }
        try:
            resp = httpx.post(
                f"{self._base}/generate_answer",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("rag-svc returned %s: %s", exc.response.status_code, exc.response.text[:200])
            raise
        except Exception as exc:
            logger.exception("rag-svc call failed: %s", exc)
            raise
        return AIResponse.from_dict(data)
