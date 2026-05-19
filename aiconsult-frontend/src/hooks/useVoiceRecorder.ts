import { useCallback, useEffect, useRef, useState } from 'react';

export type RecorderState = 'idle' | 'requesting' | 'recording' | 'processing' | 'error';

function pickMimeType(): string | undefined {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4',
  ];
  if (typeof window === 'undefined' || typeof MediaRecorder === 'undefined') return undefined;
  for (const t of candidates) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return undefined;
}

interface Options {
  maxSeconds?: number;
}

export function useVoiceRecorder(opts: Options = {}) {
  const { maxSeconds = 60 } = opts;
  const [state, setState] = useState<RecorderState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const startedAt = useRef(0);
  const resolveRef = useRef<((blob: Blob | null) => void) | null>(null);

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== 'undefined' &&
    typeof MediaRecorder !== 'undefined';

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    recorderRef.current = null;
    chunksRef.current = [];
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  const start = useCallback(async (): Promise<Blob | null> => {
    if (!supported) {
      setError('Запись звука не поддерживается в этом браузере');
      setState('error');
      return null;
    }
    setError(null);
    setState('requesting');

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Нет доступа к микрофону';
      setError(msg);
      setState('error');
      return null;
    }

    streamRef.current = stream;
    const mimeType = pickMimeType();
    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    } catch {
      cleanup();
      setError('Не удалось инициализировать запись');
      setState('error');
      return null;
    }
    recorderRef.current = recorder;
    chunksRef.current = [];

    recorder.addEventListener('dataavailable', (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    });

    const finished = new Promise<Blob | null>((resolve) => {
      resolveRef.current = resolve;
    });

    recorder.addEventListener('stop', () => {
      const blob = chunksRef.current.length
        ? new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        : null;
      cleanup();
      setState('idle');
      setElapsed(0);
      const r = resolveRef.current;
      resolveRef.current = null;
      r?.(blob);
    });

    recorder.start();
    startedAt.current = Date.now();
    setState('recording');
    setElapsed(0);
    timerRef.current = window.setInterval(() => {
      const sec = Math.floor((Date.now() - startedAt.current) / 1000);
      setElapsed(sec);
      if (sec >= maxSeconds && recorderRef.current?.state === 'recording') {
        recorderRef.current.stop();
      }
    }, 250);

    return finished;
  }, [supported, maxSeconds, cleanup]);

  const stop = useCallback(() => {
    const r = recorderRef.current;
    if (r && r.state === 'recording') {
      setState('processing');
      r.stop();
    }
  }, []);

  const cancel = useCallback(() => {
    chunksRef.current = [];
    const r = recorderRef.current;
    if (r && r.state === 'recording') {
      r.stop();
    }
    cleanup();
    setState('idle');
    setElapsed(0);
    const res = resolveRef.current;
    resolveRef.current = null;
    res?.(null);
  }, [cleanup]);

  return { state, error, elapsed, start, stop, cancel, supported };
}
