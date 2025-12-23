#!/bin/bash

echo "========================================"
echo "Запуск сервера системы поддержки"
echo "========================================"
echo ""

cd server

if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3.12 -m venv venv
    echo ""
fi

echo "Активация виртуального окружения..."
source venv/bin/activate

echo "Установка зависимостей..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Запуск сервера на порту 5000..."
echo "========================================"
echo ""

python app.py

