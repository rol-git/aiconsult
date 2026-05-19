export type UserRole = 'user' | 'support';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  createdAt: string;
}

export interface AuthResponse {
  success: boolean;
  user: User;
  token: string;
}

export type AgentType =
  | 'payouts'
  | 'actions'
  | 'law'
  | 'docs'
  | 'smalltalk'
  | 'geo';

export interface MessageSource {
  title?: string;
  document?: string;
  page?: number | string;
  snippet?: string;
  url?: string;
  [key: string]: unknown;
}

export type MessageRole = 'user' | 'assistant' | 'support' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  agentTypes?: AgentType[];
  agentLabels?: string[];
  sources?: MessageSource[];
  notes?: string;
  suggestedQuestions?: string[];
  suggestOperator?: boolean;
  senderName?: string;
}

export interface Chat {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  lastPreview?: string;
}

export interface ChatListResponse {
  success: boolean;
  chats: Chat[];
}

export interface ChatDetailResponse {
  success: boolean;
  chat: Chat;
  messages: ChatMessage[];
}

export interface SendMessageResponse {
  success: boolean;
  chat: Chat;
  messages: ChatMessage[];
}

export interface FAQItem {
  id?: string | number;
  question: string;
  answer: string;
  category?: string;
}

export interface FAQResponse {
  success: boolean;
  items: FAQItem[];
}

export type SupportTicketStatus = 'pending' | 'assigned' | 'resolved';

export interface SupportTicket {
  id: string;
  chatId: string;
  status: SupportTicketStatus;
  createdAt: string;
  assignedAt?: string | null;
  resolvedAt?: string | null;
  assignedOperatorId?: string | null;
  userName?: string;
  preview?: string;
  title?: string;
}

export interface SupportTicketsResponse {
  success: boolean;
  tickets: SupportTicket[];
}

export interface OnlineOperatorsResponse {
  success: boolean;
  count: number;
  hasOperators?: boolean;
}

export interface GeoLocation {
  lat: number;
  lon: number;
  accuracy?: number;
  source?: string;
}

export interface AskGuestResponse {
  success: boolean;
  answer: string;
  agentTypes?: AgentType[];
  agentLabels?: string[];
  sources?: MessageSource[];
  suggestedQuestions?: string[];
  notes?: string;
}

export interface ApiError {
  success: false;
  error?: string;
  message?: string;
}

export interface ServerInfo {
  success?: boolean;
  model?: string;
  mode?: string;
  region?: string;
  version?: string;
  [key: string]: unknown;
}
