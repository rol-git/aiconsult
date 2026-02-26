@echo off
echo ========================================
echo Исправление ошибки sender_id
echo ========================================
echo.

REM Получаем DATABASE_URL из .env
for /f "tokens=1,2 delims==" %%a in ('type .env ^| findstr "DATABASE_URL"') do set DATABASE_URL=%%b

echo DATABASE_URL: %DATABASE_URL%
echo.

REM Парсим DATABASE_URL
REM Формат: postgresql+psycopg://user:password@host:port/dbname
for /f "tokens=2,3,4 delims=:/@" %%a in ("%DATABASE_URL%") do (
    set DB_USER=%%a
    set DB_PASS=%%b
    set DB_HOST=%%c
)

REM Получаем имя базы (последняя часть после /)
for %%a in ("%DATABASE_URL:/=" "%") do set DB_NAME=%%~nxa

echo Подключение к базе данных...
echo База: %DB_NAME%
echo.

REM Выполняем миграцию
set PGPASSWORD=%DB_PASS%
psql -U %DB_USER% -d %DB_NAME% -f add_sender_id.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Миграция выполнена успешно!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ОШИБКА при выполнении миграции
    echo ========================================
    echo.
    echo Попробуйте выполнить вручную:
    echo psql -d %DB_NAME% -f add_sender_id.sql
)

pause

