"""Конфигурация support-rt."""

from __future__ import annotations

import os

from dotenv import load_dotenv


class Config:
    def __init__(self) -> None:
        load_dotenv()
        self.port: int = int(os.getenv("PORT", 5000))
        self.database_url: str = os.getenv("DATABASE_URL", "").strip()
        self.redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "super-secret-key")
        self.jwt_expires_minutes: int = int(os.getenv("JWT_EXPIRES_MINUTES", 60 * 24))

    def validate(self) -> bool:
        if not self.database_url:
            raise ValueError("DATABASE_URL не указан")
        return True
