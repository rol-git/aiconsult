"""
Модуль конфигурации приложения.
Принцип SRP (Single Responsibility Principle) - один класс для управления конфигурацией.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """
    Класс для управления конфигурацией приложения.
    Инкапсулирует все настройки в одном месте.
    """
    
    def __init__(self):
        """Инициализация конфигурации из переменных окружения."""
        load_dotenv()
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Загружает настройки из переменных окружения."""
        self.server_port: int = int(os.getenv('SERVER_PORT', 5000))
        self.database_url: str = os.getenv('DATABASE_URL', '').strip()
        self.jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
        self.jwt_expires_minutes: int = int(os.getenv('JWT_EXPIRES_MINUTES', 60 * 24))

        # OpenRouter
        self.openrouter_api_key: str = os.getenv('OPENROUTER_API_KEY', '').strip()
        self.openrouter_base_url: str = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').strip()
        self.openrouter_model: str = os.getenv('OPENROUTER_MODEL', 'meta-llama/Meta-Llama-3.1-70B-Instruct').strip()
        self.openrouter_site_url: str = os.getenv('OPENROUTER_SITE_URL', 'http://localhost:3000').strip()
        self.openrouter_app_name: str = os.getenv('OPENROUTER_APP_NAME', 'AIConsultTyumen').strip()
        self.llm_max_tokens: int = int(os.getenv('LLM_MAX_TOKENS', 1800))
        self.llm_temperature: float = float(os.getenv('LLM_TEMPERATURE', 0.3))

        # RAG / документы
        self.docs_root: Path = Path(os.getenv('DOCS_ROOT', '../docs')).resolve()
        self.rag_storage_path: Path = Path(
            os.getenv('RAG_STORAGE_PATH', './storage/index')
        ).resolve()
        self.chroma_persist_dir: Path = Path(
            os.getenv('CHROMA_PERSIST_DIR', './storage/chroma')
        ).resolve()
        self.chroma_collection: str = os.getenv('CHROMA_COLLECTION', 'tyumen_rag').strip()
        self.embedding_model_name: str = os.getenv(
            'EMBEDDING_MODEL_NAME',
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        )
        self.rag_top_k: int = int(os.getenv('RAG_TOP_K', 4))
    
    def validate(self) -> bool:
        """
        Валидация конфигурации.
        
        Returns:
            bool: True если конфигурация валидна
            
        Raises:
            ValueError: Если обязательные параметры отсутствуют
        """
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY не установлен в переменных окружения")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL не указан в переменных окружения")
        
        if self.server_port < 1 or self.server_port > 65535:
            raise ValueError(f"Неверный порт сервера: {self.server_port}")
        
        return True
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации (без секретных данных)."""
        return (
            f"Config(server_port={self.server_port}, "
            f"model={self.openrouter_model}, "
            f"docs_root='{self.docs_root}')"
        )

