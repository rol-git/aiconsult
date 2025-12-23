@echo off
echo ========================================
echo Запуск сервера системы поддержки
echo ========================================
echo.

cd server

if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
    echo.
)

echo Активация виртуального окружения...
call venv\Scripts\activate

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo ========================================
echo Запуск сервера на порту 5000...
echo ========================================
echo.

python app.py

pause

