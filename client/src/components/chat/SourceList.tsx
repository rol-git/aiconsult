import { memo, useState } from 'react';
import type { MessageSource } from '@/types';
import styles from './SourceList.module.css';

interface Props {
  sources?: MessageSource[];
}

function SourceListImpl({ sources }: Props) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.toggle}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>Источники ({sources.length})</span>
        <span aria-hidden="true" className={open ? styles.arrowOpen : styles.arrow}>▾</span>
      </button>
      {open && (
        <ol className={styles.list}>
          {sources.map((src, i) => {
            const title =
              src.title || src.document || (typeof src.url === 'string' ? src.url : `Источник ${i + 1}`);
            return (
              <li key={i} className={styles.item}>
                <div className={styles.title}>
                  {src.url ? (
                    <a href={String(src.url)} target="_blank" rel="noreferrer noopener">
                      {title}
                    </a>
                  ) : (
                    title
                  )}
                  {src.page !== undefined && src.page !== null && (
                    <span className="muted small"> · стр. {String(src.page)}</span>
                  )}
                </div>
                {src.snippet && <div className={styles.snippet}>{src.snippet}</div>}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

export const SourceList = memo(SourceListImpl);
