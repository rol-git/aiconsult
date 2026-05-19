import { useCallback, useEffect, useState } from 'react';
import * as chatsApi from '@/api/chats';
import type { Chat } from '@/types';

interface Result {
  chats: Chat[];
  loading: boolean;
  reload: () => Promise<void>;
  upsert: (chat: Chat) => void;
  remove: (id: string) => Promise<void>;
  prepend: (chat: Chat) => void;
}

export function useChatList(enabled: boolean): Result {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      const list = await chatsApi.listChats();
      setChats(list);
    } catch {
      setChats([]);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const upsert = useCallback((chat: Chat) => {
    setChats((prev) => {
      const i = prev.findIndex((c) => c.id === chat.id);
      if (i === -1) return [chat, ...prev];
      const next = [...prev];
      next[i] = chat;
      return next;
    });
  }, []);

  const prepend = useCallback((chat: Chat) => {
    setChats((prev) => [chat, ...prev.filter((c) => c.id !== chat.id)]);
  }, []);

  const remove = useCallback(async (id: string) => {
    await chatsApi.deleteChat(id);
    setChats((prev) => prev.filter((c) => c.id !== id));
  }, []);

  return { chats, loading, reload, upsert, remove, prepend };
}
