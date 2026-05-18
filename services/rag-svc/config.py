"""Конфигурация rag-svc."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    def __init__(self) -> None:
        load_dotenv()
        self._load()

    def _load(self) -> None:
        self.port: int = int(os.getenv("PORT", 5000))
        self.database_url: str = os.getenv("DATABASE_URL", "").strip()
        self.redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
        self.geo_service_url: str = os.getenv("GEO_SERVICE_URL", "http://geo-service:5000").strip()

        # OpenRouter
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
        self.openrouter_model: str = os.getenv("OPENROUTER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct").strip()
        self.openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000").strip()
        self.openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "AIConsultTyumen").strip()
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", 1800))
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.3))

        # RAG (pgvector)
        self.docs_root: Path = Path(os.getenv("DOCS_ROOT", "/app/docs")).resolve()
        self.embedding_model_name: str = os.getenv(
            "EMBEDDING_MODEL_NAME",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        self.embedding_dim: int = int(os.getenv("EMBEDDING_DIM", 384))
        self.rag_table_name: str = os.getenv("RAG_TABLE_NAME", "rag_chunks").strip()
        self.rag_top_k: int = int(os.getenv("RAG_TOP_K", 4))

        # Семантический кэш
        self.semantic_cache_ttl_s: int = int(os.getenv("SEMANTIC_CACHE_TTL_S", 24 * 3600))
        self.semantic_cache_enabled: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "1") != "0"

    def validate(self) -> bool:
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY не установлен")
        if not self.database_url:
            raise ValueError("DATABASE_URL не указан")
        return True

    def __repr__(self) -> str:
        return f"Config(model={self.openrouter_model}, docs={self.docs_root})"
