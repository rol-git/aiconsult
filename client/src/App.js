import React, { useState, useEffect } from 'react';
import './App.css';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import GuestChatPage from './pages/GuestChatPage';
import SupportPage from './pages/SupportPage';
import AppHeader from './components/AppHeader';
import { initSocket, disconnectSocket } from './services/socket';

function App() {
  const { isInitializing, isAuthenticated, user, token, logout } = useAuth();
  const [authMode, setAuthMode] = useState(null); // 'login' | 'register' | null

  // Инициализация WebSocket при аутентификации
  useEffect(() => {
    if (isAuthenticated && token) {
      initSocket(token);
    } else {
      disconnectSocket();
    }

    return () => {
      disconnectSocket();
    };
  }, [isAuthenticated, token]);

  const renderBody = () => {
    if (isInitializing) {
      return (
        <div className="app-loading-screen">
          <div className="loading-spinner" />
          <p>Загружаем ваш профиль...</p>
        </div>
      );
    }

    if (isAuthenticated) {
      // Если пользователь - оператор поддержки, показываем панель поддержки
      if (user?.role === 'support') {
        return <SupportPage />;
      }
      return <ChatPage />;
    }

    if (authMode) {
      return <LoginPage initialMode={authMode} onClose={() => setAuthMode(null)} />;
    }

    return <GuestChatPage />;
  };

  return (
    <div className="App">
      <div className="app-shell">
        <AppHeader
          isAuthenticated={isAuthenticated}
          onOpenLogin={() => setAuthMode('login')}
          onOpenRegister={() => setAuthMode('register')}
          onBackHome={() => setAuthMode(null)}
          onLogout={logout}
          hidden={false}
        />
        <main className="app-main">
          {renderBody()}
      </main>
      </div>
    </div>
  );
}

export default App;

