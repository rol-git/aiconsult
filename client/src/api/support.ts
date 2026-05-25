import { request } from './client';
import type {
  ChatMessage,
  SupportTicket,
  SupportTicketsResponse,
  OnlineOperatorsResponse,
} from '@/types';

export interface TicketThread {
  ticket: SupportTicket;
  messages: ChatMessage[];
}

/** Полный тред тикета для оператора (тикет + сообщения). Авто-назначает тикет на оператора. */
export async function getTicketThread(chatId: string): Promise<TicketThread> {
  const res = await request<{ success: boolean; ticket: SupportTicket; messages: ChatMessage[] }>(
    `/api/support/tickets/${chatId}`,
    { method: 'GET' },
  );
  return { ticket: res.ticket, messages: res.messages || [] };
}

export async function listTickets(): Promise<SupportTicket[]> {
  const res = await request<SupportTicketsResponse>('/api/support/tickets', { method: 'GET' });
  return res.tickets || [];
}

export async function getTicket(chatId: string): Promise<SupportTicket> {
  const res = await request<{ success: boolean; ticket: SupportTicket }>(
    `/api/support/tickets/${chatId}`,
    { method: 'GET' },
  );
  return res.ticket;
}

export async function resolveTicket(chatId: string): Promise<void> {
  await request(`/api/support/tickets/${chatId}/resolve`, { method: 'POST' });
}

export async function getMyTicket(chatId: string): Promise<SupportTicket | null> {
  try {
    const res = await request<{ success: boolean; ticket: SupportTicket | null }>(
      `/api/support/tickets/my/${chatId}`,
      { method: 'GET' },
    );
    return res.ticket || null;
  } catch {
    return null;
  }
}

export async function requestSupport(chatId: string): Promise<SupportTicket> {
  const res = await request<{ success: boolean; ticket: SupportTicket }>(
    '/api/support/request',
    { method: 'POST', body: { chatId } },
  );
  return res.ticket;
}

export async function getOnlineOperators(): Promise<OnlineOperatorsResponse> {
  return request<OnlineOperatorsResponse>('/api/support/online-operators', {
    method: 'GET',
    auth: false,
  });
}
