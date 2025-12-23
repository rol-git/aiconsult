import React from 'react';

const HistoryPage = ({ isVisible, chats, onSelect, onClose }) => {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="history-overlay">
      <div className="history-panel">
        <div className="history-header">
          <div>
            <p>История диалогов</p>
            <h3>Сохранённые чаты</h3>
          </div>
          <button className="ghost-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <div className="history-grid">
          {chats.length === 0 && (
            <div className="history-empty">
              <p>Чаты появятся после первого диалога</p>
            </div>
          )}
          {chats.map((chat) => (
            <button
              type="button"
              key={chat.id}
              className="history-card"
              onClick={() => {
                onSelect(chat.id);
                onClose();
              }}
            >
              <span className="history-topic">{chat.title || 'Пример'}</span>
              <p>{chat.lastPreview || 'Пример вопроса'}</p>
              <span className="history-date">
                {new Date(chat.updatedAt).toLocaleDateString('ru-RU', {
                  day: '2-digit',
                  month: 'long',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;

