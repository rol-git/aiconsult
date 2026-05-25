import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import type { UserRole } from '@/types';

interface Props {
  children: ReactNode;
  role?: UserRole;
}

export function ProtectedRoute({ children, role }: Props) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <span className="spinner" aria-label="Загрузка" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export default ProtectedRoute;
