import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('app:error', { detail: { error, info } }),
      );
    }
  }

  private handleReset = () => {
    this.setState({ error: null });
  };

  private handleReload = () => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          role="alert"
          style={{
            maxWidth: 520,
            margin: '60px auto',
            padding: '24px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            textAlign: 'center',
            color: 'var(--color-text)',
          }}
        >
          <h2 style={{ marginBottom: 8 }}>Что-то пошло не так</h2>
          <p style={{ color: 'var(--color-text-soft)', marginBottom: 16 }}>
            Произошла непредвиденная ошибка. Попробуйте обновить страницу.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button type="button" className="btn" onClick={this.handleReload}>
              Обновить
            </button>
            <button type="button" className="btn btn-secondary" onClick={this.handleReset}>
              Попробовать ещё раз
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
