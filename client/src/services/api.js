const API_BASE_URL = process.env.REACT_APP_SERVER_URL || 'http://localhost:5000';

const defaultHeaders = {
  'Content-Type': 'application/json',
};

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = { ...defaultHeaders };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      payload?.error ||
      payload?.message ||
      payload?.msg ||
      `Произошла ошибка при запросе к серверу (код ${response.status})`;
    throw new Error(message);
  }

  return payload;
}

export { API_BASE_URL };

