import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import * as authApi from '@/api/auth';
import { getToken, setToken } from '@/api/client';
import type { User } from '@/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  token: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, name: string) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(getToken()));
  const [token, setTok] = useState<string | null>(getToken());

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const u = await authApi.me();
      setUser(u);
    } catch {
      setToken(null);
      setTok(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setUser(res.user);
    setTok(res.token);
    return res.user;
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    const res = await authApi.register(email, password, name);
    setUser(res.user);
    setTok(res.token);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
    setTok(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, token, login, register, logout, refresh }),
    [user, loading, token, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
