from __future__ import annotations

"""
Фабрика сервисов (Service Factory).
Принцип DIP - создание и связывание зависимостей в одном месте.
Реализует паттерн Factory и Dependency Injection Container.
"""

import logging

from ai_service import MultiAgentConsultantService
from config import Config
from interfaces import IAIService
from llm.openrouter_client import OpenRouterClient
from rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Фабрика для создания и связывания всех сервисов приложения.
    Централизованное управление зависимостями (IoC Container).
    """
    
    def __init__(self):
        """Инициализация фабрики."""
        self._config: Config = None
        self._rag_service: RAGService | None = None
        self._openrouter_client: OpenRouterClient | None = None
        self._ai_service: IAIService = None
    
    def create_config(self) -> Config:
        """
        Создает и валидирует конфигурацию.
        
        Returns:
            Config: Объект конфигурации
        """
        if self._config is None:
            logger.info("Инициализация конфигурации...")
            self._config = Config()
            self._config.validate()
            logger.info(f"Конфигурация загружена: {self._config}")
        
        return self._config
    
    def create_rag_service(self) -> RAGService:
        """Создает и переиспользует RAG сервис."""
        if self._rag_service is None:
            config = self.create_config()
            logger.info("Инициализация RAG сервиса (LlamaIndex + локальные документы)")
            self._rag_service = RAGService(config)
        return self._rag_service

    def create_openrouter_client(self) -> OpenRouterClient:
        """Создает клиента OpenRouter API."""
        if self._openrouter_client is None:
            config = self.create_config()
            logger.info("Инициализация OpenRouter клиента (модель: %s)", config.openrouter_model)
            self._openrouter_client = OpenRouterClient(
                api_key=config.openrouter_api_key,
                model=config.openrouter_model,
                base_url=config.openrouter_base_url,
                site_url=config.openrouter_site_url,
                app_name=config.openrouter_app_name,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
            )
        return self._openrouter_client
    
    def create_ai_service(self) -> IAIService:
        """
        Создает AI сервис со всеми зависимостями.
        
        Returns:
            IAIService: AI сервис
        """
        if self._ai_service is None:
            config = self.create_config()
            rag_service = self.create_rag_service()
            openrouter_client = self.create_openrouter_client()

            logger.info("Инициализация мультиагентного AI сервиса (OpenRouter + RAG)")
            self._ai_service = MultiAgentConsultantService(
                config=config,
                rag_service=rag_service,
                openrouter_client=openrouter_client,
            )
            
            self._ai_service.validate_configuration()
            logger.info("AI сервис успешно инициализирован")
        
        return self._ai_service
    
    def reset(self) -> None:
        """
        Сбрасывает все созданные сервисы.
        Полезно для тестирования или переконфигурации.
        """
        logger.info("Сброс всех сервисов...")
        
        if self._openrouter_client is not None:
            self._openrouter_client.close()
        
        self._config = None
        self._rag_service = None
        self._openrouter_client = None
        self._ai_service = None
        
        logger.info("Все сервисы сброшены")


# Глобальный экземпляр фабрики (Singleton pattern)
_factory_instance: ServiceFactory = None


def get_service_factory() -> ServiceFactory:
    """
    Возвращает глобальный экземпляр фабрики (Singleton).
    
    Returns:
        ServiceFactory: Экземпляр фабрики
    """
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = ServiceFactory()
    
    return _factory_instance

