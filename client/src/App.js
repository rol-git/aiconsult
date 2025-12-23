import React, { useState } from 'react';
import './App.css';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import GuestChatPage from './pages/GuestChatPage';
import AppHeader from './components/AppHeader';

function App() {
  const { isInitializing, isAuthenticated, logout } = useAuth();
  const [authMode, setAuthMode] = useState(null); // 'login' | 'register' | null

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

