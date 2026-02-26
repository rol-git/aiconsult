"""
Маршруты для работы с чатами и сообщениями.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from database import get_session
from agents.base import AgentType, AGENT_LABELS
from models import ChatSession, Message, MessageRAGMeta
from interfaces import IAIService


def serialize_chat(chat: ChatSession) -> dict:
    last_message = chat.messages[-1] if chat.messages else None
    return {
        "id": str(chat.id),
        "title": chat.title or "Новый диалог",
        "createdAt": chat.created_at.isoformat(),
        "updatedAt": chat.updated_at.isoformat() if chat.updated_at else chat.created_at.isoformat(),
        "lastPreview": (last_message.content[:120] + "…") if last_message and len(last_message.content) > 120 else (last_message.content if last_message else ""),
    }


def serialize_message(message: Message) -> dict:
    payload = {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "createdAt": message.created_at.isoformat(),
    }
    if message.rag_meta:
        agent_types = message.rag_meta.agent_types or []
        payload["agentTypes"] = agent_types
        labels = []
        for agent in agent_types:
            if not agent:
                continue
            try:
                agent_enum = AgentType(agent)
                labels.append(AGENT_LABELS.get(agent_enum, agent))
            except ValueError:
                labels.append(agent)
        payload["agentLabels"] = labels
        payload["sources"] = message.rag_meta.sources or []
        if message.rag_meta.notes:
            payload["notes"] = message.rag_meta.notes
    payload.setdefault("suggestedQuestions", [])
    return payload


def build_context(messages: list[Message], limit: int = 10) -> Optional[str]:
    if not messages:
        return None
    history = []
    for item in messages[-limit:]:
        author = "Пользователь" if item.role == "user" else "Консультант"
        history.append(f"{author}: {item.content}")
    return "История диалога:\n" + "\n".join(history)


def create_chat_blueprint(ai_service: IAIService) -> Blueprint:
    bp = Blueprint("chats", __name__, url_prefix="/api/chats")

    def _get_user_uuid() -> uuid.UUID:
        return uuid.UUID(get_jwt_identity())

    def _load_chat(session, chat_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ChatSession]:
        return (
            session.execute(
                select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)
            ).scalar_one_or_none()
        )

    @bp.route("", methods=["GET"])
    @jwt_required()
    def list_chats():
        session = get_session()
        user_id = _get_user_uuid()
        chats = (
            session.execute(
                select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
            ).scalars().all()
        )
        return jsonify({"success": True, "chats": [serialize_chat(chat) for chat in chats]}), 200

    @bp.route("", methods=["POST"])
    @jwt_required()
    def create_chat():
        session = get_session()
        user_id = _get_user_uuid()

        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip() or "Новый диалог"

        chat = ChatSession(user_id=user_id, title=title)
        session.add(chat)
        session.commit()

        return jsonify({"success": True, "chat": serialize_chat(chat)}), 201

    @bp.route("/<chat_id>", methods=["GET"])
    @jwt_required()
    def get_chat(chat_id: str):
        session = get_session()
        user_id = _get_user_uuid()
        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        chat = _load_chat(session, chat_uuid, user_id)
        if chat is None:
            return jsonify({"success": False, "error": "Чат не найден"}), 404

        return jsonify(
            {
                "success": True,
                "chat": serialize_chat(chat),
                "messages": [serialize_message(msg) for msg in chat.messages],
            }
        ), 200

    @bp.route("/<chat_id>", methods=["DELETE"])
    @jwt_required()
    def delete_chat(chat_id: str):
        session = get_session()
        user_id = _get_user_uuid()
        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        chat = _load_chat(session, chat_uuid, user_id)
        if chat is None:
            return jsonify({"success": False, "error": "Чат не найден"}), 404

        session.delete(chat)
        session.commit()

        return jsonify({"success": True}), 200

    @bp.route("/<chat_id>/messages", methods=["POST"])
    @jwt_required()
    def send_message(chat_id: str):
        session = get_session()
        user_id = _get_user_uuid()
        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        chat = _load_chat(session, chat_uuid, user_id)
        if chat is None:
            return jsonify({"success": False, "error": "Чат не найден"}), 404

        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return jsonify({"success": False, "error": "Сообщение не может быть пустым"}), 400

        user_message = Message(chat_id=chat.id, role="user", content=content)
        session.add(user_message)

        ai_response = None
        context = build_context(chat.messages + [user_message])

        try:
            ai_response = ai_service.generate_answer(content, context=context)
        except Exception as exc:
            session.rollback()
            return jsonify({"success": False, "error": str(exc)}), 500

        assistant_message = Message(chat_id=chat.id, role="assistant", content=ai_response.answer)
        assistant_message.rag_meta = MessageRAGMeta(
            agent_types=[agent.value for agent in ai_response.agent_types],
            sources=[source.to_dict() for source in ai_response.sources],
            notes=ai_response.notes,
        )
        session.add(assistant_message)

        if not chat.title or chat.title == "Новый диалог":
            preview = content[:48].rstrip()
            chat.title = preview + ("…" if len(content) > 48 else "") or "Пример"

        chat.updated_at = datetime.utcnow()
        session.commit()

        assistant_payload = serialize_message(assistant_message)
        assistant_payload["suggestedQuestions"] = ai_response.suggested_questions
        assistant_payload["suggestOperator"] = ai_response.suggest_operator

        return jsonify(
            {
                "success": True,
                "chat": serialize_chat(chat),
                "messages": [serialize_message(user_message), assistant_payload],
            }
        ), 201

    return bp

