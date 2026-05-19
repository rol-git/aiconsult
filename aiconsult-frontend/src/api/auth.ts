import { request, setToken } from './client';
import type { AuthResponse, User } from '@/types';

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
  if (res.token) setToken(res.token);
  return res;
}

export async function register(
  email: string,
  password: string,
  name: string,
): Promise<AuthResponse> {
  const res = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: { email, password, name },
    auth: false,
  });
  if (res.token) setToken(res.token);
  return res;
}

export async function me(): Promise<User> {
  const res = await request<{ success: boolean; user: User }>('/api/auth/me', {
    method: 'GET',
  });
  return res.user;
}

export function logout(): void {
  setToken(null);
}
