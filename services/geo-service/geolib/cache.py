"""Простой in-memory TTL-кеш с потокобезопасной перезагрузкой."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    fetched_at: float
    ttl_s: float


class TTLCache:
    """Кеш по строковому ключу с разным TTL на ключ. Перегружается лениво при истечении."""

    def __init__(self) -> None:
        self._entries: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._global_lock:
            lock = self._locks.get(key)
            if not lock:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def get_or_load(
        self,
        key: str,
        loader: Callable[[], T],
        ttl_s: float,
    ) -> T:
        """Вернуть значение из кеша или загрузить через loader при истечении TTL."""
        entry = self._entries.get(key)
        if entry and (time.time() - entry.fetched_at) < entry.ttl_s:
            return entry.value

        lock = self._lock_for(key)
        with lock:
            entry = self._entries.get(key)
            if entry and (time.time() - entry.fetched_at) < entry.ttl_s:
                return entry.value
            try:
                value = loader()
            except Exception:
                if entry:
                    return entry.value
                raise
            self._entries[key] = CacheEntry(value=value, fetched_at=time.time(), ttl_s=ttl_s)
            return value

    def peek(self, key: str) -> Optional[CacheEntry]:
        return self._entries.get(key)

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)
