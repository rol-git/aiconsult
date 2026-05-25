import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useSocket } from '@/contexts/SocketContext';
import {
  askGuest,
  createChat,
  getChat,
  sendMessage,
} from '@/api/chats';
import { getMyTicket, requestSupport } from '@/api/support';
import { HttpError, getToken } from '@/api/client';
import { useGeo } from '@/hooks/useGeo';
import { useChatList } from '@/hooks/useChatList';
import { useChatRoom } from '@/hooks/useChatRoom';
import type { Chat, ChatMessage } from '@/types';
import MessageInput from '@/components/chat/MessageInput';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import styles from './ChatPage.module.css';

const GUEST_WELCOME: ChatMessage = {
  id: 'welcome-guest',
  role: 'system',
  content:
    'Здравствуйте! Я ИИ-консультант по чрезвычайным ситуациям. Опишите ситуацию или задайте вопрос — я подскажу, как действовать. Для сохранения истории — войдите в аккаунт.',
  createdAt: new Date(0).toISOString(),
};

const AUTH_WELCOME: ChatMessage = {
  id: 'welcome-auth',
  role: 'system',
  content:
    'Здравствуйте! Опишите вашу ситуацию подробно. Я подберу подходящего эксперта и подскажу следующие шаги.',
  createdAt: new Date(0).toISOString(),
};

