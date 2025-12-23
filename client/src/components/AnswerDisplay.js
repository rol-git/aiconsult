import React from 'react';
import ReactMarkdown from 'react-markdown';
import './AnswerDisplay.css';

function AnswerDisplay({ answer, isLoading, error }) {
  if (isLoading) {
    return (
      <div className="answer-display loading">
        <div className="loader"></div>
        <p className="loading-text">Обработка вашего запроса...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="answer-display error">
        <div className="error-icon">⚠️</div>
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (answer) {
    return (
      <div className="answer-display">
        <div className="answer-header">
          <div className="answer-icon">💬</div>
          <h3>Ответ консультанта:</h3>
        </div>
        <div className="answer-content markdown-content">
          <ReactMarkdown>{answer}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return null;
}

export default AnswerDisplay;

