# 🌐 ИИ‑консультант по ЧС в Тюменской области

Мультиагентная система поддержки населения при чрезвычайных ситуациях (паводки, эвакуация, оформление выплат). Ответы строятся **исключительно** на локальном наборе нормативных документов (`docs/`) с помощью RAG и модели OpenRouter.

---

## 🧠 Главное

- ✅ 4 специализированных агента: выплаты, немедленные действия, правовые разъяснения, помощь в подготовке документов  
- ✅ Нелинейный маршрутизатор (эвристики + LLM) сам выбирает подходящего эксперта  
- ✅ RAG через **LlamaIndex**: документы (`PDF`, `ODT`) индексируются локально, без обращений к внешним базам  
- ✅ LLM подключена через **OpenRouter** (например, `meta-llama/Meta-Llama-3.1-70B-Instruct`)  
- ✅ Каждое сообщение хранит ссылки на использованные документы и записывается в Postgres вместе с метаданными
- ✅ **Система поддержки с реальными операторами** - real-time чат с живыми специалистами через WebSocket

---

## 🚀 Быстрый старт

1. **Скопируйте примеры `.env`**
```bash
cp server/env.example server/.env
cp client/env.example client/.env
```

2. **Заполните ключи и пути в `server/.env`**
   ```env
   OPENROUTER_API_KEY=sk-or-ваш-ключ
   OPENROUTER_SITE_URL=https://your-domain.example.com   # обязателен для OpenRouter
   OPENROUTER_APP_NAME=AIConsultTyumen
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aiconsult
   DOCS_ROOT=../docs
   RAG_STORAGE_PATH=./storage/index
   CHROMA_PERSIST_DIR=./storage/chroma
   ```

3. **Подготовьте окружение сервера**
```bash
   cd server
   python -m venv venv
   source venv/bin/activate          # или venv\Scripts\activate в Windows
   pip install -r requirements.txt
   ```

4. **Соберите индекс документов (при первом запуске и после обновлений `docs/`)**
   ```bash
   cd server
   python -m rag.rag_service
   ```

5. **Запустите сервер и клиент**
```bash
   cd server && flask --app app run
   cd client && npm install && npm start
   ```

6. **Откройте интерфейс**: http://localhost:3000

---

## 🏗️ Архитектура

```
┌────────────┐      ┌─────────────────┐      ┌──────────────────────┐
│  Клиент    │ ->   │ Flask API / JWT │  ->  │ MultiAgent Service   │
│  React     │      └─────────────────┘      │ (Router + Agents)    │
└────────────┘                               │                      │
                                             │  ┌───────────────┐   │
                                             │  │RAG (LlamaIndex)│  │
                                             │  └───────────────┘   │
                                             │  ┌───────────────┐   │
                                             │  │OpenRouter LLM │   │
                                             │  └───────────────┘   │
                                             └──────────────────────┘
```

- `server/llm/openrouter_client.py` — изолирует HTTP-вызовы OpenRouter  
- `server/rag/rag_service.py` — отвечает за построение/загрузку индекса LlamaIndex  
- `server/agents/` — базовые классы, специализированные агенты и маршрутизатор  
- `server/ai_service.py` — мультиагентный оркестратор, реализующий `IAIService`  
- `server/models.py` — таблица `message_rag_meta` хранит типы агентов и использованные источники

---

## 🔐 Переменные окружения сервера

```env
SERVER_PORT=5000

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
OPENROUTER_SITE_URL=https://your-domain.example.com
OPENROUTER_APP_NAME=AIConsultTyumen
LLM_MAX_TOKENS=1800
LLM_TEMPERATURE=0.3

# RAG
DOCS_ROOT=../docs
RAG_STORAGE_PATH=./storage/index
CHROMA_PERSIST_DIR=./storage/chroma
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_TOP_K=4

# База и JWT
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aiconsult
JWT_SECRET_KEY=super-secret-key
JWT_EXPIRES_MINUTES=1440
```

---

## 🧩 Мультиагентная логика

1. **RouterAgent** сочетает эвристику по ключевым словам и LLM-классификацию (JSON-ответ)  
2. Выбранный агент запрашивает контекст у RAG (только локальные документы)  
3. Ответ формируется строго на основе переданных фрагментов, добавляются ссылки  
4. В БД сохраняется текст, тип агента и список источников  
5. На фронтенде источник отображается рядом с сообщением консультанта

### Доступные агенты
- `Выплаты и компенсации`
- `Что делать прямо сейчас`
- `Нормативные разъяснения`
- `Подготовка документов`

---

## 📡 API (дополнено)

- `POST /api/ask` — простой гостевой запрос. Ответ:
```json
{
  "success": true,
    "answer": "…",
    "agentTypes": ["payouts"],
    "agentLabels": ["Выплаты и компенсации"],
    "sources": [
      { "document": "ПП 304.odt", "location": "page_label: 5", "excerpt": "…" }
  ]
}
```

