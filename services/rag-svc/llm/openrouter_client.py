"""
HTTP-клиент для работы с OpenRouter.
Инкапсулирует авторизацию, логирование и обработку ошибок.
"""

from __future__ import annotations

import json
import logging
import time
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
        timeout: float = 120.0,
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
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0, read=timeout, write=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

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
        max_retries: int = 3,
    ) -> str:
        """
        Вызывает OpenRouter с заданным списком сообщений.
        Возвращает контент первого completion.
        Автоматически повторяет запрос при ошибках сети или таймаутах.
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

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                
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
                
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError) as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Экспоненциальный backoff: 1, 2, 4 сек
                    logger.warning(
                        f"Ошибка соединения с OpenRouter (попытка {attempt + 1}/{max_retries}): {exc}. "
                        f"Повтор через {wait_time} сек..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Все попытки подключения к OpenRouter исчерпаны: {exc}")
                    
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP ошибка от OpenRouter: {exc.response.status_code} - {exc.response.text}")
                raise RuntimeError(f"Ошибка API OpenRouter: {exc.response.status_code}") from exc
                
            except httpx.HTTPError as exc:
                last_error = exc
                logger.exception("Неожиданная HTTP ошибка при обращении к OpenRouter")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Ошибка при обращении к OpenRouter: {exc}") from exc

        # Если все попытки исчерпаны
        raise RuntimeError(
            f"Не удалось подключиться к OpenRouter после {max_retries} попыток. "
            f"Проверьте интернет-соединение и доступность openrouter.ai. "
            f"Последняя ошибка: {last_error}"
        )

    def close(self) -> None:
        """Закрывает HTTP клиент."""
        self._client.close()


