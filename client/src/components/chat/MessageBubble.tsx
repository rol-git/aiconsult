import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '@/types';
import { AgentBadges } from './AgentBadges';
import { SourceList } from './SourceList';
import styles from './MessageBubble.module.css';

interface Props {
  message: ChatMessage;
  onSuggested?: (q: string) => void;
}

const ROLE_LABEL: Record<string, string> = {
  user: 'Вы',
  assistant: 'ИИ-консультант',
  support: 'Оператор поддержки',
  system: 'Система',
};

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function MessageBubbleImpl({ message, onSuggested }: Props) {
  const role = message.role;
  const isUser = role === 'user';
  const isSystem = role === 'system';

  const wrapClass = `${styles.row} ${
    isUser ? styles.right : isSystem ? styles.center : styles.left
  }`;
  const bubbleClass = `${styles.bubble} ${
    isUser
      ? styles.bubbleUser
      : role === 'support'
        ? styles.bubbleSupport
        : isSystem
          ? styles.bubbleSystem
          : styles.bubbleAssistant
  }`;

  return (
    <div className={wrapClass}>
      <div className={bubbleClass}>
        {!isSystem && (
          <div className={styles.meta}>
            <span className={styles.author}>
              {message.senderName || ROLE_LABEL[role] || role}
            </span>
            <span className={styles.time}>{formatTime(message.createdAt)}</span>
          </div>
        )}

        {role === 'assistant' && (
          <AgentBadges types={message.agentTypes} labels={message.agentLabels} />
        )}

        <div className={styles.content}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown>
        </div>

        {role === 'assistant' && <SourceList sources={message.sources} />}

        {role === 'assistant' && message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
          <div className={styles.suggested}>
            <div className={styles.suggestedTitle}>Похожие вопросы:</div>
            <div className={styles.suggestedList}>
              {message.suggestedQuestions.map((q, i) => (
                <button
                  type="button"
                  key={`${q}-${i}`}
                  className={styles.suggestedItem}
                  onClick={() => onSuggested?.(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {role === 'assistant' && message.notes && (
          <div className={styles.notes}>{message.notes}</div>
        )}
      </div>
    </div>
  );
}

export const MessageBubble = memo(MessageBubbleImpl);
