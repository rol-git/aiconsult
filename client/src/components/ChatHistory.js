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

function ChatHistory({ messages, isLoading, isSending, onSuggestionSelect }) {
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
      {messages.map((message) => (
        <div key={message.id} className={`bubble ${message.role}`}>
          <div className="bubble-meta">
            <span>{message.role === 'user' ? 'Вы' : 'Консультант'}</span>
            <time>{formatTime(message.createdAt)}</time>
          </div>
          <div className="bubble-body">
            {message.role === 'assistant' ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : (
              <p>{message.content}</p>
            )}
          </div>
          {message.role === 'assistant' &&
            Array.isArray(message.suggestedQuestions) &&
            message.suggestedQuestions.length > 0 && (
              <div className="bubble-foot">
                <div className="bubble-suggestions">
                  <span>Попробуйте спросить:</span>
                  <div className="suggestions-list">
                    {message.suggestedQuestions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => onSuggestionSelect?.(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
        </div>
      ))}

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
