const RAW = import.meta.env.VITE_STT_URL?.trim() || '';
const STT_BASE = RAW ? RAW.replace(/\/+$/, '') : '/stt';

export interface TranscribeResult {
  text: string;
}

export async function transcribe(audio: Blob): Promise<TranscribeResult> {
  const form = new FormData();
  const ext = audio.type.includes('webm')
    ? 'webm'
    : audio.type.includes('ogg')
      ? 'ogg'
      : audio.type.includes('mp4')
        ? 'mp4'
        : 'wav';
  form.append('audio', audio, `voice.${ext}`);

  const res = await fetch(`${STT_BASE}/transcribe`, {
    method: 'POST',
    body: form,
  });

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const message =
      (data && typeof data === 'object' && 'error' in (data as Record<string, unknown>) &&
        typeof (data as Record<string, unknown>).error === 'string'
        ? String((data as Record<string, unknown>).error)
        : `Ошибка распознавания (${res.status})`);
    throw new Error(message);
  }

  const text =
    (data && typeof data === 'object' && 'text' in (data as Record<string, unknown>)
      ? String((data as Record<string, unknown>).text ?? '')
      : '');

  return { text };
}
