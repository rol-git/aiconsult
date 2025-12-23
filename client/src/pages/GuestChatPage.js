import React, { useState } from 'react';
import ChatHistory from '../components/ChatHistory';
import QuestionForm from '../components/QuestionForm';
import { apiRequest } from '../services/api';
import FaqPage from './FaqPage';

const createMessage = (role, content, extra = {}) => ({
  id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role,
  content,
  createdAt: new Date().toISOString(),
  ...extra,
});

const GuestChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [faqVisible, setFaqVisible] = useState(false);

  const handleSubmit = async (content) => {
    if (!content.trim() || isSending) {
      return;
    }

    const userMessage = createMessage('user', content.trim());
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setError('');

    try {
      const data = await apiRequest('/api/ask', {
        method: 'POST',
        body: { question: content.trim() },
      });

      const assistantMessage = createMessage(
        'assistant',
        data.answer || 'Не удалось получить ответ от консультанта.',
        {
          agentLabels: data.agentLabels || [],
          agentTypes: data.agentTypes || [],
          sources: data.sources || [],
          notes: data.notes || null,
          suggestedQuestions: data.suggestedQuestions || [],
        }
      );
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message || 'Не удалось получить ответ.');
      const assistantMessage = createMessage(
        'assistant',
        '❌ Произошла ошибка. Попробуйте отправить вопрос ещё раз.'
      );
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="workspace">
      <aside className="workspace__sidebar workspace__sidebar--guest">
        <p className="guest-hint">Войдите, чтобы сохранять историю диалогов и переключаться между чатами</p>
        <div className="workspace__sidebar-fab workspace__sidebar-fab--center">
          <button
            className="fab-button fab-button--faq fab-button--pulse"
            type="button"
            onClick={() => setFaqVisible(true)}
            title="Частые вопросы"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 8a5 5 0 0 1 9.5 2c0 3-5 4-5 4"/>
              <line x1="12" y1="20" x2="12.01" y2="20"/>
            </svg>
          </button>
        </div>
      </aside>

      <section className="workspace__content">
        <div className="workspace__messages">
          <ChatHistory
            messages={messages}
            isLoading={false}
            isSending={isSending}
            onSuggestionSelect={handleSubmit}
          />
        </div>
        <div className="workspace__composer">
          <QuestionForm onSubmit={handleSubmit} isLoading={isSending} disabled={false} />
          {error && <div className="inline-error">{error}</div>}
        </div>
      </section>

      <FaqPage
        isVisible={faqVisible}
        onClose={() => setFaqVisible(false)}
        onAsk={(question) => handleSubmit(question)}
      />
    </div>
  );
};

export default GuestChatPage;

