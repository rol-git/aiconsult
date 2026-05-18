# infra/

Docker-compose окружение для AI-консультанта.

## Состав

- `postgres` — PostgreSQL 16 c расширениями `pgvector` и `postgis`. Кастомный образ собирается из `postgres/Dockerfile`.
- `redis` — Redis 7 (AOF persistence).
- `server` — текущий монолит (Flask + SocketIO + RAG). Образ собирается из `../server/Dockerfile`.

Клиент пока запускается локально (`cd client && npm start`), в compose не входит.

## Запуск

```bash
cd infra
cp .env.example .env       # заполнить OPENROUTER_API_KEY и т.д.
docker compose up -d --build
docker compose logs -f server
```

## Полезные команды

```bash
# Подключиться к БД
docker compose exec postgres psql -U aiconsult -d aiconsult

# Прогнать миграции вручную
docker compose exec server alembic upgrade head

# Пересобрать pgvector-индекс (одноразово или после обновления docs/)
docker compose exec server python -m rag.rag_service

# Проверить, что чанки лежат в pgvector
docker compose exec postgres psql -U aiconsult -d aiconsult -c 'SELECT count(*) FROM public."data_rag_chunks";'

# Остановить
docker compose down

# Остановить и удалить данные (включая БД и индексы)
docker compose down -v
```

## Порты наружу

- Postgres: `localhost:${POSTGRES_PORT}` (по умолчанию 5432)
- Redis: `localhost:${REDIS_PORT}` (по умолчанию 6379)
- Server: `localhost:${SERVER_PORT}` (по умолчанию 5000)

Если на хосте уже занят, например, 5432 — поменяй `POSTGRES_PORT` в `.env`.
