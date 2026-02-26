import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatHistory.css';

const formatTime = (value) => {
  try {
    return new Date(value).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
};

function ChatHistory({ messages, isLoading, isSending, onSuggestionSelect, onRequestSupport, showOperatorButton }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, isLoading, isSending]);

  if (!messages.length && !isLoading) {
    return (
      <div className="chat-history empty">
        <div className="empty-state">
          <div className="empty-icon">✦</div>
          <h3>Новый диалог</h3>
          <p>Ваши сообщения сохраняются и не пропадают при перезагрузке</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-history" ref={containerRef}>
      {messages.map((message, index) => {
        const isUser = message.role === 'user';
        const isSupport = message.role === 'support';
        const isSystem = message.role === 'system';
        const isAssistant = message.role === 'assistant';
        const isLastMessage = index === messages.length - 1;
        
        let displayName = 'Консультант';
        if (isUser) displayName = 'Вы';
        else if (isSupport) displayName = message.senderName || 'Оператор';
        else if (isSystem) displayName = 'Система';
        
        const hasSuggestions = Array.isArray(message.suggestedQuestions) && message.suggestedQuestions.length > 0;
        const showOperatorBtn = showOperatorButton && onRequestSupport && isLastMessage && isAssistant;
        
        return (
          <div key={message.id} className={`bubble ${message.role}`}>
            <div className="bubble-meta">
              <span>{displayName}</span>
              <time>{formatTime(message.createdAt)}</time>
            </div>
            <div className="bubble-body">
              {isAssistant ? (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              ) : (
                <p>{message.content}</p>
              )}
            </div>
            {(hasSuggestions || showOperatorBtn) && (
              <div className="bubble-foot">
                <div className="bubble-suggestions">
                  <span>Попробуйте спросить:</span>
                  <div className="suggestions-list">
                    {hasSuggestions && message.suggestedQuestions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => onSuggestionSelect?.(question)}
                      >
                        {question}
                      </button>
                    ))}
                    {showOperatorBtn && (
                      <button
                        key="operator-request"
                        type="button"
                        className="operator-request-button"
                        onClick={onRequestSupport}
                      >
                        👤 Позвать оператора
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {(isLoading || isSending) && (
        <div className="bubble assistant pending">
          <div className="bubble-meta">
            <span>Консультант</span>
            <time>...</time>
          </div>
          <div className="typing">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatHistory;
