import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import ThemeToggle from './ThemeToggle';
import styles from './Header.module.css';

const NAV_ITEMS: Array<{ to: string; label: string; end?: boolean }> = [
  { to: '/', label: 'Главная', end: true },
  { to: '/chat', label: 'Консультация' },
  { to: '/faq', label: 'Вопросы и ответы' },
];

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const close = () => setOpen(false);

  const handleLogout = () => {
    logout();
    close();
    navigate('/');
  };

  const items = user?.role === 'support'
    ? [...NAV_ITEMS, { to: '/operator', label: 'Операторам' }]
    : NAV_ITEMS;

  return (
    <header className={styles.header}>
      <div className={`container ${styles.bar}`}>
        <NavLink to="/" className={styles.logo} onClick={close}>
          <span className={styles.logoMark} aria-hidden="true">▲</span>
          <span className={styles.logoText}>ЧС-Консультант</span>
        </NavLink>

        <button
          type="button"
          className={styles.toggle}
          aria-label="Меню"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={`${styles.nav} ${open ? styles.navOpen : ''}`}>
          <div className={styles.links}>
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.active : ''}`
                }
                onClick={close}
              >
                {item.label}
              </NavLink>
            ))}
          </div>

          <div className={styles.actions}>
            <ThemeToggle />
            {user ? (
              <div className={styles.userBlock}>
                <span className={styles.userName} title={user.email}>
                  {user.name || user.email}
                </span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={handleLogout}>
                  Выйти
                </button>
              </div>
            ) : (
              <div className={styles.authBlock}>
                <NavLink to="/login" className="btn btn-ghost btn-sm" onClick={close}>
                  Войти
                </NavLink>
                <NavLink to="/register" className="btn btn-sm" onClick={close}>
                  Регистрация
                </NavLink>
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

export default Header;
