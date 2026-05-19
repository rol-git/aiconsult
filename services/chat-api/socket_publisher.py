"""Write-only SocketIO publisher для chat-api.

В chat-api нет SocketIO-сервера — за WS отвечает support-rt.
Чтобы из HTTP-роутов отправлять real-time события клиентам (например,
системное сообщение при resolve тикета), используем RedisManager в
режиме write_only. События публикуются в Redis-канал; support-rt их
получает через свой Redis-adapter и эмитит подключённым клиентам.
"""

from __future__ import annotations

import logging
from typing import Optional

import socketio

logger = logging.getLogger(__name__)

_publisher: Optional[socketio.RedisManager] = None


def init(redis_url: str) -> None:
    global _publisher
    if _publisher is None:
        logger.info("Инициализация SocketIO publisher (write-only) → %s", redis_url)
        _publisher = socketio.RedisManager(redis_url, write_only=True)


def emit(event: str, data: dict, *, room: Optional[str] = None) -> None:
    if _publisher is None:
        logger.warning("socket_publisher.emit called before init (%s)", event)
        return
    try:
        _publisher.emit(event, data, room=room)
    except Exception as exc:
        logger.exception("socket_publisher.emit %s failed: %s", event, exc)
