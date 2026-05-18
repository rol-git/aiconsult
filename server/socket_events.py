"""
WebSocket события для real-time коммуникации.

Presence (онлайн-пользователи/операторы) живёт в Redis (см. realtime_state.PresenceStore),
поэтому несколько реплик процесса видят одно и то же состояние подключений.
"""

import logging
import uuid
from datetime import datetime
from typing import List

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import SocketIO, emit, join_room, leave_room
from sqlalchemy import select

from database import get_session
from models import ChatSession, Message, SupportTicket, User
from realtime_state import PresenceStore
from service_factory import get_service_factory

logger = logging.getLogger(__name__)

OPERATORS_ROOM = "operators"

socketio: SocketIO | None = None
_presence: PresenceStore | None = None


def _presence_store() -> PresenceStore:
    global _presence
    if _presence is None:
        _presence = get_service_factory().create_presence_store()
    return _presence


def init_socketio(app, socketio_instance: SocketIO):
    """Инициализация WebSocket-обработчиков."""
    global socketio
    socketio = socketio_instance
    presence = _presence_store()

    logger.info("WebSocket-обработчики регистрируются (presence backend = Redis)")

    @socketio_instance.on('connect')
    def handle_connect(auth):
        sid = request.sid
        token = (auth or {}).get('token') if auth else None
        if not token:
            logger.warning("WS connect без токена, sid=%s", sid)
            return False

        try:
            decoded = decode_token(token)
            user_uuid = uuid.UUID(decoded['sub'])
        except Exception as exc:
            logger.warning("WS connect: невалидный токен sid=%s: %s", sid, exc)
            return False

        session = get_session()
        user = session.get(User, user_uuid)
        if not user:
            logger.warning("WS connect: пользователь не найден %s", user_uuid)
            return False

        user_id = str(user_uuid)
        role = "support" if user.role == "support" else "user"
        presence.register_socket(user_id=user_id, role=role, sid=sid)

        if role == "support":
            join_room(OPERATORS_ROOM)

        logger.info(
            "WS connect: role=%s user=%s sid=%s online_%ss=%d",
            role, user.email, sid, role, presence.count_online(role),
        )
        return True

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        info = presence.unregister_socket(sid)
        if info:
            user_id, role = info
            logger.info(
                "WS disconnect: role=%s user=%s sid=%s online_%ss=%d",
                role, user_id, sid, role, presence.count_online(role),
            )

    @socketio_instance.on('join_chat')
    def handle_join_chat(data):
        chat_id = (data or {}).get('chatId')
        if not chat_id:
            emit('error', {'message': 'Chat ID не указан'})
            return
        join_room(f"chat_{chat_id}")
        emit('joined_chat', {'chatId': chat_id})
        logger.info("WS join_chat sid=%s chat=%s", request.sid, chat_id)

    @socketio_instance.on('leave_chat')
    def handle_leave_chat(data):
        chat_id = (data or {}).get('chatId')
        if not chat_id:
            return
        leave_room(f"chat_{chat_id}")
        logger.info("WS leave_chat sid=%s chat=%s", request.sid, chat_id)

    @socketio_instance.on('send_message')
    def handle_send_message(data):
        try:
            token = (data or {}).get('token')
            chat_id = (data or {}).get('chatId')
            content = ((data or {}).get('content') or '').strip()

            if not token or not chat_id or not content:
                emit('error', {'message': 'Недостаточно данных'})
                return

            decoded = decode_token(token)
            user_id = uuid.UUID(decoded['sub'])
            chat_uuid = uuid.UUID(chat_id)

            session = get_session()
            user = session.get(User, user_id)
            if not user:
                emit('error', {'message': 'Пользователь не найден'})
                return

            chat = session.get(ChatSession, chat_uuid)
            if not chat:
                emit('error', {'message': 'Чат не найден'})
                return

            if user.role == "support":
                ticket = session.execute(
                    select(SupportTicket).where(
                        SupportTicket.chat_id == chat_uuid,
                        SupportTicket.assigned_operator_id == user_id,
                    )
                ).scalar_one_or_none()
                if not ticket:
                    emit('error', {'message': 'Вы не назначены на этот тикет'})
                    return
                if ticket.status == "resolved":
                    emit('error', {'message': 'Тикет уже решен'})
                    return
                message_role = "support"
            else:
                if chat.user_id != user_id:
                    emit('error', {'message': 'Доступ запрещен'})
                    return
                message_role = "user"

            message = Message(
                chat_id=chat_uuid,
                role=message_role,
                content=content,
                sender_id=user_id,
            )
            session.add(message)
            chat.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(message)

            from routes.chat_routes import serialize_message
            payload = serialize_message(message)
            payload['senderName'] = user.name
            payload['chatId'] = chat_id

            socketio_instance.emit('new_message', payload, room=f"chat_{chat_id}")
            logger.info(
                "WS message: chat=%s sender=%s role=%s len=%d",
                chat_id, user.email, message_role, len(content),
            )
        except Exception as exc:
            logger.exception("WS send_message error: %s", exc)
            emit('error', {'message': str(exc)})

    @socketio_instance.on('typing')
    def handle_typing(data):
        try:
            chat_id = (data or {}).get('chatId')
            token = (data or {}).get('token')
            is_typing = bool((data or {}).get('isTyping', False))
            if not chat_id or not token:
                return
            decoded = decode_token(token)
            session = get_session()
            user = session.get(User, uuid.UUID(decoded['sub']))
            if not user:
                return
            emit(
                'user_typing',
                {'chatId': chat_id, 'userName': user.name, 'isTyping': is_typing},
                room=f"chat_{chat_id}",
                skip_sid=request.sid,
            )
        except Exception as exc:
            logger.exception("WS typing error: %s", exc)

    return {
        'notify_new_ticket': notify_new_ticket,
        'notify_ticket_resolved': notify_ticket_resolved,
        'get_online_operators_count': lambda: presence.count_online("support"),
        'get_online_users_count': lambda: presence.count_online("user"),
    }


def notify_new_ticket(chat_id: str, ticket_data: dict) -> None:
    """Уведомить всех онлайн-операторов о новом тикете через комнату ``operators``."""
    if socketio is None:
        logger.warning("notify_new_ticket called before socketio init")
        return
    socketio.emit(
        'new_ticket',
        {'chatId': chat_id, 'ticket': ticket_data},
        room=OPERATORS_ROOM,
    )
    logger.info("Notify operators about new ticket: chat=%s", chat_id)


def notify_ticket_resolved(chat_id: str) -> None:
    if socketio is None:
        logger.warning("notify_ticket_resolved called before socketio init")
        return
    socketio.emit('ticket_resolved', {'chatId': chat_id}, room=f"chat_{chat_id}")
    logger.info("Notify ticket_resolved: chat=%s", chat_id)


def get_online_operators() -> List[str]:
    """Возвращает список ID онлайн-операторов из Redis."""
    try:
        return _presence_store().online_users("support")
    except Exception as exc:
        logger.exception("get_online_operators failed: %s", exc)
        return []
