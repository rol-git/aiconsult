"""Сериализация сообщений для WebSocket-событий support-rt.

Локальная копия логики chat-api (без зависимости от routes/), т.к. через
socket идут только user/support-сообщения — у них нет rag_meta с метками агентов.
"""

from __future__ import annotations

from models import Message


def serialize_message(message: Message) -> dict:
    payload = {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "createdAt": message.created_at.isoformat(),
    }
    rag_meta = getattr(message, "rag_meta", None)
    if rag_meta:
        payload["agentTypes"] = rag_meta.agent_types or []
        payload["sources"] = rag_meta.sources or []
        if rag_meta.notes:
            payload["notes"] = rag_meta.notes
    payload.setdefault("suggestedQuestions", [])
    return payload
