import { io } from 'socket.io-client';
import { API_BASE_URL } from './api';

let socket = null;

export const initSocket = (token) => {
  if (socket && socket.connected) {
    console.log('Reusing existing socket connection');
    return socket;
  }

  // Если сокет существует, но не подключен, отключаем его
  if (socket) {
    console.log('Disconnecting existing socket');
    socket.disconnect();
    socket = null;
  }

  // Используем тот же базовый URL, что и для HTTP API
  // Это гарантирует, что WebSocket и HTTP подключаются к одному серверу
  // Если REACT_APP_SOCKET_URL не задан, используем тот же URL, что и для HTTP
  const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || API_BASE_URL;
  
  console.log(`🔌 WebSocket connection:`);
  console.log(`   Server URL (HTTP): ${API_BASE_URL}`);
  console.log(`   Socket URL (WS): ${SOCKET_URL}`);
  console.log(`   URLs match: ${API_BASE_URL === SOCKET_URL}`);
  console.log(`   Token provided: ${token ? 'Yes (length: ' + token.length + ')' : 'No'}`);

  if (!token) {
    console.error('❌ No token provided for WebSocket connection');
    throw new Error('Token is required for WebSocket connection');
  }

  socket = io(SOCKET_URL, {
    auth: {
      token: token,
    },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 10,
    forceNew: true, // Принудительно создаем новое соединение
  });

  socket.on('connect', () => {
    console.log('✅ Socket connected successfully, ID:', socket.id);
  });

  socket.on('disconnect', (reason) => {
    console.log('❌ Socket disconnected, reason:', reason);
  });

  socket.on('connect_error', (error) => {
    console.error('❌ Socket connection error:', error.message || error);
  });

  socket.on('reconnect', (attemptNumber) => {
    console.log('🔄 Socket reconnected after', attemptNumber, 'attempts');
  });

  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log('🔄 Reconnection attempt', attemptNumber);
  });

  socket.on('reconnect_error', (error) => {
    console.error('❌ Reconnection error:', error.message || error);
  });

  socket.on('reconnect_failed', () => {
    console.error('❌ Reconnection failed after all attempts');
  });

  return socket;
};

export const getSocket = () => {
  return socket;
};

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};

export const joinChat = (chatId) => {
  if (socket && socket.connected) {
    socket.emit('join_chat', { chatId });
  }
};

export const leaveChat = (chatId) => {
  if (socket && socket.connected) {
    socket.emit('leave_chat', { chatId });
  }
};

export const sendSocketMessage = (chatId, content, token) => {
  if (socket && socket.connected) {
    socket.emit('send_message', { chatId, content, token });
  }
};

export const emitTyping = (chatId, isTyping, token) => {
  if (socket && socket.connected) {
    socket.emit('typing', { chatId, isTyping, token });
  }
};

