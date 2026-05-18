"""Простой семантический кэш на Redis.

Сейчас — ключ по точному хешу (question + краткая история). Этого достаточно,
чтобы при пиковом трафике частые повторяющиеся вопросы не доходили до LLM.
Семантический поиск (по эмбеддингу запроса) можно подключить позднее —
точку расширения этот модуль изолирует.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from redis import Redis

logger = logging.getLogger(__name__)


class SemanticCache:
    def __init__(self, redis: Redis, ttl_s: int = 24 * 3600, enabled: bool = True) -> None:
        self._redis = redis
        self._ttl = ttl_s
        self._enabled = enabled

    @staticmethod
    def _key(question: str, history: Optional[str]) -> str:
        h = hashlib.sha256()
        h.update((question or "").strip().lower().encode("utf-8"))
        if history:
            h.update(b"\x00")
            h.update(history.strip().lower().encode("utf-8"))
        return f"rag:ans:{h.hexdigest()}"

    def get(self, question: str, history: Optional[str]) -> Optional[dict]:
        if not self._enabled:
            return None
        try:
            raw = self._redis.get(self._key(question, history))
        except Exception as exc:
            logger.warning("cache get failed: %s", exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def set(self, question: str, history: Optional[str], payload: Any) -> None:
        if not self._enabled:
            return
        try:
            self._redis.setex(self._key(question, history), self._ttl, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.warning("cache set failed: %s", exc)
