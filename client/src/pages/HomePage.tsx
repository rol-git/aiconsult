import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getOnlineOperators } from '@/api/support';
import { useAuth } from '@/contexts/AuthContext';
import styles from './HomePage.module.css';

const QUICK_QUESTIONS = [
  'Как получить выплату после паводка?',
  'Что делать прямо сейчас при угрозе подтопления?',
  'Какие документы нужны для эвакуации?',
  'Куда обращаться за компенсацией?',
];

const FEATURES = [
  {
    title: 'Выплаты и компенсации',
    desc: 'Подробные инструкции по получению финансовой поддержки и компенсаций.',
  },
  {
    title: 'Действия прямо сейчас',
    desc: 'Что делать в первые минуты при возникновении ЧС: эвакуация, спасение имущества, связь.',
  },
  {
    title: 'Нормативные разъяснения',
    desc: 'Ответы на основе официальных документов и законов Тюменской области.',
  },
  {
    title: 'Подготовка документов',
    desc: 'Помощь в оформлении заявлений, актов, обращений и других документов.',
  },
];

export function HomePage() {
  const { user } = useAuth();
  const [operatorsOnline, setOperatorsOnline] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    getOnlineOperators()
      .then((res) => {
        if (alive) setOperatorsOnline(res.count ?? (res.hasOperators ? 1 : 0));
      })
      .catch(() => {
        if (alive) setOperatorsOnline(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="container">
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <span className="badge badge-primary">Тюменская область</span>
          <h1 className={styles.title}>
            ИИ-консультант при чрезвычайных ситуациях
          </h1>
          <p className={styles.lead}>
            Получите помощь по паводкам, эвакуации, выплатам и оформлению документов.
            Ответы готовятся на основе официальных нормативных документов.
          </p>
          <div className={styles.actions}>
            <Link to="/chat" className="btn">Задать вопрос</Link>
            <Link to="/faq" className="btn btn-secondary">Частые вопросы</Link>
          </div>
          {operatorsOnline !== null && (
            <div className={styles.statusRow}>
              <span className={`${styles.dot} ${operatorsOnline > 0 ? styles.dotOn : styles.dotOff}`} />
              {operatorsOnline > 0
                ? `Операторов на связи: ${operatorsOnline}`
                : 'Операторы поддержки сейчас недоступны'}
            </div>
          )}
        </div>

        <aside className={styles.emergencyCard} aria-label="Экстренные контакты">
          <div className={styles.emergencyTitle}>Экстренные службы</div>
          <ul className={styles.emergencyList}>
            <li>
              <a href="tel:112">112 — Единый номер</a>
              <span className="muted small">с мобильного и стационарного</span>
            </li>
            <li>
              <a href="tel:101">101 — Пожарная охрана и МЧС</a>
            </li>
            <li>
              <a href="tel:103">103 — Скорая помощь</a>
            </li>
            <li>
              <a href="tel:8-800-100-94-00">8-800-100-94-00 — Горячая линия МЧС</a>
            </li>
          </ul>
        </aside>
      </section>

      <section className={styles.section}>
        <h2>Популярные вопросы</h2>
        <p className="muted">Нажмите на вопрос — мы откроем чат с ИИ-консультантом.</p>
        <div className={styles.quickList}>
          {QUICK_QUESTIONS.map((q) => (
            <Link
              key={q}
              to={`/chat?q=${encodeURIComponent(q)}`}
              className={styles.quickItem}
            >
              <span>{q}</span>
              <span aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2>Чем может помочь система</h2>
        <div className={styles.features}>
          {FEATURES.map((f) => (
            <article key={f.title} className={styles.feature}>
              <h3>{f.title}</h3>
              <p className="muted small">{f.desc}</p>
            </article>
          ))}
        </div>
      </section>

      {!user && (
        <section className={`${styles.section} ${styles.ctaBlock}`}>
          <div>
            <h2>Сохраните историю обращений</h2>
            <p className="muted">
              Зарегистрируйтесь, чтобы вернуться к диалогам, продолжить с того же места и
              при необходимости связаться с реальным оператором поддержки.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link to="/register" className="btn">Создать аккаунт</Link>
            <Link to="/login" className="btn btn-secondary">Войти</Link>
          </div>
        </section>
      )}
    </div>
  );
}

export default HomePage;
