import { request } from './client';
import type {
  Chat,
  ChatDetailResponse,
  ChatListResponse,
  SendMessageResponse,
  GeoLocation,
  AskGuestResponse,
} from '@/types';

export async function listChats(): Promise<Chat[]> {
  const res = await request<ChatListResponse>('/api/chats', { method: 'GET' });
  return res.chats || [];
}

export async function createChat(title?: string): Promise<Chat> {
  const res = await request<{ success: boolean; chat: Chat }>('/api/chats', {
    method: 'POST',
    body: { title: title || '' },
  });
  return res.chat;
}

export async function getChat(chatId: string): Promise<ChatDetailResponse> {
  return request<ChatDetailResponse>(`/api/chats/${chatId}`, { method: 'GET' });
}

export async function deleteChat(chatId: string): Promise<void> {
  await request(`/api/chats/${chatId}`, { method: 'DELETE' });
}

export async function sendMessage(
  chatId: string,
  content: string,
  location?: GeoLocation,
): Promise<SendMessageResponse> {
  const body: Record<string, unknown> = { content };
  if (location) body.location = location;
  return request<SendMessageResponse>(`/api/chats/${chatId}/messages`, {
    method: 'POST',
    body,
  });
}

export async function askGuest(question: string, location?: GeoLocation): Promise<AskGuestResponse> {
  const body: Record<string, unknown> = { question };
  if (location) body.location = location;
  return request<AskGuestResponse>('/api/ask', {
    method: 'POST',
    body,
    auth: false,
  });
}
