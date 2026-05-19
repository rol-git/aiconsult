import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { HttpError } from '@/api/client';
import styles from './AuthPage.module.css';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      const from = (location.state as { from?: string } | null)?.from || '/chat';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Не удалось войти');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={`card ${styles.card}`}>
        <h1 className={styles.title}>Вход</h1>
        <p className={styles.subtitle}>Войдите, чтобы сохранять историю обращений.</p>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              disabled={loading}
            />
          </div>

          <div className="field">
            <label htmlFor="login-password">Пароль</label>
            <input
              id="login-password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className={`btn btn-block ${styles.actions}`} disabled={loading}>
            {loading ? <span className="spinner" /> : 'Войти'}
          </button>
        </form>

        <div className={styles.altRow}>
          Ещё нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
