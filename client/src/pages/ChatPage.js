import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
import { initSocket, getSocket, joinChat, leaveChat } from '../services/socket';
import ChatHistory from '../components/ChatHistory';
import QuestionForm from '../components/QuestionForm';
import HistoryPage from './HistoryPage';
import FaqPage from './FaqPage';

const ChatPage = () => {
  const { user, token } = useAuth();
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messagesCache, setMessagesCache] = useState({});
  const [isSidebarLoading, setIsSidebarLoading] = useState(true);
  const [isMessagesLoading, setIsMessagesLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [faqVisible, setFaqVisible] = useState(false);
  const [error, setError] = useState('');
  const [supportTicketsCache, setSupportTicketsCache] = useState({});
  const [showOperatorSuggestion, setShowOperatorSuggestion] = useState(false);
  const [isRequestingSupport, setIsRequestingSupport] = useState(false);
  
  const supportTicket = activeChatId ? supportTicketsCache[activeChatId] : null;

  const activeChatKey = useMemo(
    () => (user ? `aiconsult.activeChat.${user.id}` : null),
    [user]
  );

  const ensureAtLeastOneChat = async () => {
    const created = await apiRequest('/api/chats', { method: 'POST', token });
    return created.chat;
  };

  const loadChats = async () => {
    if (!token || !user) {
      return;
    }

    setIsSidebarLoading(true);
    setError('');

    try {
      const response = await apiRequest('/api/chats', { token });
      let fetchedChats = response.chats || [];

      if (!fetchedChats.length) {
        const newChat = await ensureAtLeastOneChat();
        fetchedChats = [newChat];
      }

      setChats(fetchedChats);

      let nextActive = activeChatKey ? localStorage.getItem(activeChatKey) : null;
      if (!nextActive || !fetchedChats.some((chat) => chat.id === nextActive)) {
        nextActive = fetchedChats[0]?.id || null;
      }
      setActiveChatId(nextActive);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setIsSidebarLoading(false);
    }
  };

  // Инициализация WebSocket при монтировании
  useEffect(() => {
    if (!token) return;

    const socket = initSocket(token);

    socket.on('connect', () => {
      console.log('Chat WebSocket connected:', socket.id);
    });

    socket.on('disconnect', (reason) => {
      console.log('Chat WebSocket disconnected:', reason);
    });

    socket.on('connect_error', (error) => {
      console.error('Chat WebSocket connection error:', error);
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('connect_error');
    };
  }, [token]);

  useEffect(() => {
    loadChats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, user?.id]);

  useEffect(() => {
    if (!activeChatId || !token) {
      return;
    }

    if (activeChatKey) {
      localStorage.setItem(activeChatKey, activeChatId);
    }

    // Подключаемся к комнате чата через WebSocket (только если подключен)
    const socket = getSocket();
    if (socket && socket.connected) {
      joinChat(activeChatId);
    } else {
      // Ждем подключения
      const onConnect = () => {
        joinChat(activeChatId);
      };
      if (socket) {
        socket.once('connect', onConnect);
        return () => {
          socket.off('connect', onConnect);
        };
      }
    }

    if (messagesCache[activeChatId]) {
      setMessages(messagesCache[activeChatId]);
      return;
    }

    const loadMessages = async () => {
      setIsMessagesLoading(true);
      setError('');
      try {
        const data = await apiRequest(`/api/chats/${activeChatId}`, { token });
        setMessages(data.messages);
        setMessagesCache((prev) => ({ ...prev, [activeChatId]: data.messages }));
        setChats((prev) =>
          prev.map((chat) => (chat.id === data.chat.id ? data.chat : chat))
        );

        // Загружаем тикет для этого чата, если он есть (используем эндпоинт для пользователей)
        try {
          const ticketData = await apiRequest(`/api/support/tickets/my/${activeChatId}`, { token });
          if (ticketData && ticketData.status !== 'resolved') {
            setSupportTicketsCache((prev) => ({
              ...prev,
              [activeChatId]: ticketData,
            }));
            console.log('✅ Тикет загружен при открытии чата:', ticketData);
          }
        } catch (ticketErr) {
          // Если тикета нет - это нормально, просто игнорируем
          if (!ticketErr.message?.includes('404')) {
            console.error('Error loading ticket:', ticketErr);
          }
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setIsMessagesLoading(false);
      }
    };

    loadMessages();

    // Отключаемся от комнаты при размонтировании
    return () => {
      leaveChat(activeChatId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChatId, token]);

  // WebSocket обработчики
  useEffect(() => {
    const socket = getSocket();
    if (!socket) return;

    const handleNewMessage = (message) => {
      console.log('New message received:', message);
      
      const chatId = message.chatId || activeChatId;
      
      // Удаляем оптимистичные сообщения (с temp- префиксом) с таким же content
      // Это предотвращает дубликаты при получении реального сообщения
      setMessages((prev) => {
        const filtered = prev.filter((msg) => {
          // Удаляем оптимистичные сообщения (temp- префикс) с таким же content от того же отправителя
          if (msg.id && msg.id.startsWith('temp-')) {
            if (msg.role === message.role && msg.content === message.content) {
              console.log('🗑️ Удаляем оптимистичное сообщение:', msg.id);
              return false;
            }
          }
          // Не добавляем дубликаты по ID
          if (msg.id === message.id) {
            return false;
          }
          return true;
        });
        
        // Проверяем, нет ли уже такого сообщения
        if (filtered.some(m => m.id === message.id)) {
          return filtered;
        }
        
        return [...filtered, message];
      });
      
      // Обновляем кэш сообщений
      setMessagesCache((prev) => {
        const currentMessages = prev[chatId] || [];
        
        // Удаляем оптимистичные сообщения
        const filtered = currentMessages.filter((msg) => {
          if (msg.id && msg.id.startsWith('temp-')) {
            if (msg.role === message.role && msg.content === message.content) {
              return false;
            }
          }
          if (msg.id === message.id) {
            return false;
          }
          return true;
        });
        
        // Проверяем, нет ли уже такого сообщения
        if (filtered.some(m => m.id === message.id)) {
          return prev;
        }
        
        return {
          ...prev,
          [chatId]: [...filtered, message],
        };
      });
    };

    const handleTicketResolved = (data) => {
      if (data.chatId) {
        console.log('✅ Тикет решен:', data.chatId);
        // Обновляем статус тикета на resolved
        setSupportTicketsCache((prev) => {
          const updated = { ...prev };
          if (updated[data.chatId]) {
            updated[data.chatId] = {
              ...updated[data.chatId],
              status: 'resolved'
            };
          }
          return updated;
        });
        if (data.chatId === activeChatId) {
          setShowOperatorSuggestion(false);
        }
      }
    };

    socket.on('new_message', handleNewMessage);
    socket.on('ticket_resolved', handleTicketResolved);

    return () => {
      socket.off('new_message', handleNewMessage);
      socket.off('ticket_resolved', handleTicketResolved);
    };
  }, [activeChatId]);

  const handleSendMessage = async (content) => {
    if (!content.trim() || !activeChatId) {
      setError('Выберите диалог или создайте новый, чтобы отправить сообщение.');
      return;
    }

    const currentTicket = supportTicketsCache[activeChatId];
    const hasActiveTicket = currentTicket && currentTicket.status !== 'resolved';
    
    console.log('📤 Отправка сообщения:', {
      chatId: activeChatId,
      hasActiveTicket,
      ticketStatus: currentTicket?.status,
      ticket: currentTicket
    });

    // Если есть активный тикет - отправляем через WebSocket, а не к нейросети
    if (hasActiveTicket) {
      console.log('✅ Отправка через WebSocket (активный тикет)');
      const tempId = `temp-${Date.now()}`;
      const optimisticMessage = {
        id: tempId,
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, optimisticMessage]);
      setMessagesCache((prev) => ({
        ...prev,
        [activeChatId]: [...(prev[activeChatId] || []), optimisticMessage],
      }));
      setIsSending(true);
      setError('');

      try {
        let socket = getSocket();
        
        // Если сокет не инициализирован или не подключен, пытаемся инициализировать
        if (!socket) {
          socket = initSocket(token);
          // Ждем подключения
          await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Таймаут подключения WebSocket'));
            }, 5000);
            
            if (socket.connected) {
              clearTimeout(timeout);
              resolve();
            } else {
              socket.once('connect', () => {
                clearTimeout(timeout);
                resolve();
              });
              socket.once('connect_error', (error) => {
                clearTimeout(timeout);
                reject(error);
              });
            }
          });
        } else if (!socket.connected) {
          // Если сокет есть, но не подключен, ждем подключения
          await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Таймаут подключения WebSocket'));
            }, 5000);
            
            socket.once('connect', () => {
              clearTimeout(timeout);
              resolve();
            });
            socket.once('connect_error', (error) => {
              clearTimeout(timeout);
              reject(error);
            });
          });
        }

        // Отправляем сообщение
        socket.emit('send_message', {
          chatId: activeChatId,
          content,
          token,
        });

        // Не удаляем оптимистичное сообщение по таймауту - оно будет удалено
        // автоматически в handleNewMessage при получении реального сообщения
      } catch (err) {
        setMessages((prev) => prev.filter((msg) => msg.id !== tempId));
        setMessagesCache((prev) => ({
          ...prev,
          [activeChatId]: (prev[activeChatId] || []).filter((msg) => msg.id !== tempId),
        }));
        setError(err.message || 'Ошибка при отправке сообщения. Попробуйте перезагрузить страницу.');
      } finally {
        setIsSending(false);
      }
      return;
    }

    // Обычная отправка к нейросети (если нет активного тикета)
    console.log('🤖 Отправка к нейросети (нет активного тикета)');
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage = {
      id: tempId,
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    setMessagesCache((prev) => ({
      ...prev,
      [activeChatId]: [...(prev[activeChatId] || []), optimisticMessage],
    }));
    setIsSending(true);
    setError('');

    try {
      const data = await apiRequest(`/api/chats/${activeChatId}/messages`, {
        method: 'POST',
        body: { content },
        token,
      });

      setMessages((prev) => [
        ...prev.filter((msg) => msg.id !== tempId),
        ...data.messages,
      ]);
      setMessagesCache((prev) => ({
        ...prev,
        [activeChatId]: [
          ...((prev[activeChatId] || []).filter((msg) => msg.id !== tempId)),
          ...data.messages,
        ],
      }));

      setChats((prev) => {
        const updated = prev.map((chat) => (chat.id === data.chat.id ? data.chat : chat));
        updated.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
        return updated;
      });

      // Проверяем, предлагает ли система оператора
      const lastMessage = data.messages[data.messages.length - 1];
      if (lastMessage && lastMessage.suggestOperator) {
        setShowOperatorSuggestion(true);
      }
    } catch (err) {
      setMessages((prev) => prev.filter((msg) => msg.id !== tempId));
      setMessagesCache((prev) => ({
        ...prev,
        [activeChatId]: (prev[activeChatId] || []).filter((msg) => msg.id !== tempId),
      }));
      setError(err.message);
    } finally {
      setIsSending(false);
    }
  };

  const handleNewChat = async () => {
    setError('');
    
    // Проверяем, есть ли пустой диалог
    const emptyChat = chats.find(chat => {
      const cached = messagesCache[chat.id];
      return cached && cached.length === 0;
    });
    
    if (emptyChat) {
      // Переключаемся на существующий пустой диалог
      setActiveChatId(emptyChat.id);
      return;
    }
    
    try {
      const data = await apiRequest('/api/chats', { method: 'POST', token });
      setChats((prev) => [data.chat, ...prev]);
      setMessages([]);
      setMessagesCache((prev) => ({ ...prev, [data.chat.id]: [] }));
      setActiveChatId(data.chat.id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectFromHistory = (chatId) => {
    setActiveChatId(chatId);
  };

  const handleDeleteChat = async (chatId, e) => {
    e.stopPropagation();
    
    if (!window.confirm('Удалить этот диалог?')) {
      return;
    }

    try {
      await apiRequest(`/api/chats/${chatId}`, { method: 'DELETE', token });
      
      const updatedChats = chats.filter((chat) => chat.id !== chatId);
      setChats(updatedChats);
      
      // Удаляем из кэша
      setMessagesCache((prev) => {
        const { [chatId]: _, ...rest } = prev;
        return rest;
      });

      // Если удалили активный чат, переключаемся на другой
      if (activeChatId === chatId) {
        if (updatedChats.length > 0) {
          setActiveChatId(updatedChats[0].id);
        } else {
          // Создаем новый чат если не осталось
          handleNewChat();
        }
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRequestSupport = async () => {
    if (!activeChatId) {
      setError('Нет активного чата');
      return;
    }

    setIsRequestingSupport(true);
    setError('');

    try {
      const response = await apiRequest('/api/support/request', {
        method: 'POST',
        body: { chatId: activeChatId },
        token,
      });

      // Загружаем полный тикет после создания (используем эндпоинт для пользователей)
      try {
        const fullTicket = await apiRequest(`/api/support/tickets/my/${activeChatId}`, { token });
        if (fullTicket) {
          setSupportTicketsCache((prev) => ({
            ...prev,
            [activeChatId]: fullTicket,
          }));
          console.log('✅ Тикет создан и загружен:', fullTicket);
        } else {
          // Если не удалось загрузить, используем данные из ответа
          setSupportTicketsCache((prev) => ({
            ...prev,
            [activeChatId]: response.ticket,
          }));
        }
      } catch (ticketErr) {
        console.error('Ошибка загрузки тикета:', ticketErr);
        // Используем данные из ответа создания
        setSupportTicketsCache((prev) => ({
          ...prev,
          [activeChatId]: response.ticket,
        }));
      }
      setShowOperatorSuggestion(false);

      const systemMessage = {
        id: `system-${Date.now()}`,
        role: 'system',
        content: 'Ваш запрос направлен оператору. Пожалуйста, ожидайте ответа.',
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, systemMessage]);
      setMessagesCache((prev) => ({
        ...prev,
        [activeChatId]: [...(prev[activeChatId] || []), systemMessage],
      }));
    } catch (err) {
      if (err.message && (err.message.includes('операторы заняты') || err.message.includes('горячую линию'))) {
        alert(err.message);
      } else {
        setError(err.message || 'Ошибка при запросе оператора');
      }
    } finally {
      setIsRequestingSupport(false);
    }
  };

  const handleDismissOperatorSuggestion = () => {
    setShowOperatorSuggestion(false);
  };

  return (
    <div className="workspace">
      <aside className="workspace__sidebar">
        <div className="workspace__sidebar-list">
          {isSidebarLoading && <p className="muted-text">Загружаем чаты...</p>}
          {!isSidebarLoading && chats.length === 0 && (
            <p className="muted-text">Диалогов пока нет</p>
          )}
          {!isSidebarLoading &&
            chats.map((chat) => {
              const normalizedTitle = chat.title?.trim();
              const preview = chat.lastPreview?.trim();
              const cachedMessages = messagesCache[chat.id];
              const isEmpty = cachedMessages && cachedMessages.length === 0;
              const isLastChat = chats.length === 1;
              const canDelete = !(isLastChat && isEmpty);
              
              return (
                <div
                  key={chat.id}
                  className={`workspace__chat ${chat.id === activeChatId ? 'active' : ''}`}
                  onClick={() => setActiveChatId(chat.id)}
                >
                  <span className="workspace__chat-title">{normalizedTitle || preview || 'Без названия'}</span>
                  {canDelete && (
                    <button
                      type="button"
                      className="workspace__chat-delete"
                      onClick={(e) => handleDeleteChat(chat.id, e)}
                      title="Удалить диалог"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18"/>
                        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
                      </svg>
                    </button>
                  )}
                </div>
              );
            })}
        </div>
        <div className="workspace__sidebar-footer">
          <div className="sidebar-user">
            <span className="sidebar-user__name">{user?.name}</span>
            <small className="sidebar-user__email">{user?.email}</small>
          </div>
          <div className="sidebar-actions">
            <button
              className="fab-button fab-button--faq"
              type="button"
              onClick={() => setFaqVisible(true)}
              title="Частые вопросы"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 8a5 5 0 0 1 9.5 2c0 3-5 4-5 4"/>
                <line x1="12" y1="20" x2="12.01" y2="20"/>
              </svg>
            </button>
            <button
              className="fab-button fab-button--new"
              type="button"
              onClick={handleNewChat}
              title="Новый диалог"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <section className="workspace__content">
        <div className="workspace__messages">
          <ChatHistory
            messages={messages}
            isLoading={isMessagesLoading}
            isSending={isSending}
            onSuggestionSelect={handleSendMessage}
            onRequestSupport={handleRequestSupport}
            showOperatorButton={!supportTicket && !isRequestingSupport}
          />
        </div>
        {showOperatorSuggestion && !supportTicket && (
          <div className="operator-suggestion">
            <div className="operator-suggestion-content">
              <p>Похоже, вам может понадобиться помощь специалиста. Хотите связаться с оператором?</p>
              <div className="operator-suggestion-actions">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleRequestSupport}
                  disabled={isRequestingSupport}
                >
                  {isRequestingSupport ? 'Отправка запроса...' : 'Связаться с оператором'}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleDismissOperatorSuggestion}
                >
                  Продолжить с AI
                </button>
              </div>
            </div>
          </div>
        )}
        {supportTicket && supportTicket.status !== 'resolved' && (
          <div className="support-status-banner">
            <span className="support-status-icon">👤</span>
            <span>Оператор подключен к диалогу</span>
          </div>
        )}
        <div className="workspace__composer">
          <QuestionForm
            onSubmit={handleSendMessage}
            isLoading={isSending}
            disabled={!activeChatId}
          />
          {error && <div className="inline-error">{error}</div>}
        </div>
      </section>

      <HistoryPage
        isVisible={historyVisible}
        chats={chats}
        onSelect={handleSelectFromHistory}
        onClose={() => setHistoryVisible(false)}
      />

      <FaqPage
        isVisible={faqVisible}
        onClose={() => setFaqVisible(false)}
        onAsk={(question) => handleSendMessage(question)}
      />
    </div>
  );
};

export default ChatPage;

