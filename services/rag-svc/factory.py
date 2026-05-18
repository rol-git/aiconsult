"""Сервис-фабрика rag-svc: собирает RAG + LLM + GeoClient + AIService."""

from __future__ import annotations

import logging
from typing import Optional

from redis import Redis

from ai_service import MultiAgentConsultantService
from config import Config
from geo_client import GeoHttpClient
from interfaces import IAIService
from llm.openrouter_client import OpenRouterClient
from rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class Factory:
    def __init__(self) -> None:
        self._config: Optional[Config] = None
        self._rag: Optional[RAGService] = None
        self._llm: Optional[OpenRouterClient] = None
        self._geo: Optional[GeoHttpClient] = None
        self._ai: Optional[IAIService] = None
        self._redis: Optional[Redis] = None

    def config(self) -> Config:
        if self._config is None:
            self._config = Config()
            self._config.validate()
            logger.info("Config: %s", self._config)
        return self._config

    def rag(self) -> RAGService:
        if self._rag is None:
            self._rag = RAGService(self.config())
        return self._rag

    def llm(self) -> OpenRouterClient:
        if self._llm is None:
            c = self.config()
            self._llm = OpenRouterClient(
                api_key=c.openrouter_api_key,
                model=c.openrouter_model,
                base_url=c.openrouter_base_url,
                site_url=c.openrouter_site_url,
                app_name=c.openrouter_app_name,
                temperature=c.llm_temperature,
                max_tokens=c.llm_max_tokens,
            )
        return self._llm

    def geo(self) -> GeoHttpClient:
        if self._geo is None:
            self._geo = GeoHttpClient(self.config().geo_service_url)
        return self._geo

    def ai(self) -> IAIService:
        if self._ai is None:
            c = self.config()
            self._ai = MultiAgentConsultantService(
                config=c,
                rag_service=self.rag(),
                openrouter_client=self.llm(),
                geo_client=self.geo(),
            )
            self._ai.validate_configuration()
        return self._ai

    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.config().redis_url, decode_responses=True)
        return self._redis


_factory: Optional[Factory] = None


def get_factory() -> Factory:
    global _factory
    if _factory is None:
        _factory = Factory()
    return _factory
