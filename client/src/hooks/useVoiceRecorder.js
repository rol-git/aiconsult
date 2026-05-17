import { useCallback, useRef, useState } from 'react';

import { API_BASE_URL } from '../services/api';

const TRANSCRIBE_URL = `${API_BASE_URL}/api/voice/transcribe`;

function pickMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/ogg;codecs=opus',
    'audio/webm',
    'audio/mp4',
  ];
  if (typeof MediaRecorder === 'undefined') return null;
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || null;
}

export function useVoiceRecorder({ onTranscribed, onError } = {}) {
  const [state, setState] = useState('idle');
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const cancelledRef = useRef(false);

  const releaseStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const start = useCallback(async () => {
    if (state !== 'idle') return;

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      onError?.('Браузер не поддерживает запись звука');
      return;
    }

    const mimeType = pickMimeType();
    if (!mimeType) {
      onError?.('Браузер не поддерживает MediaRecorder');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      cancelledRef.current = false;

      const recorder = new MediaRecorder(stream, { mimeType });

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const wasCancelled = cancelledRef.current;
        releaseStream();

        if (wasCancelled) {
          chunksRef.current = [];
          setState('idle');
          return;
        }

        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];

        if (blob.size === 0) {
          setState('idle');
          onError?.('Ничего не записалось');
          return;
        }

        setState('processing');
        try {
          const formData = new FormData();
          const ext = mimeType.includes('webm') ? 'webm' : mimeType.includes('ogg') ? 'ogg' : 'm4a';
          formData.append('audio', blob, `voice.${ext}`);

          const response = await fetch(TRANSCRIBE_URL, {
            method: 'POST',
            body: formData,
          });

          let payload = null;
          try {
            payload = await response.json();
          } catch {
            payload = null;
          }

          if (!response.ok) {
            throw new Error(payload?.error || `Ошибка сервера ${response.status}`);
          }

          const text = (payload?.text || '').trim();
          if (!text) {
            onError?.('Не удалось распознать речь');
          } else {
            onTranscribed?.(text);
          }
        } catch (err) {
          onError?.(err?.message || 'Ошибка распознавания');
        } finally {
          setState('idle');
        }
      };

      recorder.onerror = (event) => {
        onError?.(event?.error?.message || 'Ошибка записи');
        releaseStream();
        chunksRef.current = [];
        setState('idle');
      };

      recorder.start();
      recorderRef.current = recorder;
      setState('recording');
    } catch (err) {
      releaseStream();
      const message = err?.name === 'NotAllowedError'
        ? 'Доступ к микрофону запрещён'
        : err?.message || 'Не удалось включить микрофон';
      onError?.(message);
      setState('idle');
    }
  }, [state, onTranscribed, onError, releaseStream]);

  const stop = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      cancelledRef.current = false;
      recorderRef.current.stop();
    }
  }, []);

  const cancel = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      cancelledRef.current = true;
      recorderRef.current.stop();
    } else {
      releaseStream();
      chunksRef.current = [];
      setState('idle');
    }
  }, [releaseStream]);

  return { state, start, stop, cancel };
}
