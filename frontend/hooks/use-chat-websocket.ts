"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionState } from "@/types/chat";

type UseChatWebSocketOptions = {
  url: string;
  enabled: boolean;
  maxReconnectAttempts?: number;
  maxReconnectDelayMs?: number;
  onMessage: (event: MessageEvent<string>) => void;
  onOpen?: () => void;
  onError?: () => void;
};

type UseChatWebSocketResult = {
  connectionState: ConnectionState;
  reconnectAttempts: number;
  sendJsonMessage: (payload: unknown) => boolean;
  retryNow: () => void;
};

const DEFAULT_MAX_ATTEMPTS = 7;
const BASE_RETRY_DELAY_MS = 500;
const DEFAULT_MAX_RETRY_DELAY_MS = 8000;

export function useChatWebSocket({
  url,
  enabled,
  maxReconnectAttempts = DEFAULT_MAX_ATTEMPTS,
  maxReconnectDelayMs = DEFAULT_MAX_RETRY_DELAY_MS,
  onMessage,
  onOpen,
  onError,
}: UseChatWebSocketOptions): UseChatWebSocketResult {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const attemptsRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onErrorRef = useRef(onError);

  const [connectionState, setConnectionState] = useState<ConnectionState>(
    enabled ? "connecting" : "disconnected",
  );
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closeSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onmessage = null;
      socketRef.current.onerror = null;
      socketRef.current.onclose = null;
      socketRef.current.close();
      socketRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(
    (connect: () => void) => {
      if (!enabled || !shouldReconnectRef.current) {
        return;
      }

      if (attemptsRef.current >= maxReconnectAttempts) {
        setConnectionState("disconnected");
        return;
      }

      attemptsRef.current += 1;
      setReconnectAttempts(attemptsRef.current);
      setConnectionState("reconnecting");

      const exponentialDelay = BASE_RETRY_DELAY_MS * 2 ** (attemptsRef.current - 1);
      const delay = Math.min(exponentialDelay, maxReconnectDelayMs);
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    },
    [enabled, maxReconnectAttempts, maxReconnectDelayMs],
  );

  const connectRef = useRef<() => void>(() => {});

  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onErrorRef.current = onError;
  }, [onError, onMessage, onOpen]);

  useEffect(() => {
    shouldReconnectRef.current = true;

    if (!enabled) {
      return () => {
        shouldReconnectRef.current = false;
      };
    }

    const connect = () => {
      clearReconnectTimer();
      closeSocket();

      try {
        setConnectionState(attemptsRef.current === 0 ? "connecting" : "reconnecting");
        const socket = new WebSocket(url);
        socketRef.current = socket;

        socket.onopen = () => {
          attemptsRef.current = 0;
          setReconnectAttempts(0);
          setConnectionState("connected");
          onOpenRef.current?.();
        };

        socket.onmessage = (event) => {
          onMessageRef.current(event as MessageEvent<string>);
        };

        socket.onerror = () => {
          onErrorRef.current?.();
        };

        socket.onclose = () => {
          if (!shouldReconnectRef.current) {
            setConnectionState("disconnected");
            return;
          }
          scheduleReconnect(connect);
        };
      } catch {
        scheduleReconnect(connect);
      }
    };

    connectRef.current = connect;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimer();
      closeSocket();
    };
  }, [clearReconnectTimer, closeSocket, enabled, scheduleReconnect, url]);

  const sendJsonMessage = useCallback((payload: unknown): boolean => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    socket.send(JSON.stringify(payload));
    return true;
  }, []);

  const retryNow = useCallback(() => {
    if (!enabled || !shouldReconnectRef.current) {
      return;
    }

    attemptsRef.current = 0;
    setReconnectAttempts(0);
    clearReconnectTimer();
    connectRef.current();
  }, [clearReconnectTimer, enabled]);

  return {
    connectionState: enabled ? connectionState : "disconnected",
    reconnectAttempts,
    sendJsonMessage,
    retryNow,
  };
}
