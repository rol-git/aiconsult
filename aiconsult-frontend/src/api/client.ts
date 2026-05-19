const RAW_BASE = import.meta.env.VITE_API_URL?.trim() || '';
export const API_BASE: string = RAW_BASE.replace(/\/+$/, '');
const TOKEN_KEY = 'aic_token';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    void 0;
  }
}

export class HttpError extends Error {
  status: number;
  payload: unknown;
  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body' | 'headers'> {
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers = {}, auth = true, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...headers,
  };

  let payload: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    finalHeaders['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  if (auth) {
    const token = getToken();
    if (token) finalHeaders['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, { ...rest, headers: finalHeaders, body: payload });
  } catch (e) {
    throw new HttpError(0, 'Сеть недоступна. Проверьте подключение.', e);
  }

  let data: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    if (data && typeof data === 'object') {
      const obj = data as Record<string, unknown>;
      if (typeof obj.error === 'string') message = obj.error;
      else if (typeof obj.message === 'string') message = obj.message;
    }
    if (/connection refused|econnrefused|errno 61|сервис недоступен/i.test(message)) {
      message = 'Сервис ИИ-консультанта временно недоступен. Попробуйте через минуту.';
    }
    if (response.status === 401) setToken(null);
    throw new HttpError(response.status, message, data);
  }

  return data as T;
}
