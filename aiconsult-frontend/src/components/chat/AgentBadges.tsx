import { memo } from 'react';
import type { AgentType } from '@/types';

const AGENT_LABELS: Record<AgentType, string> = {
  payouts: 'Выплаты',
  actions: 'Действия',
  law: 'Право',
  docs: 'Документы',
  smalltalk: 'Поддержка',
  geo: 'Карта',
};

interface Props {
  types?: AgentType[];
  labels?: string[];
}

function AgentBadgesImpl({ types, labels }: Props) {
  const items: string[] = labels && labels.length
    ? labels
    : (types || []).map((t) => AGENT_LABELS[t] || t);

  if (!items.length) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
      {items.map((label, i) => (
        <span key={`${label}-${i}`} className="badge badge-primary">
          {label}
        </span>
      ))}
    </div>
  );
}

export const AgentBadges = memo(AgentBadgesImpl);
