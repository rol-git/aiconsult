import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './AnswerDisplay.css';

const MD_COMPONENTS = {
  a: ({ node, children, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};
const MD_PLUGINS = [remarkGfm];

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
          <ReactMarkdown remarkPlugins={MD_PLUGINS} components={MD_COMPONENTS}>
            {answer}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  return null;
}

export default AnswerDisplay;

