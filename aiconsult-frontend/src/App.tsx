import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { SocketProvider } from '@/contexts/SocketContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import ErrorBoundary from '@/components/ErrorBoundary';
import HomePage from '@/pages/HomePage';

const ChatPage = lazy(() => import('@/pages/ChatPage'));
const FAQPage = lazy(() => import('@/pages/FAQPage'));
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/RegisterPage'));
const OperatorPage = lazy(() => import('@/pages/OperatorPage'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

function PageLoader() {
  return (
    <div style={{ padding: '60px 20px', textAlign: 'center' }}>
      <span className="spinner" aria-label="Загрузка" />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <SocketProvider>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route
                  path="/"
                  element={
                    <Layout>
                      <HomePage />
                    </Layout>
                  }
                />
                <Route
                  path="/faq"
                  element={
                    <Layout>
                      <FAQPage />
                    </Layout>
                  }
                />
                <Route
                  path="/login"
                  element={
                    <Layout>
                      <LoginPage />
                    </Layout>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <Layout>
                      <RegisterPage />
                    </Layout>
                  }
                />
                <Route
                  path="/chat"
                  element={
                    <Layout fullHeight>
                      <ChatPage />
                    </Layout>
                  }
                />
                <Route
                  path="/chat/:chatId"
                  element={
                    <ProtectedRoute>
                      <Layout fullHeight>
                        <ChatPage />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operator"
                  element={
                    <ProtectedRoute role="support">
                      <Layout>
                        <OperatorPage />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="*"
                  element={
                    <Layout>
                      <NotFoundPage />
                    </Layout>
                  }
                />
              </Routes>
            </Suspense>
          </SocketProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
