@echo off
echo ========================================
echo Запуск клиента системы поддержки
echo ========================================
echo.

cd client

if not exist node_modules (
    echo Установка зависимостей...
    call npm install
    echo.
)

echo ========================================
echo Запуск клиента на порту 3000...
echo ========================================
echo.

call npm start

pause

