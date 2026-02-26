"""
Скрипт для создания пользователя с ролью оператора поддержки.
"""

import sys
from getpass import getpass
from werkzeug.security import generate_password_hash

from database import init_engine, get_session
from models import User
from config import Config


def create_support_user():
    """Создает пользователя с ролью support."""
    print("=== Создание оператора поддержки ===\n")
    
    # Получаем данные от пользователя
    name = input("Введите имя оператора: ").strip()
    if not name:
        print("Ошибка: имя не может быть пустым")
        sys.exit(1)
    
    email = input("Введите email оператора: ").strip().lower()
    if not email or '@' not in email:
        print("Ошибка: некорректный email")
        sys.exit(1)
    
    password = getpass("Введите пароль: ").strip()
    if len(password) < 6:
        print("Ошибка: пароль должен содержать минимум 6 символов")
        sys.exit(1)
    
    password_confirm = getpass("Подтвердите пароль: ").strip()
    if password != password_confirm:
        print("Ошибка: пароли не совпадают")
        sys.exit(1)
    
    # Инициализируем подключение к БД
    config = Config()
    engine = init_engine(config.database_url)
    
    # Создаем пользователя
    session = get_session()
    
    # Проверяем, существует ли пользователь с таким email
    existing_user = session.query(User).filter_by(email=email).first()
    if existing_user:
        print(f"\nПользователь с email {email} уже существует.")
        update = input("Обновить роль на 'support'? (y/n): ").strip().lower()
        if update == 'y':
            existing_user.role = 'support'
            existing_user.name = name
            session.commit()
            print(f"\n✓ Роль пользователя {email} обновлена на 'support'")
        else:
            print("Операция отменена")
        sys.exit(0)
    
    # Создаем нового пользователя
    user = User(
        email=email,
        name=name,
        password_hash=generate_password_hash(password),
        role='support'
    )
    
    session.add(user)
    session.commit()
    
    print(f"\n✓ Оператор поддержки успешно создан!")
    print(f"  Имя: {name}")
    print(f"  Email: {email}")
    print(f"  Роль: support")
    print(f"\nТеперь этот пользователь может войти в систему и увидит панель поддержки.")


if __name__ == '__main__':
    try:
        create_support_user()
    except KeyboardInterrupt:
        print("\n\nОперация отменена пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nОшибка: {e}")
        sys.exit(1)

