-- Скрипт проверки состояния системы поддержки

\echo '=== 1. Проверка структуры таблицы messages ==='
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'messages' AND column_name IN ('id', 'role', 'sender_id')
ORDER BY ordinal_position;

\echo ''
\echo '=== 2. Проверка наличия операторов ==='
SELECT id, email, name, role, created_at 
FROM users 
WHERE role = 'support'
ORDER BY created_at DESC;

\echo ''
\echo '=== 3. Проверка таблицы support_tickets ==='
SELECT 
    COUNT(*) as total_tickets,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
    COUNT(CASE WHEN status = 'assigned' THEN 1 END) as assigned,
    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved
FROM support_tickets;

\echo ''
\echo '=== 4. Последние тикеты ==='
SELECT 
    t.id,
    t.status,
    c.title as chat_title,
    u.name as user_name,
    o.name as operator_name,
    t.created_at
FROM support_tickets t
JOIN chat_sessions c ON t.chat_id = c.id
JOIN users u ON c.user_id = u.id
LEFT JOIN users o ON t.assigned_operator_id = o.id
ORDER BY t.created_at DESC
LIMIT 5;

\echo ''
\echo '=== 5. Нагрузка операторов ==='
SELECT 
    u.name as operator_name,
    u.email,
    COUNT(CASE WHEN t.status = 'assigned' THEN 1 END) as active_tickets,
    COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved_tickets
FROM users u
LEFT JOIN support_tickets t ON u.id = t.assigned_operator_id
WHERE u.role = 'support'
GROUP BY u.id, u.name, u.email
ORDER BY active_tickets DESC;

\echo ''
\echo '=== Проверка завершена ==='

