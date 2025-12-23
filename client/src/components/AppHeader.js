import React from 'react';
import './AppHeader.css';

const MAP_URL =
  'https://gis.72to.ru/orbismap/public_map/geoportal72/map29/#/map/65.507851,57.028528/7/31354,31356,31352,31363,31366,31372,31376,31373,31381,31501,31500,31351,31349';

function AppHeader({ isAuthenticated, onOpenLogin, onOpenRegister, onBackHome, onLogout, hidden }) {
  return (
    <header className={`app-header ${hidden ? 'app-header--hidden' : ''}`}>
      <button type="button" className="app-header__brand" onClick={onBackHome}>
        <p>ЧС 2025 · Тюменская область</p>
        <h1>Цифровой консультант поддержки</h1>
      </button>
      <div className="app-header__actions">
        <a href={MAP_URL} target="_blank" rel="noopener noreferrer" className="header-icon-btn" title="Интерактивная карта">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
        </a>
        {isAuthenticated ? (
          <button type="button" className="header-icon-btn header-icon-btn--danger" onClick={onLogout} title="Выйти">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        ) : (
          <>
            <button type="button" className="header-btn" onClick={onOpenLogin}>
              Войти
            </button>
            <button type="button" className="header-btn" onClick={onOpenRegister}>
              Регистрация
            </button>
          </>
        )}
      </div>
    </header>
  );
}

export default AppHeader;

