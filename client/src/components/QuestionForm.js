import React, { useCallback, useEffect, useRef, useState } from 'react';

import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import './QuestionForm.css';

function QuestionForm({ onSubmit, isLoading, disabled, placeholder }) {
  const [question, setQuestion] = useState('');
  const [voiceError, setVoiceError] = useState('');
  const errorTimerRef = useRef(null);

  const submitText = useCallback(
    (text) => {
      const trimmed = (text || '').trim();
      if (!trimmed || isLoading || disabled) return;
      onSubmit(trimmed);
      setQuestion('');
    },
    [onSubmit, isLoading, disabled]
  );

  const showVoiceError = useCallback((message) => {
    setVoiceError(message);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => setVoiceError(''), 4000);
  }, []);

  const handleTranscribed = useCallback(
    (text) => {
      setVoiceError('');
      submitText(text);
    },
    [submitText]
  );

  const { state: voiceState, start: startVoice, stop: stopVoice } = useVoiceRecorder({
    onTranscribed: handleTranscribed,
    onError: showVoiceError,
  });

  useEffect(() => () => {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    submitText(question);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitText(question);
    }
  };

  const handleMicClick = () => {
    if (voiceState === 'idle') startVoice();
    else if (voiceState === 'recording') stopVoice();
  };

  const inputsLocked = isLoading || disabled || voiceState !== 'idle';
  const micDisabled = isLoading || disabled || voiceState === 'processing';

  const micTitle =
    voiceState === 'recording' ? 'Остановить запись' :
    voiceState === 'processing' ? 'Распознаём…' :
    'Голосовой ввод';

  return (
    <form className="question-form" onSubmit={handleSubmit}>
      <div className="input-row">
        <textarea
          rows="1"
          placeholder={placeholder || "Задайте вопрос или нажмите микрофон…"}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={inputsLocked}
        />
        <button
          type="button"
          className={`mic-button mic-${voiceState}`}
          onClick={handleMicClick}
          disabled={micDisabled}
          title={micTitle}
          aria-label={micTitle}
        >
          {voiceState === 'processing' ? (
            <span className="send-spinner" />
          ) : voiceState === 'recording' ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <rect x="6" y="6" width="12" height="12" rx="1.5" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>
        <button
          type="submit"
          className="send-button"
          disabled={isLoading || disabled || !question.trim() || voiceState !== 'idle'}
          title="Отправить"
        >
          {isLoading ? (
            <span className="send-spinner" />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
      {voiceError && <div className="voice-error" role="alert">{voiceError}</div>}
    </form>
  );
}

export default QuestionForm;
