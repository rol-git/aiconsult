"""
HTTP-клиент для работы с OpenRouter.
Инкапсулирует авторизацию, логирование и обработку ошибок.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

import httpx


logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Минимальный клиент OpenRouter для чат-комплишенов."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        site_url: str,
        app_name: str,
        temperature: float,
        max_tokens: int,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url
        self.app_name = app_name
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stop: Optional[Iterable[str]] = None,
    ) -> str:
        """
        Вызывает OpenRouter с заданным списком сообщений.
        Возвращает контент первого completion.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if stop:
            payload["stop"] = list(stop)

        logger.debug("Запрос к OpenRouter: %s", json.dumps(payload, ensure_ascii=False)[:500])

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Ошибка HTTP при обращении к OpenRouter")
            raise RuntimeError(f"Ошибка при обращении к OpenRouter: {exc}") from exc

        data = response.json()
        choices = data.get("choices")
        if not choices:
            logger.error("Пустой ответ OpenRouter: %s", data)
            raise RuntimeError("OpenRouter вернул пустой ответ")

        message = choices[0].get("message", {})
        content = (message.get("content") or "").strip()
        if not content:
            logger.error("Пустой контент OpenRouter: %s", data)
            raise RuntimeError("OpenRouter не вернул текст ответа")

        return content

    def close(self) -> None:
        """Закрывает HTTP клиент."""
        self._client.close()


