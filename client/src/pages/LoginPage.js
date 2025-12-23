import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import '../App.css';

const LoginPage = ({ initialMode = 'login', onClose }) => {
  const { login, register } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    setMode(initialMode);
    setError('');
    setStatus('');
  }, [initialMode]);

  const handleChange = (evt) => {
    const { name, value } = evt.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (evt) => {
    evt.preventDefault();
    setError('');
    setStatus('');

    if (!form.email.trim() || !form.password.trim()) {
      setError('Введите email и пароль');
      return;
    }

    if (mode === 'register' && !form.name.trim()) {
      setError('Введите имя');
      return;
    }

    if (mode === 'register' && form.password !== form.confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login({ email: form.email, password: form.password });
      } else {
        await register({ name: form.name, email: form.email, password: form.password });
        setStatus('Профиль создан — теперь можно войти.');
        setMode('login');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          {onClose && (
            <button type="button" className="login-close" onClick={onClose} title="Назад">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"/>
                <polyline points="12 19 5 12 12 5"/>
              </svg>
            </button>
          )}
          <div className="login-tabs">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => {
              setMode('login');
              setError('');
              setStatus('');
            }}
          >
            Вход
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'active' : ''}
            onClick={() => {
              setMode('register');
              setError('');
              setStatus('');
            }}
          >
            Регистрация
          </button>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-field">
              <label htmlFor="name">Имя</label>
              <input
                type="text"
                id="name"
                name="name"
                placeholder="Мария"
                value={form.name}
                onChange={handleChange}
                disabled={isSubmitting}
              />
            </div>
          )}
          <div className="form-field">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              disabled={isSubmitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Пароль</label>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="••••••••"
              value={form.password}
              onChange={handleChange}
              disabled={isSubmitting}
            />
          </div>

          {mode === 'register' && (
            <div className="form-field">
              <label htmlFor="confirmPassword">Подтвердите пароль</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                placeholder="••••••••"
                value={form.confirmPassword}
                onChange={handleChange}
                disabled={isSubmitting}
              />
            </div>
          )}

          {error && <div className="form-error">{error}</div>}
          {status && <div className="form-status">{status}</div>}

          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? 'Сохраняем...' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
          </button>
        </form>

      </div>
    </div>
  );
};

export default LoginPage;

