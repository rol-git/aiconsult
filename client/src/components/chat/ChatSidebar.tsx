import { memo } from 'react';
import type { Chat } from '@/types';
import styles from './ChatSidebar.module.css';

interface Props {
  chats: Chat[];
  currentId?: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  loading?: boolean;
  open: boolean;
  onClose: () => void;
}

function formatDate(iso?: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    if (sameDay) return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
  } catch {
    return '';
  }
}

function ChatSidebarImpl({
  chats,
  currentId,
  onSelect,
  onCreate,
  onDelete,
  loading,
  open,
  onClose,
}: Props) {
  return (
    <>
      <aside className={`${styles.sidebar} ${open ? styles.open : ''}`} aria-label="Список диалогов">
        <div className={styles.header}>
          <button type="button" className="btn btn-block" onClick={onCreate}>
            + Новый диалог
          </button>
        </div>

        <div className={styles.list}>
          {loading && chats.length === 0 && (
            <div className={styles.empty}>
              <span className="spinner" /> <span className="muted small">Загрузка...</span>
            </div>
          )}
          {!loading && chats.length === 0 && (
            <div className={styles.empty}>
              <div className="muted small">У вас пока нет диалогов</div>
            </div>
          )}
          {chats.map((c) => (
            <div
              key={c.id}
              className={`${styles.item} ${c.id === currentId ? styles.itemActive : ''}`}
            >
              <button
                type="button"
                className={styles.itemBtn}
                onClick={() => {
                  onSelect(c.id);
                  onClose();
                }}
              >
                <div className={styles.itemTitle}>{c.title || 'Без названия'}</div>
                {c.lastPreview && <div className={styles.itemPreview}>{c.lastPreview}</div>}
                <div className={styles.itemDate}>{formatDate(c.updatedAt || c.createdAt)}</div>
              </button>
              <button
                type="button"
                className={styles.delete}
                aria-label="Удалить диалог"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('Удалить диалог?')) onDelete(c.id);
                }}
                title="Удалить"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>
      {open && <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />}
    </>
  );
}

export const ChatSidebar = memo(ChatSidebarImpl);
