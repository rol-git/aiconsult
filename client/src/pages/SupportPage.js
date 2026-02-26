import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
import { initSocket, getSocket, joinChat, leaveChat } from '../services/socket';
import ChatHistory from '../components/ChatHistory';
import QuestionForm from '../components/QuestionForm';
import './SupportPage.css';

const SupportPage = () => {
  const { user, token } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [activeTicketId, setActiveTicketId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messagesCache, setMessagesCache] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isMessagesLoading, setIsMessagesLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [typingUsers, setTypingUsers] = useState({});
  const [isSocketConnected, setIsSocketConnected] = useState(false);

  // Инициализация WebSocket
  useEffect(() => {
    if (!token) return;

    const socket = initSocket(token);

    // Обработчик подключения
    socket.on('connect', () => {
      console.log('Support WebSocket connected, socket ID:', socket.id);
      setIsSocketConnected(true);
    });

    socket.on('disconnect', (reason) => {
      console.log('Support WebSocket disconnected, reason:', reason);
      setIsSocketConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('Support WebSocket connection error:', error);
      setIsSocketConnected(false);
    });

    // Обработчик новых сообщений
    socket.on('new_message', (message) => {
      console.log('New message received:', message);
      
      // Обновляем кэш сообщений для соответствующего чата
      setMessagesCache((prev) => {
        const chatId = message.chatId || activeTicketId;
        const currentMessages = prev[chatId] || [];
        
        // Проверяем, не дублируется ли сообщение
        if (currentMessages.some(m => m.id === message.id)) {
          return prev;
        }
        
        return {
          ...prev,
          [chatId]: [...currentMessages, message],
        };
      });

      // Если это активный чат, обновляем messages
      if (activeTicketId && message.chatId === activeTicketId) {
        setMessages((prev) => {
          if (prev.some(m => m.id === message.id)) {
            return prev;
          }
          return [...prev, message];
        });
      }

      // Обновляем превью в списке тикетов
      setTickets((prev) =>
        prev.map((ticket) =>
          ticket.id === message.chatId
            ? {
                ...ticket,
                lastPreview: message.content.substring(0, 120) + (message.content.length > 120 ? '…' : ''),
                updatedAt: new Date().toISOString(),
              }
            : ticket
        )
      );
    });

    // Обработчик нового тикета
    socket.on('new_ticket', (data) => {
      console.log('New ticket received:', data);
      loadTickets();
    });

    // Обработчик решенного тикета
    socket.on('ticket_resolved', (data) => {
      console.log('Ticket resolved:', data);
      setTickets((prev) =>
        prev.map((ticket) =>
          ticket.id === data.chatId
            ? { ...ticket, ticketStatus: 'resolved' }
            : ticket
        )
      );
    });

    // Обработчик печати
    socket.on('user_typing', (data) => {
      if (data.chatId === activeTicketId) {
        setTypingUsers((prev) => ({
          ...prev,
          [data.chatId]: data.isTyping ? data.userName : null,
        }));

        // Убираем индикатор через 3 секунды
        if (data.isTyping) {
          setTimeout(() => {
            setTypingUsers((prev) => ({
              ...prev,
              [data.chatId]: null,
            }));
          }, 3000);
        }
      }
    });

    return () => {
      socket.off('new_message');
      socket.off('new_ticket');
      socket.off('ticket_resolved');
      socket.off('user_typing');
    };
  }, [token, activeTicketId]);

  // Загрузка тикетов
  const loadTickets = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await apiRequest('/api/support/tickets', { token });
      setTickets(response.tickets || []);

      // Если есть активный тикет, проверяем его наличие
      if (activeTicketId && !response.tickets.some(t => t.id === activeTicketId)) {
        setActiveTicketId(null);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [token, activeTicketId]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  // Загрузка сообщений для выбранного тикета
  useEffect(() => {
    if (!activeTicketId || !token) {
      return;
    }

    // Подключаемся к комнате чата
    joinChat(activeTicketId);

    // Если сообщения уже в кэше, используем их
    if (messagesCache[activeTicketId]) {
      setMessages(messagesCache[activeTicketId]);
      return;
    }

    const loadMessages = async () => {
      setIsMessagesLoading(true);
      setError('');
      try {
        const data = await apiRequest(`/api/support/tickets/${activeTicketId}`, { token });
        setMessages(data.messages);
        setMessagesCache((prev) => ({ ...prev, [activeTicketId]: data.messages }));
        
        // Обновляем тикет в списке
        setTickets((prev) =>
          prev.map((ticket) => (ticket.id === data.ticket.id ? data.ticket : ticket))
        );
      } catch (err) {
        setError(err.message);
      } finally {
        setIsMessagesLoading(false);
      }
    };

    loadMessages();

    // Подключаемся к комнате чата через WebSocket (только если подключен)
    const socket = getSocket();
    if (socket && socket.connected) {
      joinChat(activeTicketId);
    } else if (socket) {
      // Ждем подключения
      const onConnect = () => {
        joinChat(activeTicketId);
      };
      socket.once('connect', onConnect);
      return () => {
        socket.off('connect', onConnect);
        leaveChat(activeTicketId);
      };
    }

    // Отключаемся от комнаты при размонтировании
    return () => {
      leaveChat(activeTicketId);
    };
  }, [activeTicketId, token, messagesCache]);

  const handleSendMessage = async (content) => {
    if (!content.trim() || !activeTicketId) {
      setError('Выберите тикет для отправки сообщения.');
      return;
    }

    const activeTicket = tickets.find(t => t.id === activeTicketId);
    if (activeTicket && activeTicket.ticketStatus === 'resolved') {
      setError('Этот тикет уже решен. Вы не можете отправлять сообщения.');
      return;
    }

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

      // Отправляем через WebSocket
      // Сообщение придет обратно через событие 'new_message'
      socket.emit('send_message', {
        chatId: activeTicketId,
        content,
        token,
      });
      
      console.log('Message sent via WebSocket:', { chatId: activeTicketId, content });
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message || 'Ошибка при отправке сообщения. Попробуйте перезагрузить страницу.');
    } finally {
      setIsSending(false);
    }
  };

  const handleResolveTicket = async () => {
    if (!activeTicketId) return;

    if (!window.confirm('Отметить этот тикет как решенный?')) {
      return;
    }

    try {
      await apiRequest(`/api/support/tickets/${activeTicketId}/resolve`, {
        method: 'POST',
        token,
      });

      // Обновляем статус тикета
      setTickets((prev) =>
        prev.map((ticket) =>
          ticket.id === activeTicketId
            ? { ...ticket, ticketStatus: 'resolved', resolvedAt: new Date().toISOString() }
            : ticket
        )
      );

      // Перезагружаем тикеты
      loadTickets();
    } catch (err) {
      setError(err.message);
    }
  };

  const getTicketClassName = (ticket) => {
    let className = 'support-ticket';
    if (ticket.id === activeTicketId) {
      className += ' active';
    }
    if (ticket.ticketStatus === 'resolved') {
      className += ' resolved';
    }
    return className;
  };

  const activeTicket = tickets.find(t => t.id === activeTicketId);
  const canSendMessages = activeTicket && activeTicket.ticketStatus !== 'resolved';

  return (
    <div className="support-workspace">
      <aside className="support-sidebar">
        <div className="support-sidebar-header">
          <h2>Панель поддержки</h2>
          <p className="support-operator-name">{user?.name}</p>
          {/* <div className="support-connection-status">
            <span className={`status-indicator ${isSocketConnected ? 'connected' : 'disconnected'}`}>
              {isSocketConnected ? '🟢 Онлайн' : '🔴 Офлайн'}
            </span>
          </div> */}
        </div>
        <div className="support-sidebar-list">
          {isLoading && <p className="muted-text">Загружаем тикеты...</p>}
          {!isLoading && tickets.length === 0 && (
            <p className="muted-text">Нет активных тикетов</p>
          )}
          {!isLoading &&
            tickets.map((ticket) => (
              <div
                key={ticket.id}
                className={getTicketClassName(ticket)}
                onClick={() => setActiveTicketId(ticket.id)}
              >
                <div className="support-ticket-header">
                  <span className="support-ticket-user">{ticket.userName}</span>
                  <span className={`support-ticket-status status-${ticket.ticketStatus}`}>
                    {ticket.ticketStatus === 'pending' && 'Ожидает'}
                    {ticket.ticketStatus === 'assigned' && 'Назначен'}
                    {ticket.ticketStatus === 'resolved' && 'Решен'}
                  </span>
                </div>
                <p className="support-ticket-preview">
                  {ticket.lastPreview || 'Нет сообщений'}
                </p>
                <small className="support-ticket-time">
                  {new Date(ticket.updatedAt).toLocaleString('ru-RU')}
                </small>
              </div>
            ))}
        </div>
      </aside>

      <section className="support-content">
        {!activeTicketId ? (
          <div className="support-empty">
            <p>Выберите тикет из списка слева</p>
          </div>
        ) : (
          <>
            <div className="support-header">
              {activeTicket && (
                <>
                  <div className="support-header-info">
                    <h3>{activeTicket.userName}</h3>
                    <p>{activeTicket.userEmail}</p>
                  </div>
                  {canSendMessages && (
                    <button
                      className="support-resolve-btn"
                      onClick={handleResolveTicket}
                      type="button"
                    >
                      Отметить решенным
                    </button>
                  )}
                </>
              )}
            </div>
            <div className="support-messages">
              <ChatHistory
                messages={messages}
                isLoading={isMessagesLoading}
                isSending={isSending}
                onSuggestionSelect={canSendMessages ? handleSendMessage : null}
                onRequestSupport={null}
                showOperatorButton={false}
              />
              {typingUsers[activeTicketId] && (
                <div className="typing-indicator">
                  {typingUsers[activeTicketId]} печатает...
                </div>
              )}
            </div>
            <div className="support-composer">
              <QuestionForm
                onSubmit={handleSendMessage}
                isLoading={isSending}
                disabled={!canSendMessages}
                placeholder={
                  canSendMessages
                    ? 'Напишите сообщение пользователю...'
                    : 'Тикет решен, отправка сообщений недоступна'
                }
              />
              {error && <div className="inline-error">{error}</div>}
            </div>
          </>
        )}
      </section>
    </div>
  );
};

export default SupportPage;

