import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="container" style={{ padding: '60px 20px', textAlign: 'center' }}>
      <h1 style={{ fontSize: '3rem', marginBottom: 8 }}>404</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Страница не найдена.</p>
      <Link to="/" className="btn">На главную</Link>
    </div>
  );
}

export default NotFoundPage;
