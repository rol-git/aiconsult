"""Мини-фабрика support-rt: Redis-клиент и PresenceStore."""

from __future__ import annotations

from typing import Optional

from redis import Redis

from config import Config
from realtime_state import PresenceStore


class ServiceFactory:
    def __init__(self) -> None:
        self._config: Optional[Config] = None
        self._redis: Optional[Redis] = None
        self._presence: Optional[PresenceStore] = None

    def create_config(self) -> Config:
        if self._config is None:
            self._config = Config()
            self._config.validate()
        return self._config

    def create_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.create_config().redis_url, decode_responses=True)
        return self._redis

    def create_presence_store(self) -> PresenceStore:
        if self._presence is None:
            self._presence = PresenceStore(self.create_redis())
        return self._presence


_factory: Optional[ServiceFactory] = None


def get_service_factory() -> ServiceFactory:
    global _factory
    if _factory is None:
        _factory = ServiceFactory()
    return _factory
