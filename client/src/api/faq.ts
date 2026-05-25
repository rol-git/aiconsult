import { request } from './client';
import type { FAQItem, FAQResponse } from '@/types';

export async function listFAQ(): Promise<FAQItem[]> {
  const res = await request<FAQResponse>('/api/faq', { method: 'GET', auth: false });
  return res.items || [];
}
