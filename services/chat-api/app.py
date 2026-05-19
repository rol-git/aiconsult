"""chat-api: HTTP-сервис для auth/chats/ask/faq/support REST.

WebSocket (real-time чат с операторами) живёт в отдельном сервисе support-rt.
Чтобы из HTTP-роутов отправлять события подключённым клиентам, используется
socket_publisher (write-only Redis-канал, который support-rt получает через
свой Redis-adapter и доставляет клиентам).
"""

from datetime import timedelta
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import socket_publisher
from database import init_engine, remove_session
from interfaces import IAIService
from geo import UserContext, UserLocation
from routes.auth_routes import create_auth_blueprint
from routes.chat_routes import create_chat_blueprint
from routes.faq_routes import create_faq_blueprint
from routes.support_routes import create_support_blueprint
from service_factory import get_service_factory


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class ChatApiApp:
    """HTTP-only Flask-приложение чат-API."""

    def __init__(self) -> None:
        self.app = Flask(__name__)
        CORS(self.app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

        self.service_factory = get_service_factory()
        self.config = self.service_factory.create_config()
        self._setup_database()
        self._setup_security()
        socket_publisher.init(self.config.redis_url)
        self.ai_service: IAIService = self.service_factory.create_ai_service()
        self._register_routes()
        logger.info("chat-api инициализирован")

    def _setup_database(self) -> None:
        self.engine = init_engine(self.config.database_url)
        from models import ChatSession, Message, User  # noqa: F401
        self.app.teardown_appcontext(remove_session)
        logger.info("Подключение к БД готово")

    def _setup_security(self) -> None:
        self.app.config["JWT_SECRET_KEY"] = self.config.jwt_secret_key
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=self.config.jwt_expires_minutes)
        self.jwt = JWTManager(self.app)

    def _register_routes(self) -> None:
        self.app.route('/api/ask', methods=['POST'])(self.ask_question)
        self.app.route('/api/health', methods=['GET'])(self.health_check)
        self.app.route('/api/info', methods=['GET'])(self.get_info)
        self.app.register_blueprint(create_auth_blueprint())
        self.app.register_blueprint(create_chat_blueprint(self.ai_service))
        self.app.register_blueprint(create_faq_blueprint())
        self.app.register_blueprint(create_support_blueprint())

    def ask_question(self):
        try:
            data = request.get_json()
            err = self._validate_question_request(data)
            if err:
                return jsonify(err), 400
            question = data['question']
            user_context = self._parse_user_context(data)
            ai_response = self.ai_service.generate_answer(question, user_context=user_context)
            return jsonify({'success': True, **ai_response.to_dict()}), 200
        except Exception as exc:
            logger.exception("ask_question failed: %s", exc)
            return jsonify({'error': f'Ошибка: {exc}', 'success': False}), 500

    @staticmethod
    def _validate_question_request(data):
        if not data or 'question' not in data:
            return {'error': 'Вопрос не предоставлен', 'success': False}
        question = data['question']
        if not question or not question.strip():
            return {'error': 'Вопрос не может быть пустым', 'success': False}
        if len(question) > 5000:
            return {'error': 'Вопрос слишком длинный (макс. 5000 символов)', 'success': False}
        return None

    @staticmethod
    def _parse_user_context(data: dict) -> UserContext:
        loc_raw = data.get("location") if isinstance(data, dict) else None
        if not isinstance(loc_raw, dict):
            return UserContext()
        try:
            lat = float(loc_raw.get("lat"))
            lon = float(loc_raw.get("lon"))
            acc = loc_raw.get("accuracy")
            acc_f = float(acc) if acc is not None else None
            source = str(loc_raw.get("source") or "browser")
            return UserContext(
                location=UserLocation(lat=lat, lon=lon, accuracy_m=acc_f, source=source),
            )
        except (TypeError, ValueError):
            return UserContext()

    def health_check(self):
        try:
            self.config.validate()
            return jsonify({'status': 'ok', 'service': 'chat-api'}), 200
        except Exception as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 500

    def get_info(self):
        return jsonify({
            'service': 'chat-api',
            'version': '4.0.0',
            'region': 'Тюменская область',
            'rag_service_url': self.config.rag_service_url,
        }), 200

    def run(self, host: str = '0.0.0.0', port: int = None, debug: bool = False) -> None:
        if port is None:
            port = self.config.server_port
        logger.info("Запуск chat-api на %s:%s", host, port)
        self.app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)


def create_app() -> Flask:
    return ChatApiApp().app


if __name__ == '__main__':
    ChatApiApp().run()
