import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type FormEvent } from 'react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { transcribe } from '@/api/stt';
import styles from './MessageInput.module.css';

interface Props {
  onSend: (text: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  onTyping?: (isTyping: boolean) => void;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function MessageInput({ onSend, disabled, placeholder, onTyping }: Props) {
  const [value, setValue] = useState('');
  const [sttBusy, setSttBusy] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const typingTimer = useRef<number | null>(null);
  const typingActive = useRef(false);
  const recorder = useVoiceRecorder({ maxSeconds: 60 });

  const autoresize = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 180) + 'px';
  }, []);

  useEffect(() => {
    autoresize();
  }, [value, autoresize]);

  const fireTyping = useCallback(
    (active: boolean) => {
      if (!onTyping) return;
      if (active && !typingActive.current) {
        typingActive.current = true;
        onTyping(true);
      } else if (!active && typingActive.current) {
        typingActive.current = false;
        onTyping(false);
      }
    },
    [onTyping],
  );

  const submit = useCallback(async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue('');
    if (typingTimer.current) {
      window.clearTimeout(typingTimer.current);
      typingTimer.current = null;
    }
    fireTyping(false);
    try {
      await onSend(trimmed);
    } catch {
      setValue(trimmed);
    }
  }, [value, disabled, onSend, fireTyping]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    if (onTyping) {
      fireTyping(true);
      if (typingTimer.current) window.clearTimeout(typingTimer.current);
      typingTimer.current = window.setTimeout(() => fireTyping(false), 2000);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void submit();
  };

  const handleMicClick = useCallback(async () => {
    setVoiceError(null);
    if (recorder.state === 'recording') {
      recorder.stop();
      return;
    }
    const blob = await recorder.start();
    if (!blob) return;
    setSttBusy(true);
    try {
      const res = await transcribe(blob);
      const text = (res.text || '').trim();
      if (text) {
        setValue((prev) => (prev ? `${prev.trimEnd()} ${text}` : text));
        if (ref.current) ref.current.focus();
      } else {
        setVoiceError('Речь не распознана. Попробуйте ещё раз.');
      }
    } catch (e) {
      setVoiceError(e instanceof Error ? e.message : 'Ошибка распознавания');
    } finally {
      setSttBusy(false);
    }
  }, [recorder]);

  const handleMicCancel = useCallback(() => {
    recorder.cancel();
    setSttBusy(false);
  }, [recorder]);

  const isRecording = recorder.state === 'recording';
  const isRequesting = recorder.state === 'requesting';
  const micError = voiceError || recorder.error;
  const hasText = value.trim().length > 0;

  return (
    <div className={styles.wrap}>
      <div className={styles.inner}>
        {micError && (
          <div className={styles.voiceError} role="alert">
            {micError}
          </div>
        )}

        {isRecording && (
          <div className={styles.recordingBar} role="status">
            <span className={styles.recDot} aria-hidden="true" />
            <span>Идёт запись... {formatTime(recorder.elapsed)}</span>
            <button type="button" className={styles.recCancel} onClick={handleMicCancel}>
              Отмена
            </button>
          </div>
        )}

        <form
          className={`${styles.form} ${focused ? styles.formFocused : ''} ${isRecording ? styles.formRecording : ''}`}
          onSubmit={handleSubmit}
        >
          <textarea
            ref={ref}
            className={styles.input}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={
              isRecording
                ? 'Идёт запись голоса...'
                : sttBusy
                  ? 'Распознавание речи...'
                  : placeholder || 'Опишите ситуацию или задайте вопрос...'
            }
            disabled={disabled || isRecording || sttBusy}
            rows={1}
            aria-label="Сообщение"
          />

          <div className={styles.actions}>
            {recorder.supported && (
              <button
                type="button"
                className={`${styles.iconBtn} ${styles.mic} ${isRecording ? styles.micActive : ''}`}
                onClick={handleMicClick}
                disabled={disabled || sttBusy || isRequesting}
                aria-label={isRecording ? 'Остановить запись' : 'Записать голосовое сообщение'}
                title={isRecording ? 'Остановить и распознать' : 'Записать голосом'}
              >
                {sttBusy || isRequesting ? (
                  <span className="spinner" />
                ) : isRecording ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <rect x="6" y="6" width="12" height="12" rx="2" />
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
            )}

            <button
              type="submit"
              className={`${styles.iconBtn} ${styles.send}`}
              disabled={disabled || !hasText || isRecording || sttBusy}
              aria-label="Отправить"
              title="Отправить (Enter)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 19V5" />
                <path d="m5 12 7-7 7 7" />
              </svg>
            </button>
          </div>
        </form>

        <div className={styles.hint}>
          Нажмите <kbd>Enter</kbd> для отправки, <kbd>Shift</kbd>+<kbd>Enter</kbd> — новая строка
        </div>
      </div>
    </div>
  );
}

export default MessageInput;
