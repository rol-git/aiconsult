-- Миграция базы данных для добавления системы поддержки
-- Выполните этот скрипт, если у вас уже есть существующая база данных

-- 1. Добавляем поле role в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user' NOT NULL;

-- 2. Добавляем поле sender_id в таблицу messages (если его еще нет)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'sender_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN sender_id UUID REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 3. Создаем таблицу support_tickets
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL UNIQUE REFERENCES chat_sessions(id) ON DELETE CASCADE,
    assigned_operator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    assigned_at TIMESTAMP,
    resolved_at TIMESTAMP
);

-- 4. Создаем индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_operator ON support_tickets(assigned_operator_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_chat ON support_tickets(chat_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);

-- 5. Комментарии к полям
COMMENT ON COLUMN users.role IS 'Роль пользователя: user или support';
COMMENT ON COLUMN messages.sender_id IS 'ID оператора для сообщений от support';
COMMENT ON TABLE support_tickets IS 'Тикеты поддержки для связи пользователей с операторами';
COMMENT ON COLUMN support_tickets.status IS 'Статус тикета: pending, assigned, resolved';

-- 6. Вывод результата
SELECT 'Миграция успешно выполнена!' as result;

