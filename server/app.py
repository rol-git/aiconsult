"""
Flask приложение с использованием принципов ООП и SOLID.
Принцип DIP - зависимость от абстракций через Service Factory.
"""

from datetime import timedelta
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

from database import Base, init_engine, remove_session
from interfaces import IAIService
from routes.auth_routes import create_auth_blueprint
from routes.chat_routes import create_chat_blueprint
from routes.faq_routes import create_faq_blueprint
from routes.support_routes import create_support_blueprint
from service_factory import get_service_factory
from socket_events import init_socketio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FloodSupportApp:
    """
    Класс приложения для системы поддержки при паводках.
    Инкапсулирует логику Flask приложения.
    Принцип SRP - управление веб-приложением.
    """
    
    def __init__(self):
        """Инициализация приложения."""
        self.app = Flask(__name__)
        # CORS для HTTP API - разрешаем все источники
        CORS(self.app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
        # Также разрешаем CORS для корневых путей (health, info и т.д.)
        CORS(self.app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
        
        # Получаем фабрику сервисов
        self.service_factory = get_service_factory()
        
        # Инициализируем сервисы
        self.config = self.service_factory.create_config()
        self._setup_database()
        self._setup_security()
        self.ai_service: IAIService = self.service_factory.create_ai_service()
        
        # Инициализируем SocketIO
        self._setup_socketio()
        
        # Регистрируем маршруты
        self._register_routes()
        
        logger.info("Приложение FloodSupportApp инициализировано")
    
    def _setup_database(self) -> None:
        """Настраивает подключение к базе данных."""
        self.engine = init_engine(self.config.database_url)

        # Импорт моделей для регистрации метаданных
        from models import ChatSession, Message, User  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.app.teardown_appcontext(remove_session)
        logger.info("Подключение к базе данных инициализировано")

    def _setup_security(self) -> None:
        """Настраивает JWT аутентификацию."""
        self.app.config["JWT_SECRET_KEY"] = self.config.jwt_secret_key
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=self.config.jwt_expires_minutes)
        self.jwt = JWTManager(self.app)

    def _setup_socketio(self) -> None:
        """Настраивает WebSocket соединение."""
        # SocketIO использует тот же Flask app, поэтому работает на том же порту
        # CORS настроен для разрешения подключений с любого источника
        self.socketio = SocketIO(
            self.app,  # Используем тот же Flask app - WebSocket на том же порту
            cors_allowed_origins="*",  # Разрешаем подключения с любого источника
            async_mode='threading',
            logger=True,
            engineio_logger=True,  # Включаем логирование для отладки
            always_connect=True,
            ping_timeout=60,
            ping_interval=25
        )
        # Инициализируем обработчики событий
        print("=" * 80)
        print("🔧 НАСТРОЙКА SocketIO")
        print(f"   Flask app: {self.app}")
        print(f"   SocketIO instance: {self.socketio}")
        print("=" * 80)
        self.socket_handlers = init_socketio(self.app, self.socketio)
        print("✅ SocketIO обработчики зарегистрированы")
        logger.info("SocketIO инициализирован с полным логированием")

    def _register_routes(self) -> None:
        """Регистрирует все маршруты приложения."""
        self.app.route('/api/ask', methods=['POST'])(self.ask_question)
        self.app.route('/api/health', methods=['GET'])(self.health_check)
        self.app.route('/api/info', methods=['GET'])(self.get_info)
        self.app.register_blueprint(create_auth_blueprint())
        self.app.register_blueprint(create_chat_blueprint(self.ai_service))
        self.app.register_blueprint(create_faq_blueprint())
        self.app.register_blueprint(create_support_blueprint())
    
    def ask_question(self):
        """
        Обрабатывает вопрос от клиента.
        Принцип SRP - только обработка HTTP запроса, логика в AI сервисе.
        
        Returns:
            JSON ответ с результатом
        """
        try:
            data = request.get_json()
            
            # Валидация входных данных
            validation_error = self._validate_question_request(data)
            if validation_error:
                return jsonify(validation_error), 400
            
            question = data['question']
            logger.info(f"Получен вопрос: {question[:100]}...")
            
            # Генерируем ответ через AI сервис (DIP - зависимость от абстракции)
            ai_response = self.ai_service.generate_answer(question)
            
            logger.info("Ответ успешно сгенерирован")
            
            return jsonify({
                'success': True,
                **ai_response.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {str(e)}")
            return jsonify({
                'error': f'Произошла ошибка при обработке запроса: {str(e)}',
                'success': False
            }), 500
    
    def _validate_question_request(self, data: dict) -> dict:
        """
        Валидирует запрос с вопросом.
        
        Args:
            data: Данные запроса
            
        Returns:
            dict: Сообщение об ошибке или None
        """
        if not data or 'question' not in data:
            return {'error': 'Вопрос не предоставлен', 'success': False}
        
        question = data['question']
        
        if not question or not question.strip():
            return {'error': 'Вопрос не может быть пустым', 'success': False}
        
        if len(question) > 5000:
            return {'error': 'Вопрос слишком длинный (макс. 5000 символов)', 'success': False}
        
        return None
    
    def health_check(self):
        """
        Проверка работоспособности сервера.
        
        Returns:
            JSON ответ со статусом
        """
        try:
            # Проверяем конфигурацию
            self.config.validate()
            
            return jsonify({
                'status': 'ok',
                'message': 'Сервер работает',
                'mode': 'Мультиагентный RAG по локальным документам',
                'model': self.config.openrouter_model
            }), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    def get_info(self):
        """
        Возвращает информацию о системе.
        
        Returns:
            JSON ответ с информацией
        """
        return jsonify({
            'version': '3.0.0',
            'region': 'Тюменская область',
            'ai_model': self.config.openrouter_model,
            'mode': 'Multi-agent RAG (локальные документы)',
            'architecture': 'Ориентированная на сервисы (Service Factory, RAG, OpenRouter)'
        }), 200
    
    def run(self, host: str = '0.0.0.0', port: int = None, debug: bool = False) -> None:
        """
        Запускает Flask приложение.
        
        Args:
            host: Хост для запуска
            port: Порт (если None, берется из конфигурации)
            debug: Режим отладки
        """
        if port is None:
            port = self.config.server_port
        
        print("=" * 80)
        print("🚀 ЗАПУСК СЕРВЕРА")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Debug: {debug}")
        print(f"   HTTP API: http://{host}:{port}/api/*")
        print(f"   WebSocket: ws://{host}:{port}/socket.io/")
        print(f"   CORS: разрешены все источники (*)")
        print(f"   SocketIO: {self.socketio}")
        print(f"   Flask app: {self.app}")
        print("=" * 80)
        logger.info(f"Запуск сервера на {host}:{port}")
        logger.info(f"Модель AI: {self.config.openrouter_model}")
        logger.info(f"Режим: мультиагентный RAG (локальные документы)")
        logger.info(f"Регион: Тюменская область")
        logger.info("WebSocket поддержка включена")
        
        self.socketio.run(self.app, host=host, port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)


def create_app() -> Flask:
    """
    Фабричная функция для создания Flask приложения.
    Используется для тестирования и расширения.
    
    Returns:
        Flask: Экземпляр приложения
    """
    flood_app = FloodSupportApp()
    return flood_app.app


# Точка входа
if __name__ == '__main__':
    try:
        app_instance = FloodSupportApp()
        app_instance.run(debug=False)
    except Exception as e:
        logger.critical(f"Не удалось запустить приложение: {str(e)}")
        raise
