import React, { useState } from 'react';
import './QuestionForm.css';

function QuestionForm({ onSubmit, isLoading, disabled }) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    if (disabled || isLoading || !question.trim()) {
      return;
    }
    onSubmit(question.trim());
    setQuestion('');
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  return (
    <form className="question-form" onSubmit={handleSubmit}>
      <div className="input-row">
        <textarea
          rows="1"
          placeholder="Задайте вопрос..."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading || disabled}
        />
        <button
          type="submit"
          className="send-button"
          disabled={isLoading || disabled || !question.trim()}
          title="Отправить"
        >
          {isLoading ? (
            <span className="send-spinner" />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          )}
        </button>
      </div>
    </form>
  );
}

export default QuestionForm;

