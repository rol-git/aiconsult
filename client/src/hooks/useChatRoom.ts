import { useEffect, useState } from 'react';
import type { Socket } from 'socket.io-client';
import type { ChatMessage } from '@/types';

interface Result {
  liveMessages: ChatMessage[];
  typingUsers: string[];
  resolvedSignal: number;
  reset: () => void;
}

interface Options {
  socket: Socket | null;
  chatId: string | null;
}

export function useChatRoom({ socket, chatId }: Options): Result {
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [resolvedSignal, setResolvedSignal] = useState(0);

  useEffect(() => {
    setLiveMessages([]);
    setTypingUsers([]);
  }, [chatId]);

  useEffect(() => {
    if (!socket || !chatId) return;

    socket.emit('join_chat', { chatId });

    const onMessage = (data: ChatMessage & { chatId?: string }) => {
      if (data.chatId && data.chatId !== chatId) return;
      setLiveMessages((prev) =>
        prev.some((m) => m.id === data.id) ? prev : [...prev, data],
      );
    };

    const onTyping = (data: { chatId: string; userName: string; isTyping: boolean }) => {
      if (data.chatId !== chatId) return;
      setTypingUsers((prev) => {
        const set = new Set(prev);
        if (data.isTyping) set.add(data.userName);
        else set.delete(data.userName);
        return Array.from(set);
      });
    };

    const onResolved = (data: { chatId: string }) => {
      if (data.chatId === chatId) setResolvedSignal((n) => n + 1);
    };

    socket.on('new_message', onMessage);
    socket.on('user_typing', onTyping);
    socket.on('ticket_resolved', onResolved);

    return () => {
      socket.emit('leave_chat', { chatId });
      socket.off('new_message', onMessage);
      socket.off('user_typing', onTyping);
      socket.off('ticket_resolved', onResolved);
    };
  }, [socket, chatId]);

  const reset = () => {
    setLiveMessages([]);
    setTypingUsers([]);
  };

  return { liveMessages, typingUsers, resolvedSignal, reset };
}
