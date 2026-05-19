import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listTickets, resolveTicket } from '@/api/support';
import { useSocket } from '@/contexts/SocketContext';
import type { SupportTicket } from '@/types';
import styles from './OperatorPage.module.css';

const STATUS_LABEL: Record<string, string> = {
  pending: 'Новый',
  assigned: 'В работе',
  resolved: 'Решён',
};

function formatDate(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function OperatorPage() {
  const { socket } = useSocket();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'assigned' | 'resolved'>('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await listTickets();
      setTickets(list);
      setError(null);
    } catch {
      setError('Не удалось загрузить тикеты');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!socket) return;
    const onNew = () => {
      void load();
    };
    const onResolved = () => {
      void load();
    };
    socket.on('new_ticket', onNew);
    socket.on('ticket_resolved', onResolved);
    return () => {
      socket.off('new_ticket', onNew);
      socket.off('ticket_resolved', onResolved);
    };
  }, [socket, load]);

  const handleResolve = useCallback(
    async (chatId: string) => {
      if (!confirm('Отметить тикет как решённый?')) return;
      try {
        await resolveTicket(chatId);
        await load();
      } catch {
        setError('Не удалось завершить тикет');
      }
    },
    [load],
  );

  const filtered = filter === 'all' ? tickets : tickets.filter((t) => t.status === filter);

  return (
    <div className="container">
      <header className={styles.header}>
        <div>
          <h1>Тикеты поддержки</h1>
          <p className="muted">Назначенные на вас обращения и новые запросы.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void load()}>
          Обновить
        </button>
      </header>

      <div className={styles.filters} role="tablist">
        {(['all', 'pending', 'assigned', 'resolved'] as const).map((key) => {
          const count =
            key === 'all' ? tickets.length : tickets.filter((t) => t.status === key).length;
          return (
            <button
              key={key}
              type="button"
              className={`${styles.filter} ${filter === key ? styles.filterActive : ''}`}
              onClick={() => setFilter(key)}
              role="tab"
              aria-selected={filter === key}
            >
              {key === 'all' ? 'Все' : STATUS_LABEL[key]} <span className={styles.count}>{count}</span>
            </button>
          );
        })}
      </div>

      {loading && (
        <div className={styles.empty}>
          <span className="spinner" /> <span className="muted">Загрузка...</span>
        </div>
      )}
      {error && <div className="alert alert-error">{error}</div>}

      {!loading && filtered.length === 0 && !error && (
        <div className={styles.empty}>
          <p className="muted">Тикетов не найдено.</p>
        </div>
      )}

      <div className={styles.list}>
        {filtered.map((t) => (
          <article key={t.id} className={styles.ticket}>
            <div className={styles.ticketHead}>
              <span
                className={`badge ${
                  t.status === 'resolved'
                    ? 'badge-success'
                    : t.status === 'assigned'
                      ? 'badge-warning'
                      : 'badge-danger'
                }`}
              >
                {STATUS_LABEL[t.status] || t.status}
              </span>
              <span className="muted small">{formatDate(t.createdAt)}</span>
            </div>
            <h3 className={styles.ticketTitle}>
              {t.title || t.userName || `Диалог ${t.chatId.slice(0, 8)}`}
            </h3>
            {t.preview && <p className={styles.ticketPreview}>{t.preview}</p>}
            <div className={styles.ticketActions}>
              <Link to={`/chat/${t.chatId}`} className="btn btn-sm">
                Открыть диалог
              </Link>
              {t.status !== 'resolved' && (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => void handleResolve(t.chatId)}
                >
                  Завершить
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export default OperatorPage;