function makeTempId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ChatPage() {
  const { user } = useAuth();
  const { socket, lastError: socketError, clearError: clearSocketError } = useSocket();
  const navigate = useNavigate();
  const params = useParams<{ chatId?: string }>();
  const [search, setSearch] = useSearchParams();
  const geo = useGeo();

  const chatId = params.chatId ?? null;
  const list = useChatList(Boolean(user));
  const room = useChatRoom({ socket, chatId });

  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [storedMessages, setStoredMessages] = useState<ChatMessage[]>(
    user ? [AUTH_WELCOME] : [GUEST_WELCOME],
  );
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [shareGeo, setShareGeo] = useState(false);
  const [ticketStatus, setTicketStatus] = useState<string | null>(null);
  const [supportLoading, setSupportLoading] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);
  const initialQuestionSent = useRef(false);

  useEffect(() => {
    if (!user) {
      setStoredMessages([GUEST_WELCOME]);
      setCurrentChat(null);
      setTicketStatus(null);
      return;
    }
    if (!chatId) {
      setStoredMessages([AUTH_WELCOME]);
      setCurrentChat(null);
      setTicketStatus(null);
      return;
    }

    let alive = true;
    setError(null);

    getChat(chatId)
      .then((res) => {
        if (!alive) return;
        setCurrentChat(res.chat);
        setStoredMessages(res.messages.length ? res.messages : [AUTH_WELCOME]);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        if (err instanceof HttpError && err.status === 404) {
          navigate('/chat', { replace: true });
        } else {
          setError('Не удалось загрузить диалог');
        }
      });

    void getMyTicket(chatId).then((t) => {
      if (alive && t) setTicketStatus(t.status);
    });

    return () => {
      alive = false;
    };
  }, [chatId, user, navigate]);

  useEffect(() => {
    if (room.resolvedSignal > 0) setTicketStatus('resolved');
  }, [room.resolvedSignal]);

  const messages = useMemo(() => {
    const ids = new Set(storedMessages.map((m) => m.id));
    const fresh = room.liveMessages.filter((m) => !ids.has(m.id));
    return [...storedMessages, ...fresh];
  }, [storedMessages, room.liveMessages]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, room.typingUsers]);

  const handleCreateChat = useCallback(async (): Promise<string | null> => {
    if (!user) return null;
    try {
      const chat = await createChat();
      list.prepend(chat);
      navigate(`/chat/${chat.id}`);
      return chat.id;
    } catch {
      setError('Не удалось создать диалог');
      return null;
    }
  }, [user, navigate, list]);

  const handleSendGuest = useCallback(
    async (text: string, locationData?: ReturnType<typeof useGeo>['location']) => {
      const userMsg: ChatMessage = {
        id: makeTempId('u'),
        role: 'user',
        content: text,
        createdAt: new Date().toISOString(),
      };
      setStoredMessages((prev) => [...prev, userMsg]);
      setSending(true);
      try {
        const res = await askGuest(text, locationData ?? undefined);
        const aiMsg: ChatMessage = {
          id: makeTempId('a'),
          role: 'assistant',
          content: res.answer || '',
          createdAt: new Date().toISOString(),
          agentTypes: res.agentTypes,
          agentLabels: res.agentLabels,
          sources: res.sources,
          suggestedQuestions: res.suggestedQuestions,
          notes: res.notes,
        };
        setStoredMessages((prev) => [...prev, aiMsg]);
      } catch (err: unknown) {
        setError(err instanceof HttpError ? err.message : 'Не удалось получить ответ');
      } finally {
        setSending(false);
      }
    },
    [],
  );

  const handleSendAuth = useCallback(
    async (text: string, locationData?: ReturnType<typeof useGeo>['location']) => {
      let id = chatId;
      if (!id) {
        const created = await handleCreateChat();
        if (!created) return;
        id = created;
      }

      const tempMsg: ChatMessage = {
        id: makeTempId('u'),
        role: 'user',
        content: text,
        createdAt: new Date().toISOString(),
      };
      setStoredMessages((prev) => [
        ...prev.filter((m) => m.id !== AUTH_WELCOME.id),
        tempMsg,
      ]);
      setSending(true);

      try {
        const res = await sendMessage(id, text, locationData ?? undefined);
        setCurrentChat(res.chat);
        list.upsert(res.chat);
        setStoredMessages((prev) => [
          ...prev.filter((m) => m.id !== tempMsg.id),
          ...res.messages,
        ]);
      } catch (err: unknown) {
        setError(err instanceof HttpError ? err.message : 'Не удалось отправить');
        setStoredMessages((prev) => prev.filter((m) => m.id !== tempMsg.id));
      } finally {
        setSending(false);
      }
    },
    [chatId, handleCreateChat, list],
  );

  const handleSend = useCallback(
    async (text: string) => {
      setError(null);
      const loc = shareGeo ? geo.location || (await geo.request()) : null;
      if (user) await handleSendAuth(text, loc ?? undefined);
      else await handleSendGuest(text, loc ?? undefined);
    },
    [user, shareGeo, geo, handleSendAuth, handleSendGuest],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await list.remove(id);
        if (chatId === id) navigate('/chat');
      } catch {
        setError('Не удалось удалить диалог');
      }
    },
    [chatId, list, navigate],
  );

  const handleTyping = useCallback(
    (isTyping: boolean) => {
      if (!socket || !chatId) return;
      const tok = getToken();
      if (!tok) return;
      socket.emit('typing', { chatId, token: tok, isTyping });
    },
    [socket, chatId],
  );

  const handleRequestOperator = useCallback(async () => {
    if (!chatId) return;
    setSupportLoading(true);
    try {
      const ticket = await requestSupport(chatId);
      setTicketStatus(ticket.status);
    } catch (err: unknown) {
      setError(err instanceof HttpError ? err.message : 'Не удалось запросить оператора');
    } finally {
      setSupportLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    const q = search.get('q');
    if (!q || initialQuestionSent.current) return;
    initialQuestionSent.current = true;
    setSearch({}, { replace: true });
    void handleSend(q);
  }, [search, setSearch, handleSend]);

  const headerTitle = useMemo(() => {
    if (currentChat?.title) return currentChat.title;
    if (chatId) return 'Диалог';
    return user ? 'Новый диалог' : 'Гостевая консультация';
  }, [currentChat, chatId, user]);

  const operatorAvailable =
    Boolean(user) && Boolean(chatId) &&
    (!ticketStatus || ticketStatus === 'resolved') &&
    messages.some((m) => m.role === 'assistant' && m.suggestOperator);

  return (
    <div className={styles.shell}>
      {user && (
        <ChatSidebar
          chats={list.chats}
          currentId={chatId ?? undefined}
          onSelect={(id) => navigate(`/chat/${id}`)}
          onCreate={() => void handleCreateChat()}
          onDelete={handleDelete}
          loading={list.loading}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
      )}

      <div className={styles.main}>
        <header className={styles.head}>
          {user && (
            <button
              type="button"
              className={styles.sidebarToggle}
              onClick={() => setSidebarOpen(true)}
              aria-label="Открыть список диалогов"
            >
              ☰
            </button>
          )}
          <div className={styles.headInfo}>
            <h2 className={styles.headTitle}>{headerTitle}</h2>
            {ticketStatus && (
              <span
                className={`badge ${
                  ticketStatus === 'resolved'
                    ? 'badge-success'
                    : ticketStatus === 'assigned'
                      ? 'badge-warning'
                      : 'badge-primary'
                }`}
              >
                {ticketStatus === 'pending' && 'Запрошен оператор'}
                {ticketStatus === 'assigned' && 'Оператор подключён'}
                {ticketStatus === 'resolved' && 'Решено'}
              </span>
            )}
          </div>
          {user && (
            <label className={styles.geoToggle}>
              <input
                type="checkbox"
                checked={shareGeo}
                onChange={(e) => setShareGeo(e.target.checked)}
              />
              <span>Геопозиция</span>
            </label>
          )}
        </header>

        <div ref={listRef} className={styles.list}>
          <div className={styles.listInner}>
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} onSuggested={handleSend} />
            ))}
            {room.typingUsers.length > 0 && (
              <div className={`${styles.typing} muted small`}>
                {room.typingUsers.join(', ')} печатает...
              </div>
            )}
            {sending && (
              <div className={styles.thinking}>
                <span className="spinner" />
                <span className="muted small">ИИ-консультант готовит ответ...</span>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className={styles.errorRow}>
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          </div>
        )}

        {socketError && user && (
          <div className={styles.errorRow}>
            <div className={`alert alert-error ${styles.socketAlert}`} role="status">
              <span>Связь с сервером прервана: {socketError}</span>
              <button
                type="button"
                className={styles.socketAlertDismiss}
                onClick={clearSocketError}
                aria-label="Скрыть"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {operatorAvailable && (
          <div className={styles.supportBanner}>
            <span>Вопрос требует личного участия?</span>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => void handleRequestOperator()}
              disabled={supportLoading}
            >
              {supportLoading ? <span className="spinner" /> : 'Запросить оператора'}
            </button>
          </div>
        )}

        <MessageInput
          onSend={handleSend}
          disabled={sending}
          onTyping={user && chatId ? handleTyping : undefined}
          placeholder={
            user
              ? 'Опишите ситуацию или задайте вопрос...'
              : 'Задайте вопрос (история не сохраняется)...'
          }
        />
      </div>
    </div>
  );
}

export default ChatPage;
