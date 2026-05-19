import { useEffect, useMemo, useState } from 'react';
import { listFAQ } from '@/api/faq';
import type { FAQItem } from '@/types';
import styles from './FAQPage.module.css';

export function FAQPage() {
  const [items, setItems] = useState<FAQItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    listFAQ()
      .then((arr) => {
        if (alive) setItems(arr);
      })
      .catch(() => {
        if (alive) setError('Не удалось загрузить вопросы');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) =>
      (it.question + ' ' + it.answer + ' ' + (it.category || '')).toLowerCase().includes(q),
    );
  }, [items, query]);

  const grouped = useMemo(() => {
    const map = new Map<string, FAQItem[]>();
    for (const it of filtered) {
      const key = it.category || 'Прочее';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(it);
    }
    return Array.from(map.entries());
  }, [filtered]);

  return (
    <div className="container">
      <h1>Часто задаваемые вопросы</h1>
      <p className="muted">Готовые ответы по выплатам, эвакуации и нормативной базе.</p>

      <div className={styles.searchBar}>
        <input
          type="search"
          className="input"
          placeholder="Поиск по вопросам и ответам..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Поиск"
        />
      </div>

      {loading && (
        <div className={styles.empty}>
          <span className="spinner" /> <span className="muted">Загрузка...</span>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className={styles.empty}>
          <p className="muted">Ничего не найдено. Попробуйте задать вопрос ИИ-консультанту.</p>
        </div>
      )}

      <div className={styles.groups}>
        {grouped.map(([category, list]) => (
          <section key={category} className={styles.group}>
            {grouped.length > 1 && <h2 className={styles.groupTitle}>{category}</h2>}
            <div className={styles.list}>
              {list.map((it, i) => {
                const id = String(it.id ?? `${category}-${i}`);
                const open = openId === id;
                return (
                  <div key={id} className={`${styles.item} ${open ? styles.itemOpen : ''}`}>
                    <button
                      type="button"
                      className={styles.question}
                      onClick={() => setOpenId(open ? null : id)}
                      aria-expanded={open}
                    >
                      <span>{it.question}</span>
                      <span className={styles.icon} aria-hidden="true">{open ? '−' : '+'}</span>
                    </button>
                    {open && <div className={styles.answer}>{it.answer}</div>}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

export default FAQPage;
