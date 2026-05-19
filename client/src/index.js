import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { GeoProvider } from './context/GeoContext';
import { register as registerServiceWorker } from './serviceWorkerRegistration';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <GeoProvider>
        <App />
      </GeoProvider>
    </AuthProvider>
  </React.StrictMode>
);

registerServiceWorker();

