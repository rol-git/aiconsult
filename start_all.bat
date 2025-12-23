@echo off
echo ========================================
echo Запуск полной системы поддержки
echo ========================================
echo.
echo Запуск сервера и клиента в отдельных окнах...
echo.

start "Сервер - Порт 5000" cmd /k start_server.bat
timeout /t 3 /nobreak >nul
start "Клиент - Порт 3000" cmd /k start_client.bat

echo.
echo Система запущена!
echo Сервер: http://localhost:5000
echo Клиент: http://localhost:3000
echo.
pause