- `POST /api/chats/<chat_id>/messages` — добавляет два сообщения и возвращает их с метаданными. История диалога теперь содержит поля `agentTypes`, `agentLabels`, `sources`, `notes`.

---

## 🖥️ Клиент

- React 18 + Context API  
- История диалогов, JWT, гостевой режим  
- Обновлённый `ChatHistory`: отображение активного агента и перечня документов-источников  
- Markdown-ответы и заметки (`notes`) с пояснением, если нужной информации нет

---

## 📚 Работа с документами

- Документы лежат в `docs/` (PDF/ODT).  
- После обновления папки выполните пересборку:
  ```bash
  cd server
  python -m rag.rag_service      # пересоздаст индекс
  ```
- Хранилище индекса (по умолчанию `server/storage/index`) задаётся `RAG_STORAGE_PATH`, а файлы ChromaDB — `CHROMA_PERSIST_DIR`.

---

## 🧪 Тестирование и отладка

- Проверка здоровья: `GET /api/health`  
- Информация о сборке: `GET /api/info` (вернёт модель, режим и регион)  
- Логи сервера содержат выбранных агентов и ход маршрутизации

---

## ❓ Частые вопросы

**OpenRouter**  
1. Создайте key на https://openrouter.ai/  
2. Добавьте `OPENROUTER_SITE_URL` (это ссылка на вашу систему) и `OPENROUTER_APP_NAME` (будет показан пользователю при подтверждении токена)

**Почему ответы иногда пустые?**  
Если ни один документ не подошёл, агент честно сообщает об этом. Попробуйте уточнить формулировку или расширить набор файлов в `docs/`.

**Можно ли использовать другую модель?**  
Да. Укажите любое имя модели OpenRouter, совместимое с `chat/completions`. Для точных юридических ответов рекомендуется семейство Llama 3.1 или Qwen 2.5.

---

## 📦 Версия

- **Текущая версия**: 3.1.0  
- **Режим**: мультиагентный RAG по локальным документам + система поддержки  
- **Регион**: Тюменская область  
- **База**: PostgreSQL + SQLAlchemy  
- **LLM-провайдер**: OpenRouter
- **Real-time**: Flask-SocketIO + socket.io-client

---

## 🆕 Система поддержки с операторами (v3.1.0)

### Что нового?

Добавлена полнофункциональная система чата с реальными операторами поддержки:

- 🤖 **Интеллектное определение** - AI автоматически предлагает связаться с оператором при необходимости
- ⚡ **Real-time коммуникация** - мгновенная доставка сообщений через WebSocket
- 👨‍💼 **Панель оператора** - специальный интерфейс для операторов поддержки
- 🎯 **Автоматическое распределение** - тикеты назначаются наиболее свободному оператору
- 📊 **Управление тикетами** - статусы pending/assigned/resolved
- 🔄 **Бесшовная интеграция** - переход от AI к оператору и обратно в одном чате

### Быстрый старт системы поддержки

```bash
# 1. Установите зависимости
cd server && pip install -r requirements.txt
cd ../client && npm install

# 2. Добавьте поле sender_id в БД (обязательно!)
cd server
psql -d your_database -f add_sender_id.sql
# Или: fix_sender_id.bat (Windows)

# 3. Создайте оператора поддержки
python create_support_user.py

# 4. Запустите систему
python app.py              # Терминал 1
cd ../client && npm start  # Терминал 2
```

### Документация системы поддержки

- 📖 **[SUPPORT_SYSTEM_README.md](SUPPORT_SYSTEM_README.md)** - полная документация
- 🚀 **[QUICK_START_SUPPORT.md](QUICK_START_SUPPORT.md)** - быстрый старт
- 📋 **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - резюме реализации
- 🇷🇺 **[ИНСТРУКЦИЯ_СИСТЕМА_ПОДДЕРЖКИ.md](ИНСТРУКЦИЯ_СИСТЕМА_ПОДДЕРЖКИ.md)** - инструкция на русском
- 💻 **[COMMANDS.md](COMMANDS.md)** - команды для запуска

### Как это работает?

1. **Пользователь** общается с AI-ассистентом
2. **AI анализирует** запросы и при необходимости предлагает оператора
3. **Пользователь** может принять или отклонить предложение
4. **Система** создает тикет и назначает свободного оператора
5. **Оператор** видит всю историю и отвечает в реальном времени
6. После решения вопроса **оператор** закрывает тикет
7. Дальнейшие сообщения снова обрабатываются **AI**

---

Проект создан для оперативной помощи жителям Тюменской области. Любые улучшения и новые документы легко интегрируются — добавьте файлы в `docs/`, пересоберите индекс и перезапустите сервер. Вместе делаем консультации точнее и надёжнее. 💙
