"""
Инициализация подключения к базе данных Postgres.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase, Session

engine = None
_session_factory: Optional[scoped_session] = None


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""


def init_engine(database_url: str):
    """
    Создает движок и фабрику сессий.

    Args:
        database_url: Строка подключения к БД
    """
    global engine, _session_factory

    engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )

    _session_factory = scoped_session(
        sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    )

    return engine


def get_session() -> Session:
    """Возвращает текущую сессию SQLAlchemy."""
    if _session_factory is None:
        raise RuntimeError("DB session factory is not initialized. Call init_engine first.")
    return _session_factory()


def remove_session(exception: Optional[BaseException] = None) -> None:
    """Закрывает текущую сессию после запроса."""
    if _session_factory is not None:
        _session_factory.remove()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для безопасной работы с сессиями.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

