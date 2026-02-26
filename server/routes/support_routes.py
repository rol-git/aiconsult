"""
Маршруты для работы с поддержкой операторов.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select, func, case
from sqlalchemy.orm import joinedload

from database import get_session
from models import ChatSession, Message, SupportTicket, User


def serialize_support_chat(chat: ChatSession, ticket: SupportTicket) -> dict:
    last_message = chat.messages[-1] if chat.messages else None
    return {
        "id": str(chat.id),
        "title": chat.title or "Новый диалог",
        "userName": chat.user.name if chat.user else "Пользователь",
        "userEmail": chat.user.email if chat.user else "",
        "createdAt": chat.created_at.isoformat(),
        "updatedAt": chat.updated_at.isoformat() if chat.updated_at else chat.created_at.isoformat(),
        "lastPreview": (last_message.content[:120] + "…") if last_message and len(last_message.content) > 120 else (last_message.content if last_message else ""),
        "ticketStatus": ticket.status,
        "assignedOperatorId": str(ticket.assigned_operator_id) if ticket.assigned_operator_id else None,
        "createdAt": ticket.created_at.isoformat(),
        "assignedAt": ticket.assigned_at.isoformat() if ticket.assigned_at else None,
        "resolvedAt": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    }


def create_support_blueprint() -> Blueprint:
    bp = Blueprint("support", __name__, url_prefix="/api/support")

    def _get_user_uuid() -> uuid.UUID:
        return uuid.UUID(get_jwt_identity())

    def _verify_support_role(session, user_id: uuid.UUID) -> bool:
        """Проверяет, является ли пользователь оператором поддержки."""
        user = session.get(User, user_id)
        return user is not None and user.role == "support"

    @bp.route("/tickets", methods=["GET"])
    @jwt_required()
    def list_tickets():
        """Получить список всех тикетов для оператора поддержки."""
        session = get_session()
        user_id = _get_user_uuid()

        if not _verify_support_role(session, user_id):
            return jsonify({"success": False, "error": "Доступ запрещен"}), 403

        # Получаем тикеты, назначенные этому оператору или нераспределенные
        # ВАЖНО: При использовании joinedload с коллекциями (например, messages)
        # необходимо вызвать .unique() перед .scalars() или .scalar_one_or_none()
        tickets = (
            session.execute(
                select(SupportTicket)
                .options(joinedload(SupportTicket.chat).joinedload(ChatSession.messages))
                .options(joinedload(SupportTicket.chat).joinedload(ChatSession.user))
                .where(
                    (SupportTicket.assigned_operator_id == user_id) | 
                    (SupportTicket.status == "pending")
                )
                .order_by(
                    # Сначала pending, потом assigned, потом resolved
                    case(
                        (SupportTicket.status == "pending", 0),
                        (SupportTicket.status == "assigned", 1),
                        (SupportTicket.status == "resolved", 2),
                        else_=3
                    ),
                    # Внутри каждой группы сортируем по дате обновления (новые сверху)
                    SupportTicket.created_at.desc()
                )
            )
            .unique()
            .scalars()
            .all()
        )

        result = []
        for ticket in tickets:
            if ticket.chat:
                result.append(serialize_support_chat(ticket.chat, ticket))

        return jsonify({"success": True, "tickets": result}), 200

    @bp.route("/tickets/<chat_id>", methods=["GET"])
    @jwt_required()
    def get_ticket(chat_id: str):
        """Получить детали конкретного тикета."""
        session = get_session()
        user_id = _get_user_uuid()

        if not _verify_support_role(session, user_id):
            return jsonify({"success": False, "error": "Доступ запрещен"}), 403

        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        # ВАЖНО: .unique() необходим при joinedload с коллекциями
        ticket = (
            session.execute(
                select(SupportTicket)
                .options(joinedload(SupportTicket.chat).joinedload(ChatSession.messages))
                .options(joinedload(SupportTicket.chat).joinedload(ChatSession.user))
                .where(SupportTicket.chat_id == chat_uuid)
            )
            .unique()
            .scalar_one_or_none()
        )

        if ticket is None:
            return jsonify({"success": False, "error": "Тикет не найден"}), 404

        # Автоматически назначаем тикет, если он pending и еще не назначен
        if ticket.status == "pending" and ticket.assigned_operator_id is None:
            ticket.assigned_operator_id = user_id
            ticket.status = "assigned"
            ticket.assigned_at = datetime.utcnow()
            session.commit()

        from routes.chat_routes import serialize_message
        return jsonify({
            "success": True,
            "ticket": serialize_support_chat(ticket.chat, ticket),
            "messages": [serialize_message(msg) for msg in ticket.chat.messages],
        }), 200

    @bp.route("/tickets/<chat_id>/resolve", methods=["POST"])
    @jwt_required()
    def resolve_ticket(chat_id: str):
        """Отметить тикет как решенный."""
        session = get_session()
        user_id = _get_user_uuid()

        if not _verify_support_role(session, user_id):
            return jsonify({"success": False, "error": "Доступ запрещен"}), 403

        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        ticket = (
            session.execute(
                select(SupportTicket)
                .options(joinedload(SupportTicket.chat))
                .where(SupportTicket.chat_id == chat_uuid)
            )
            .scalar_one_or_none()
        )

        if ticket is None:
            return jsonify({"success": False, "error": "Тикет не найден"}), 404

        if ticket.assigned_operator_id != user_id:
            return jsonify({"success": False, "error": "Этот тикет назначен другому оператору"}), 403

        ticket.status = "resolved"
        ticket.resolved_at = datetime.utcnow()

        # Добавляем системное сообщение в чат
        system_message = Message(
            chat_id=chat_uuid,
            role="system",
            content="Оператор отметил ваше обращение как решенное. Чат продолжит работу с нейросетью — на ваши сообщения будет отвечать AI-ассистент. При необходимости вы всегда можете снова обратиться к оператору, нажав кнопку 'Позвать оператора'.",
        )
        session.add(system_message)
        session.commit()
        
        # Отправляем системное сообщение через WebSocket и уведомляем о решении тикета
        try:
            from socket_events import notify_ticket_resolved
            # Отправляем системное сообщение через WebSocket
            from routes.chat_routes import serialize_message
            message_data = serialize_message(system_message)
            message_data['chatId'] = chat_id
            
            from socket_events import socketio
            socketio.emit('new_message', message_data, room=f"chat_{chat_id}")
            
            # Уведомляем о решении тикета
            notify_ticket_resolved(chat_id)
        except Exception as e:
            # Если WebSocket недоступен, просто логируем ошибку
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not send WebSocket notification for resolved ticket: {e}")

        return jsonify({"success": True, "ticket": serialize_support_chat(ticket.chat, ticket)}), 200

    @bp.route("/tickets/my/<chat_id>", methods=["GET"])
    @jwt_required()
    def get_my_ticket(chat_id: str):
        """Получить информацию о тикете пользователя (для самого пользователя)."""
        session = get_session()
        user_id = _get_user_uuid()

        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        # Проверяем, что чат принадлежит пользователю
        chat = session.execute(
            select(ChatSession).where(
                ChatSession.id == chat_uuid,
                ChatSession.user_id == user_id
            )
        ).scalar_one_or_none()

        if chat is None:
            return jsonify({"success": False, "error": "Чат не найден"}), 404

        # Ищем тикет для этого чата
        ticket = session.execute(
            select(SupportTicket).where(SupportTicket.chat_id == chat_uuid)
        ).scalar_one_or_none()

        if ticket is None:
            return jsonify({"success": False, "error": "Тикет не найден"}), 404

        return jsonify({
            "success": True,
            "id": str(ticket.id),
            "status": ticket.status,
            "assignedOperatorId": str(ticket.assigned_operator_id) if ticket.assigned_operator_id else None,
            "createdAt": ticket.created_at.isoformat(),
            "assignedAt": ticket.assigned_at.isoformat() if ticket.assigned_at else None,
            "resolvedAt": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        }), 200

    @bp.route("/request", methods=["POST"])
    @jwt_required()
    def request_support():
        """Создать запрос на поддержку оператора для чата."""
        session = get_session()
        user_id = _get_user_uuid()

        payload = request.get_json(silent=True) or {}
        chat_id = payload.get("chatId")

        if not chat_id:
            return jsonify({"success": False, "error": "Не указан идентификатор чата"}), 400

        try:
            chat_uuid = uuid.UUID(chat_id)
        except ValueError:
            return jsonify({"success": False, "error": "Некорректный идентификатор чата"}), 400

        # Проверяем, что чат принадлежит пользователю
        chat = session.execute(
            select(ChatSession).where(
                ChatSession.id == chat_uuid,
                ChatSession.user_id == user_id
            )
        ).scalar_one_or_none()

        if chat is None:
            return jsonify({"success": False, "error": "Чат не найден"}), 404

        # Проверяем, есть ли уже активный тикет
        existing_ticket = session.execute(
            select(SupportTicket).where(
                SupportTicket.chat_id == chat_uuid,
                SupportTicket.status.in_(["pending", "assigned"])
            )
        ).scalar_one_or_none()

        if existing_ticket:
            return jsonify({"success": False, "error": "Запрос на поддержку уже создан"}), 400

        # Создаем новый тикет
        ticket = SupportTicket(
            chat_id=chat_uuid,
            status="pending"
        )
        session.add(ticket)

        # Находим наиболее свободного оператора среди ВСЕХ операторов (независимо от онлайн статуса)
        operator_workload = session.execute(
            select(
                User.id,
                User.name,
                User.email,
                func.count(SupportTicket.id).label("ticket_count")
            )
            .outerjoin(
                SupportTicket,
                (SupportTicket.assigned_operator_id == User.id) &
                (SupportTicket.status == "assigned")
            )
            .where(User.role == "support")
            .group_by(User.id, User.name, User.email)
            .order_by(func.count(SupportTicket.id).asc())
        ).first()

        if operator_workload:
            operator_id, operator_name, operator_email, workload = operator_workload
            ticket.assigned_operator_id = operator_id
            ticket.status = "assigned"
            ticket.assigned_at = datetime.utcnow()
            
            # Логирование в консоль
            print(f"\n{'='*60}")
            print(f"🎫 ТИКЕТ НАЗНАЧЕН ОПЕРАТОРУ")
            print(f"{'='*60}")
            print(f"Тикет ID: {ticket.id}")
            print(f"Чат ID: {chat_id}")
            print(f"Оператор ID: {operator_id}")
            print(f"Оператор: {operator_name} ({operator_email})")
            print(f"Текущая нагрузка: {workload} активных тикетов")
            print(f"{'='*60}\n")
            
            current_app.logger.info(f"Ticket {ticket.id} assigned to operator {operator_name} ({operator_id}), workload: {workload}")
        else:
            print(f"\n⚠️  ВНИМАНИЕ: Не найдено операторов для назначения тикета {ticket.id}\n")
            current_app.logger.warning("No operator found for assignment, ticket will remain pending")

        # Добавляем системное сообщение в чат
        system_message = Message(
            chat_id=chat_uuid,
            role="system",
            content="Ваш запрос направлен оператору. Пожалуйста, ожидайте ответа.",
        )
        session.add(system_message)
        session.commit()

        return jsonify({
            "success": True,
            "ticket": {
                "id": str(ticket.id),
                "status": ticket.status,
                "assignedOperatorId": str(ticket.assigned_operator_id) if ticket.assigned_operator_id else None,
            }
        }), 201

    @bp.route("/online-operators", methods=["GET"])
    @jwt_required()
    def check_online_operators():
        """Проверить наличие онлайн операторов."""
        from socket_events import get_online_operators
        
        online_operator_ids = get_online_operators()
        operators_count = len(online_operator_ids)

        return jsonify({
            "success": True,
            "available": operators_count > 0,
            "count": operators_count
        }), 200

    return bp

