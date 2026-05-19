import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { io, type Socket } from 'socket.io-client';
import { useAuth } from './AuthContext';

const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL?.trim() ||
  import.meta.env.VITE_API_URL?.trim() ||
  '';

interface SocketContextValue {
  socket: Socket | null;
  connected: boolean;
  lastError: string | null;
  clearError: () => void;
}

const SocketContext = createContext<SocketContextValue>({
  socket: null,
  connected: false,
  lastError: null,
  clearError: () => {},
});

export function SocketProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
        setConnected(false);
      }
      return;
    }

    const target = SOCKET_URL || window.location.origin;
    const s = io(target, {
      transports: ['websocket', 'polling'],
      auth: { token },
      query: { token },
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1500,
      reconnectionDelayMax: 8000,
    });

    s.on('connect', () => {
      setConnected(true);
      setLastError(null);
    });
    s.on('disconnect', () => setConnected(false));
    s.on('connect_error', (err) => {
      setConnected(false);
      setLastError(err?.message || 'Соединение с сервером недоступно');
    });
    s.on('error', (payload: unknown) => {
      const msg =
        payload && typeof payload === 'object' && 'message' in (payload as Record<string, unknown>)
          ? String((payload as Record<string, unknown>).message)
          : 'Ошибка соединения';
      setLastError(msg);
    });

    socketRef.current = s;

    return () => {
      s.removeAllListeners();
      s.disconnect();
      socketRef.current = null;
      setConnected(false);
    };
  }, [token]);

  const value = useMemo<SocketContextValue>(
    () => ({
      socket: socketRef.current,
      connected,
      lastError,
      clearError: () => setLastError(null),
    }),
    [connected, lastError],
  );

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>;
}

export function useSocket(): SocketContextValue {
  return useContext(SocketContext);
}
