import React, { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../services/api';

const normalize = (value) => (value || '').toString().trim().toLowerCase();

const FaqPage = ({ isVisible, onClose, onAsk }) => {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isVisible) {
      return;
    }

    // Грузим FAQ только при открытии — этого достаточно и дешевле.
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const data = await apiRequest('/api/faq');
        setItems(Array.isArray(data?.items) ? data.items : []);
      } catch (err) {
        setError(err.message || 'Не удалось загрузить FAQ');
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [isVisible]);

  const filtered = useMemo(() => {
    const q = normalize(query);
    if (!q) {
      return items;
    }
    return items.filter((item) => normalize(item?.question).includes(q));
  }, [items, query]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="faq-overlay" role="dialog" aria-modal="true">
      <div className="faq-panel">
        <div className="faq-header">
          <div>
            <p>Частые вопросы</p>
            <h3>FAQ</h3>
          </div>
          <button className="ghost-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <div className="faq-search">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по вопросам…"
          />
        </div>

        {isLoading && <p className="muted-text">Загружаем FAQ…</p>}
        {error && <div className="inline-error">{error}</div>}

        {!isLoading && !error && filtered.length === 0 && (
          <div className="faq-empty">
            <p>Ничего не нашли. Попробуйте другой запрос.</p>
          </div>
        )}

        <div className="faq-grid">
          {filtered.map((item) => {
            const question = (item?.question || '').trim();
            if (!question) {
              return null;
            }
            return (
              <button
                key={question}
                type="button"
                className="faq-card"
                onClick={() => {
                  onAsk?.(question);
                  onClose?.();
                }}
              >
                <strong>{question}</strong>
                <span>Нажмите, чтобы отправить в чат</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default FaqPage;


