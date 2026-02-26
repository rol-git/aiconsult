"""
WebSocket события для real-time коммуникации.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Set

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import SocketIO, emit, join_room, leave_room
from sqlalchemy import select

from database import get_session
from models import ChatSession, Message, SupportTicket, User

logger = logging.getLogger(__name__)

# Хранилище подключенных пользователей и операторов
# {user_id: {socket_id, ...}}
connected_users: Dict[str, Set[str]] = {}
# {operator_id: {socket_id, ...}}
connected_operators: Dict[str, Set[str]] = {}

# Глобальная ссылка на socketio
socketio = None


def init_socketio(app, socketio_instance: SocketIO):
    """Инициализация WebSocket событий."""
    global socketio
    socketio = socketio_instance
    
    print("=" * 80)
    print("🔧 ИНИЦИАЛИЗАЦИЯ WebSocket обработчиков")
    print(f"   SocketIO instance: {socketio_instance}")
    print(f"   Global socketio set: {socketio is not None}")
    print("=" * 80)
    logger.info("=" * 80)
    logger.info("🔧 ИНИЦИАЛИЗАЦИЯ WebSocket обработчиков")
    logger.info(f"   SocketIO instance: {socketio_instance}")
    logger.info(f"   Global socketio set: {socketio is not None}")
    logger.info("=" * 80)

    @socketio_instance.on('connect')
    def handle_connect(auth):
        """Обработка подключения клиента."""
        print("=" * 80)
        print(f"🔌 ПОПЫТКА ПОДКЛЮЧЕНИЯ WebSocket")
        print(f"   Socket ID: {request.sid}")
        print(f"   Auth data: {auth}")
        print(f"   Auth type: {type(auth)}")
        print("=" * 80)
        logger.info(f"🔌 Попытка подключения WebSocket, socket ID: {request.sid}")
        logger.info(f"   Auth data: {auth}")
        logger.info(f"   Auth type: {type(auth)}")
        
        try:
            # Получаем токен из auth
            token = auth.get('token') if auth else None
            if not token:
                logger.warning("❌ Connection attempt without token")
                logger.warning(f"   Auth object: {auth}")
                return False
            
            print(f"✅ Token received, length: {len(token) if token else 0}")
            logger.info(f"✅ Token received, length: {len(token) if token else 0}")

            # Декодируем JWT токен
            try:
                decoded = decode_token(token)
                user_id_str = decoded['sub']
            except Exception as e:
                logger.error(f"Token decode error: {e}")
                return False
            
            # Нормализуем ID - всегда используем строковое представление UUID
            try:
                user_uuid = uuid.UUID(user_id_str)
                user_id_normalized = str(user_uuid)  # Нормализованный формат с дефисами
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
                return False
            
            session = get_session()
            try:
                user = session.get(User, user_uuid)
            except Exception as e:
                logger.error(f"Database error getting user: {e}")
                return False
            
            if not user:
                logger.warning(f"User not found: {user_id_normalized}")
                return False

            # Добавляем в соответствующее хранилище (используем нормализованный ID)
            if user.role == "support":
                if user_id_normalized not in connected_operators:
                    connected_operators[user_id_normalized] = set()
                connected_operators[user_id_normalized].add(request.sid)
                
                # Детальное логирование пары учетной записи
                print("=" * 80)
                print(f"🔵 ОПЕРАТОР ПОДКЛЮЧЕН")
                print(f"   Имя: {user.name}")
                print(f"   Email: {user.email}")
                print(f"   ID: {user_id_normalized}")
                print(f"   Socket ID: {request.sid}")
                print(f"   Роль: {user.role}")
                print(f"   Всего операторов онлайн: {len(connected_operators)}")
                print("=" * 80)
                logger.info("=" * 80)
                logger.info(f"🔵 ОПЕРАТОР ПОДКЛЮЧЕН")
                logger.info(f"   Имя: {user.name}")
                logger.info(f"   Email: {user.email}")
                logger.info(f"   ID: {user_id_normalized}")
                logger.info(f"   Socket ID: {request.sid}")
                logger.info(f"   Роль: {user.role}")
                logger.info(f"   Всего операторов онлайн: {len(connected_operators)}")
                logger.info("=" * 80)
            else:
                if user_id_normalized not in connected_users:
                    connected_users[user_id_normalized] = set()
                connected_users[user_id_normalized].add(request.sid)
                
                # Детальное логирование пары учетной записи
                print("=" * 80)
                print(f"🟢 ПОЛЬЗОВАТЕЛЬ ПОДКЛЮЧЕН")
                print(f"   Имя: {user.name}")
                print(f"   Email: {user.email}")
                print(f"   ID: {user_id_normalized}")
                print(f"   Socket ID: {request.sid}")
                print(f"   Роль: {user.role}")
                print(f"   Всего пользователей онлайн: {len(connected_users)}")
                print("=" * 80)
                logger.info("=" * 80)
                logger.info(f"🟢 ПОЛЬЗОВАТЕЛЬ ПОДКЛЮЧЕН")
                logger.info(f"   Имя: {user.name}")
                logger.info(f"   Email: {user.email}")
                logger.info(f"   ID: {user_id_normalized}")
                logger.info(f"   Socket ID: {request.sid}")
                logger.info(f"   Роль: {user.role}")
                logger.info(f"   Всего пользователей онлайн: {len(connected_users)}")
                logger.info("=" * 80)

            return True

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print("=" * 80)
            print(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ WebSocket")
            print(f"   Socket ID: {request.sid}")
            print(f"   Ошибка: {str(e)}")
            print(f"   Тип ошибки: {type(e).__name__}")
            print(f"   Traceback:\n{error_trace}")
            print("=" * 80)
            logger.error("=" * 80)
            logger.error(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ WebSocket")
            logger.error(f"   Socket ID: {request.sid}")
            logger.error(f"   Ошибка: {str(e)}")
            logger.error(f"   Тип ошибки: {type(e).__name__}")
            logger.error("=" * 80)
            logger.error(error_trace)
            return False

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Обработка отключения клиента."""
        sid = request.sid
        logger.info(f"🔌 Отключение WebSocket, socket ID: {sid}")
        
        # Удаляем из операторов
        for operator_id, sockets in list(connected_operators.items()):
            if sid in sockets:
                sockets.remove(sid)
                if not sockets:
                    del connected_operators[operator_id]
                logger.info("=" * 80)
                logger.info(f"🔵 ОПЕРАТОР ОТКЛЮЧЕН")
                logger.info(f"   ID: {operator_id}")
                logger.info(f"   Socket ID: {sid}")
                logger.info(f"   Осталось операторов онлайн: {len(connected_operators)}")
                logger.info("=" * 80)
                break
        
        # Удаляем из пользователей
        for user_id, sockets in list(connected_users.items()):
            if sid in sockets:
                sockets.remove(sid)
                if not sockets:
                    del connected_users[user_id]
                logger.info("=" * 80)
                logger.info(f"🟢 ПОЛЬЗОВАТЕЛЬ ОТКЛЮЧЕН")
                logger.info(f"   ID: {user_id}")
                logger.info(f"   Socket ID: {sid}")
                logger.info(f"   Осталось пользователей онлайн: {len(connected_users)}")
                logger.info("=" * 80)
                break

    @socketio_instance.on('join_chat')
    def handle_join_chat(data):
        """Подключение к комнате чата."""
        try:
            chat_id = data.get('chatId')
            logger.info(f"🔗 Попытка присоединения к комнате, socket ID: {request.sid}, chat ID: {chat_id}")
            if not chat_id:
                logger.warning("❌ Chat ID не указан")
                emit('error', {'message': 'Chat ID не указан'})
                return

            # Присоединяемся к комнате чата
            room_name = f"chat_{chat_id}"
            join_room(room_name)
            logger.info("=" * 80)
            logger.info(f"✅ ПРИСОЕДИНЕНИЕ К КОМНАТЕ")
            logger.info(f"   Socket ID: {request.sid}")
            logger.info(f"   Chat ID: {chat_id}")
            logger.info(f"   Room name: {room_name}")
            logger.info("=" * 80)
            emit('joined_chat', {'chatId': chat_id})

        except Exception as e:
            logger.error(f"Error joining chat: {e}")
            emit('error', {'message': str(e)})

    @socketio_instance.on('leave_chat')
    def handle_leave_chat(data):
        """Отключение от комнаты чата."""
        try:
            chat_id = data.get('chatId')
            if not chat_id:
                return

            leave_room(f"chat_{chat_id}")
            logger.info(f"Socket {request.sid} left chat room: {chat_id}")

        except Exception as e:
            logger.error(f"Error leaving chat: {e}")

    @socketio_instance.on('send_message')
    def handle_send_message(data):
        """Отправка сообщения в чат."""
        logger.info(f"📨 Получено сообщение через WebSocket, socket ID: {request.sid}")
        logger.info(f"   Data keys: {list(data.keys()) if data else 'None'}")
        try:
            token = data.get('token')
            chat_id = data.get('chatId')
            content = data.get('content', '').strip()

            logger.info(f"   Chat ID: {chat_id}")
            logger.info(f"   Content length: {len(content) if content else 0}")
            logger.info(f"   Token provided: {bool(token)}")

            if not token or not chat_id or not content:
                error_msg = 'Недостаточно данных'
                logger.warning(f"❌ {error_msg}: token={bool(token)}, chat_id={bool(chat_id)}, content={bool(content)}")
                emit('error', {'message': error_msg})
                return

            # Декодируем токен
            decoded = decode_token(token)
            user_id = uuid.UUID(decoded['sub'])
            chat_uuid = uuid.UUID(chat_id)

            session = get_session()
            user = session.get(User, user_id)
            
            if not user:
                emit('error', {'message': 'Пользователь не найден'})
                return

            # Проверяем доступ к чату
            chat = session.get(ChatSession, chat_uuid)
            if not chat:
                emit('error', {'message': 'Чат не найден'})
                return

            # Определяем роль сообщения
            if user.role == "support":
                # Проверяем, что оператор назначен на этот тикет
                ticket = session.execute(
                    select(SupportTicket).where(
                        SupportTicket.chat_id == chat_uuid,
                        SupportTicket.assigned_operator_id == user_id
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
                # Проверяем, что чат принадлежит пользователю
                if chat.user_id != user_id:
                    emit('error', {'message': 'Доступ запрещен'})
                    return
                
                message_role = "user"

            # Создаем сообщение
            message = Message(
                chat_id=chat_uuid,
                role=message_role,
                content=content,
                sender_id=user_id
            )
            session.add(message)
            chat.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(message)

            # Сериализуем сообщение
            from routes.chat_routes import serialize_message
            message_data = serialize_message(message)
            message_data['senderName'] = user.name
            message_data['chatId'] = chat_id

            # Отправляем всем в комнате
            socketio.emit('new_message', message_data, room=f"chat_{chat_id}")
            logger.info("=" * 80)
            logger.info(f"📨 СООБЩЕНИЕ ОТПРАВЛЕНО")
            logger.info(f"   Отправитель: {user.name} ({user.email})")
            logger.info(f"   Роль: {message_role}")
            logger.info(f"   Чат ID: {chat_id}")
            logger.info(f"   Сообщение ID: {message.id}")
            logger.info(f"   Длина сообщения: {len(content)} символов")
            logger.info(f"   Комната: chat_{chat_id}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            emit('error', {'message': str(e)})

    @socketio_instance.on('typing')
    def handle_typing(data):
        """Уведомление о печати."""
        try:
            chat_id = data.get('chatId')
            is_typing = data.get('isTyping', False)
            token = data.get('token')

            if not chat_id or not token:
                return

            decoded = decode_token(token)
            user_id = decoded['sub']
            
            session = get_session()
            user = session.get(User, uuid.UUID(user_id))

            if user:
                # Отправляем уведомление всем в комнате кроме отправителя
                emit('user_typing', {
                    'chatId': chat_id,
                    'userName': user.name,
                    'isTyping': is_typing
                }, room=f"chat_{chat_id}", skip_sid=request.sid)

        except Exception as e:
            logger.error(f"Error in typing event: {e}")

    def notify_new_ticket(chat_id: str, ticket_data: dict):
        """Уведомить всех онлайн операторов о новом тикете."""
        for operator_id, sockets in connected_operators.items():
            for socket_id in sockets:
                socketio.emit('new_ticket', {
                    'chatId': chat_id,
                    'ticket': ticket_data
                }, room=socket_id)
        logger.info(f"Notified operators about new ticket for chat {chat_id}")

    def notify_ticket_resolved(chat_id: str):
        """Уведомить пользователя о решении тикета."""
        socketio.emit('ticket_resolved', {'chatId': chat_id}, room=f"chat_{chat_id}")
        logger.info(f"Notified about resolved ticket for chat {chat_id}")

    # Возвращаем функции для использования в других модулях
    return {
        'notify_new_ticket': notify_new_ticket,
        'notify_ticket_resolved': notify_ticket_resolved,
        'get_online_operators_count': lambda: len(connected_operators),
        'get_online_users_count': lambda: len(connected_users),
    }


def get_online_operators():
    """Возвращает список ID онлайн операторов (нормализованные UUID строки)."""
    operators = list(connected_operators.keys())
    logger.debug(f"Online operators: {operators}, count: {len(operators)}")
    return operators

