import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
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
      } catch (err) {
        setError(err.message);
      } finally {
        setIsMessagesLoading(false);
      }
    };

    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChatId, token]);

  const handleSendMessage = async (content) => {
    if (!content.trim() || !activeChatId) {
      setError('Выберите диалог или создайте новый, чтобы отправить сообщение.');
      return;
    }

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
          />
        </div>
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

