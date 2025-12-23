"""
Интерфейсы (абстрактные классы) для системы.
Принцип DIP (Dependency Inversion Principle) - зависимость от абстракций.
Принцип ISP (Interface Segregation Principle) - специфичные интерфейсы.
"""

from abc import ABC, abstractmethod
from typing import Optional

from agents.base import AIResponse


class IAIService(ABC):
    """
    Интерфейс для AI сервиса.
    Позволяет заменять ChatGPT на другие AI (Claude, Gemini и т.д.)
    """
    
    @abstractmethod
    def generate_answer(self, question: str, context: Optional[str] = None) -> AIResponse:
        """
        Генерирует ответ на вопрос с учетом контекста.
        
        Args:
            question: Вопрос пользователя
            context: Контекст (опционально)
            
        Returns:
            AIResponse: Сгенерированный ответ с метаданными
            
        Raises:
            Exception: Если произошла ошибка при генерации
        """
        pass
    
    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Проверяет корректность конфигурации сервиса.
        
        Returns:
            bool: True если конфигурация валидна
        """
        pass


class IPromptBuilder(ABC):
    """
    Интерфейс для построителя промптов.
    Принцип SRP - отдельная ответственность за формирование промптов.
    """
    
    @abstractmethod
    def build_system_prompt(self) -> str:
        """
        Создает системный промпт для AI.
        
        Returns:
            str: Системный промпт
        """
        pass
    
    @abstractmethod
    def build_user_message(self, question: str) -> str:
        """
        Создает сообщение пользователя с вопросом.
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            str: Отформатированное сообщение
        """
        pass
