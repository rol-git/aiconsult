# SQLAlchemy Tips - Избегаем распространенных ошибок

## Ошибка: "The unique() method must be invoked"

### Проблема
```python
# ❌ НЕПРАВИЛЬНО - вызовет ошибку
result = session.execute(
    select(Model)
    .options(joinedload(Model.collection))  # collection = relationship с list
).scalar_one_or_none()
```

### Решение
```python
# ✅ ПРАВИЛЬНО - добавить .unique()
result = session.execute(
    select(Model)
    .options(joinedload(Model.collection))
).unique()  # ← Добавить перед .scalar_one_or_none() или .scalars()
.scalar_one_or_none()
```

### Когда нужен .unique()?

**Нужен** когда:
- Используется `joinedload()` с коллекциями (relationships с `uselist=True`, то есть списки)
- Например: `messages`, `chats`, `users` и т.д.

**Не нужен** когда:
- Используется `joinedload()` с единичными объектами (relationships с `uselist=False`)
- Например: `user`, `chat`, `ticket` и т.д.
- Или вообще не используется `joinedload()`

### Примеры из нашего кода

#### ✅ Правильно (с коллекцией)
```python
tickets = session.execute(
    select(SupportTicket)
    .options(joinedload(SupportTicket.chat).joinedload(ChatSession.messages))
    #                                                   ^^^^^^^^ это список!
).unique()  # ← Обязательно!
.scalars()
.all()
```

#### ✅ Правильно (без коллекции)
```python
ticket = session.execute(
    select(SupportTicket)
    .options(joinedload(SupportTicket.chat))  # chat - единичный объект
).scalar_one_or_none()  # .unique() не нужен
```

### Где добавлять .unique()

```python
session.execute(...)
    .unique()           # ← Сюда, после execute()
    .scalars()          # и перед scalars()/scalar_one_or_none()
    .all()
```

## Другие советы

### 1. Используйте type hints
```python
from typing import Optional
from sqlalchemy.orm import Mapped

class User(Base):
    id: Mapped[int]
    name: Mapped[str]
    messages: Mapped[list["Message"]]  # ← явно указываем list
```

### 2. Проверяйте запросы
При написании нового запроса с `joinedload`:
1. Посмотрите на relationship - это список или единичный объект?
2. Если список - добавьте `.unique()`
3. Тестируйте сразу

### 3. Консистентность
Для единообразия можно всегда использовать `.unique()` с `joinedload`, это безопасно:
```python
# Работает в обоих случаях
result = session.execute(
    select(Model).options(joinedload(...))
).unique().scalar_one_or_none()
```

---

**Итог**: При использовании `joinedload` с коллекциями ВСЕГДА добавляйте `.unique()`!

