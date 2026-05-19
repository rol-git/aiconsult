"""support-rt: Flask-SocketIO с Redis-adapter.

Сервис принимает WebSocket-соединения от клиента, валидирует JWT в
handshake, регистрирует presence в Redis (PresenceStore) и обрабатывает
события чата с операторами. Через Redis message_queue события долетают
от других реплик support-rt и от chat-api (write-only publisher).
"""

from __future__ import annotations

from datetime import timedelta
import logging

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

from database import init_engine, remove_session
from service_factory import get_service_factory
from socket_events import init_socketio


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class SupportRtApp:
    def __init__(self) -> None:
        self.app = Flask(__name__)
        CORS(self.app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

        self.factory = get_service_factory()
        self.config = self.factory.create_config()
        self._setup_database()
        self._setup_jwt()
        self._setup_socketio()
        self._register_routes()
        logger.info("support-rt инициализирован")

    def _setup_database(self) -> None:
        self.engine = init_engine(self.config.database_url)
        from models import ChatSession, Message, SupportTicket, User  # noqa: F401
        self.app.teardown_appcontext(remove_session)

    def _setup_jwt(self) -> None:
        self.app.config["JWT_SECRET_KEY"] = self.config.jwt_secret_key
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=self.config.jwt_expires_minutes)
        self.jwt = JWTManager(self.app)

    def _setup_socketio(self) -> None:
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=False,
            engineio_logger=False,
            always_connect=True,
            ping_timeout=60,
            ping_interval=25,
            message_queue=self.config.redis_url,
        )
        init_socketio(self.app, self.socketio)

    def _register_routes(self) -> None:
        @self.app.get('/health')
        def health():
            return jsonify({'status': 'ok', 'service': 'support-rt'}), 200

        @self.app.get('/ready')
        def ready():
            try:
                self.factory.create_redis().ping()
                return jsonify({'ready': True}), 200
            except Exception as exc:
                return jsonify({'ready': False, 'error': str(exc)}), 503

    def run(self, host: str = '0.0.0.0', port: int = None) -> None:
        port = port or self.config.port
        logger.info("Запуск support-rt на %s:%s", host, port)
        self.socketio.run(self.app, host=host, port=port, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    SupportRtApp().run()
