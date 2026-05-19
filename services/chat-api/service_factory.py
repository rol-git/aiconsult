from __future__ import annotations

"""Service factory монолита (после волны 4).

После выделения rag-svc монолит больше не держит RAG/LLM/embedding модель.
IAIService теперь — это HTTP-клиент в rag-svc (см. ai_client.RemoteAIService).
"""

import logging

from redis import Redis

from ai_client import RemoteAIService
from config import Config
from geo_client import GeoHttpClient
from interfaces import IAIService
from realtime_state import PresenceStore

logger = logging.getLogger(__name__)


class ServiceFactory:
    """Сборка зависимостей монолита (IoC)."""

    def __init__(self) -> None:
        self._config: Config | None = None
        self._ai_service: IAIService | None = None
        self._redis: Redis | None = None
        self._presence: PresenceStore | None = None
        self._geo_client: GeoHttpClient | None = None

    def create_config(self) -> Config:
        if self._config is None:
            logger.info("Инициализация конфигурации...")
            self._config = Config()
            self._config.validate()
            logger.info("Конфигурация загружена: %s", self._config)
        return self._config

    def create_redis(self) -> Redis:
        if self._redis is None:
            config = self.create_config()
            logger.info("Инициализация Redis-клиента: %s", config.redis_url)
            self._redis = Redis.from_url(config.redis_url, decode_responses=True)
        return self._redis

    def create_presence_store(self) -> PresenceStore:
        if self._presence is None:
            self._presence = PresenceStore(self.create_redis())
        return self._presence

    def create_geo_client(self) -> GeoHttpClient:
        if self._geo_client is None:
            config = self.create_config()
            logger.info("Инициализация GeoHttpClient: %s", config.geo_service_url)
            self._geo_client = GeoHttpClient(config.geo_service_url)
        return self._geo_client

    def create_ai_service(self) -> IAIService:
        if self._ai_service is None:
            config = self.create_config()
            logger.info("Инициализация RemoteAIService → %s", config.rag_service_url)
            self._ai_service = RemoteAIService(config.rag_service_url)
        return self._ai_service

    def reset(self) -> None:
        if self._redis is not None:
            self._redis.close()
        self._config = None
        self._ai_service = None
        self._redis = None
        self._presence = None
        self._geo_client = None


_factory_instance: ServiceFactory | None = None


def get_service_factory() -> ServiceFactory:
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ServiceFactory()
    return _factory_instance
