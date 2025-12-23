import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../services/api';

const TOKEN_KEY = 'aiconsult.token';
const PROFILE_KEY = 'aiconsult.profile';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) {
      setIsInitializing(false);
      setUser(null);
      localStorage.removeItem(PROFILE_KEY);
      return;
    }

    const fetchProfile = async () => {
      try {
        const data = await apiRequest('/api/auth/me', { token });
        setUser(data.user);
        localStorage.setItem(PROFILE_KEY, JSON.stringify(data.user));
      } catch (err) {
        console.error(err);
        setToken(null);
        localStorage.removeItem(TOKEN_KEY);
      } finally {
        setIsInitializing(false);
      }
    };

    fetchProfile();
  }, [token]);

  const handleAuthSuccess = (payload) => {
    setToken(payload.token);
    setUser(payload.user);
    localStorage.setItem(TOKEN_KEY, payload.token);
    localStorage.setItem(PROFILE_KEY, JSON.stringify(payload.user));
    setError(null);
    return payload.user;
  };

  const login = async ({ email, password }) => {
    const data = await apiRequest('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    return handleAuthSuccess(data);
  };

  const register = async ({ name, email, password }) => {
    const data = await apiRequest('/api/auth/register', {
      method: 'POST',
      body: { name, email, password },
    });
    return handleAuthSuccess(data);
  };

  const logout = () => {
    const previousUser = user;
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PROFILE_KEY);
    if (previousUser?.id) {
      localStorage.removeItem(`aiconsult.activeChat.${previousUser.id}`);
    }
  };

  const value = useMemo(
    () => ({
      user,
      token,
      isInitializing,
      isAuthenticated: Boolean(user && token),
      error,
      setError,
      login,
      register,
      logout,
    }),
    [user, token, isInitializing, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth должен использоваться внутри AuthProvider');
  }
  return context;
};

