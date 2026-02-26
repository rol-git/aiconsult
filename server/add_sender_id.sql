-- Быстрая миграция для добавления sender_id в таблицу messages
-- Выполните: psql -d your_database -f add_sender_id.sql

\echo 'Добавление sender_id в таблицу messages...'

-- Добавляем поле sender_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'sender_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN sender_id UUID;
        RAISE NOTICE 'Столбец sender_id добавлен';
    ELSE
        RAISE NOTICE 'Столбец sender_id уже существует';
    END IF;
END $$;

-- Добавляем внешний ключ (если его нет)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_messages_sender'
    ) THEN
        ALTER TABLE messages ADD CONSTRAINT fk_messages_sender 
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL;
        RAISE NOTICE 'Внешний ключ fk_messages_sender добавлен';
    ELSE
        RAISE NOTICE 'Внешний ключ fk_messages_sender уже существует';
    END IF;
END $$;

-- Создаем индекс
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);

\echo 'Миграция завершена!'
\echo ''
\echo 'Проверка результата:'

-- Проверка результата
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'messages' AND column_name = 'sender_id';

