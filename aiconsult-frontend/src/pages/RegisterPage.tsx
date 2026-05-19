import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { HttpError } from '@/api/client';
import styles from './AuthPage.module.css';

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов');
      return;
    }
    if (password !== confirm) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
      navigate('/chat', { replace: true });
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Не удалось зарегистрироваться');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={`card ${styles.card}`}>
        <h1 className={styles.title}>Регистрация</h1>
        <p className={styles.subtitle}>
          Создайте аккаунт, чтобы сохранять диалоги и обращаться к оператору.
        </p>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          <div className="field">
            <label htmlFor="reg-name">Имя</label>
            <input
              id="reg-name"
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              disabled={loading}
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
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
            <label htmlFor="reg-password">Пароль</label>
            <input
              id="reg-password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={6}
              disabled={loading}
            />
          </div>

          <div className="field">
            <label htmlFor="reg-confirm">Повторите пароль</label>
            <input
              id="reg-confirm"
              type="password"
              className="input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
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
            {loading ? <span className="spinner" /> : 'Создать аккаунт'}
          </button>
        </form>

        <div className={styles.altRow}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
