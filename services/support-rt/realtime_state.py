"""
Хранилище онлайн-присутствия (presence) в Redis.

In-memory dict'ы из старого socket_events.py заменены ключами в Redis,
чтобы несколько реплик процесса видели одно и то же состояние подключений.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from redis import Redis

logger = logging.getLogger(__name__)


SOCKET_TTL_SECONDS = 24 * 60 * 60  # 24h — соответствует времени жизни JWT


class PresenceStore:
    """Учёт подключённых клиентов: user_id → set socket_id + индексы онлайн-пользователей."""

    def __init__(self, redis: Redis):
        self._redis = redis

    # --- ключи ---

    @staticmethod
    def _sockets_key(role: str, user_id: str) -> str:
        return f"ws:{role}:{user_id}:sockets"

    @staticmethod
    def _online_set_key(role: str) -> str:
        return f"ws:{role}:online"

    @staticmethod
    def _sid_key(sid: str) -> str:
        return f"ws:sid:{sid}"

    # --- основные операции ---

    def register_socket(self, user_id: str, role: str, sid: str) -> None:
        """Зарегистрировать сокет пользователя/оператора."""
        sockets_key = self._sockets_key(role, user_id)
        online_key = self._online_set_key(role)
        sid_key = self._sid_key(sid)

        pipe = self._redis.pipeline()
        pipe.sadd(sockets_key, sid)
        pipe.expire(sockets_key, SOCKET_TTL_SECONDS)
        pipe.sadd(online_key, user_id)
        pipe.hset(sid_key, mapping={"user_id": user_id, "role": role})
        pipe.expire(sid_key, SOCKET_TTL_SECONDS)
        pipe.execute()

    def unregister_socket(self, sid: str) -> Optional[Tuple[str, str]]:
        """Удалить socket из presence, вернуть (user_id, role) если был известен."""
        sid_key = self._sid_key(sid)
        info = self._redis.hgetall(sid_key)
        if not info:
            return None

        user_id = info.get("user_id") or info.get(b"user_id".decode())
        role = info.get("role") or info.get(b"role".decode())
        if not user_id or not role:
            self._redis.delete(sid_key)
            return None

        sockets_key = self._sockets_key(role, user_id)
        online_key = self._online_set_key(role)

        pipe = self._redis.pipeline()
        pipe.srem(sockets_key, sid)
        pipe.scard(sockets_key)
        pipe.delete(sid_key)
        _, remaining, _ = pipe.execute()

        if remaining == 0:
            pipe = self._redis.pipeline()
            pipe.delete(sockets_key)
            pipe.srem(online_key, user_id)
            pipe.execute()

        return user_id, role

    def online_users(self, role: str) -> List[str]:
        return list(self._redis.smembers(self._online_set_key(role)))

    def count_online(self, role: str) -> int:
        return self._redis.scard(self._online_set_key(role))

    def clear_all(self) -> None:
        """Удалить весь presence — используется в тестах и при ручной чистке."""
        for key in self._redis.scan_iter(match="ws:*"):
            self._redis.delete(key)
