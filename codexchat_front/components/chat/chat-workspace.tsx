"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import ThemeToggle from "@/app/components/theme-toggle";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import { getApiBaseUrl, getWebSocketUrl } from "@/lib/network-config";
import MessageMarkdown from "@/components/chat/message-markdown";
import type {
  AssistantDeltaEvent,
  AssistantDoneEvent,
  ChatErrorEvent,
  ChatMessage,
  ChatRole,
  ConversationBusyEvent,
} from "@/types/chat";

type ApiConversation = {
  id?: string;
  title?: string | null;
  updated_at?: string;
  updatedAt?: string;
  created_at?: string;
  createdAt?: string;
};

type ApiConversationMessage = {
  id?: string;
  role?: string;
  content?: string;
  created_at?: string;
  createdAt?: string;
};

type ConversationItem = {
  id: string;
  title: string;
  updatedAt: string | null;
};

type ConversationDetail = {
  messages: ChatMessage[];
};

type ChatEvent =
  | AssistantDeltaEvent
  | AssistantDoneEvent
  | ChatErrorEvent
  | ConversationBusyEvent
  | {
      type?: string;
      conversationId?: string;
      conversation_id?: string;
      [key: string]: unknown;
    };

const SHOULD_USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "1";

const MOCK_CONVERSATIONS: ConversationItem[] = [
  {
    id: "mock-1",
    title: "Draft deployment checklist",
    updatedAt: new Date(Date.now() - 1000 * 60 * 14).toISOString(),
  },
  {
    id: "mock-2",
    title: "Layout polish notes",
    updatedAt: new Date(Date.now() - 1000 * 60 * 95).toISOString(),
  },
];

function extractConversations(payload: unknown): ApiConversation[] {
  if (Array.isArray(payload)) {
    return payload as ApiConversation[];
  }

  if (payload && typeof payload === "object") {
    const container = payload as {
      conversations?: unknown;
      items?: unknown;
      data?: unknown;
    };

    if (Array.isArray(container.conversations)) {
      return container.conversations as ApiConversation[];
    }

    if (Array.isArray(container.items)) {
      return container.items as ApiConversation[];
    }

    if (Array.isArray(container.data)) {
      return container.data as ApiConversation[];
    }
  }

  return [];
}

function normalizeConversation(item: ApiConversation): ConversationItem | null {
  if (!item.id || typeof item.id !== "string") {
    return null;
  }

  return {
    id: item.id,
    title: item.title?.trim() || "Untitled chat",
    updatedAt: item.updated_at ?? item.updatedAt ?? item.created_at ?? item.createdAt ?? null,
  };
}

function isChatRole(value: string): value is ChatRole {
  return value === "user" || value === "assistant" || value === "system";
}

function normalizeMessage(item: ApiConversationMessage): ChatMessage | null {
  if (!item.id || typeof item.id !== "string") {
    return null;
  }

  const role = typeof item.role === "string" ? item.role : "assistant";
  if (!isChatRole(role)) {
    return null;
  }

  return {
    id: item.id,
    role,
    content: typeof item.content === "string" ? item.content : "",
    createdAt: item.created_at ?? item.createdAt ?? new Date().toISOString(),
  };
}

function extractConversationDetail(payload: unknown): ConversationDetail {
  if (!payload || typeof payload !== "object") {
    return { messages: [] };
  }

  const root = payload as {
    conversation?: {
      messages?: unknown;
    };
    messages?: unknown;
    data?: {
      messages?: unknown;
    };
  };

  const rawMessages =
    root.conversation?.messages ??
    root.messages ??
    root.data?.messages ??
    [];

  const messages = Array.isArray(rawMessages)
    ? rawMessages.map((item) => normalizeMessage(item as ApiConversationMessage)).filter((item): item is ChatMessage => Boolean(item))
    : [];

  return {
    messages,
  };
}

function extractCreatedConversation(payload: unknown): ConversationItem | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const root = payload as {
    conversation?: unknown;
    data?: {
      conversation?: unknown;
    };
  };

  const rawConversation = root.conversation ?? root.data?.conversation;
  if (!rawConversation || typeof rawConversation !== "object") {
    return null;
  }

  return normalizeConversation(rawConversation as ApiConversation);
}

function formatUpdatedAt(value: string | null): string {
  if (!value) {
    return "No activity";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "No activity";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatMessageTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function isLikelyNetworkFailure(error: unknown): boolean {
  if (error instanceof TypeError) {
    return true;
  }

  if (error instanceof Error) {
    return /network|failed to fetch|load failed|fetch/i.test(error.message);
  }

  return false;
}

function createClientMessageId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function parseEventPayload(raw: string): ChatEvent | null {
  try {
    const payload = JSON.parse(raw) as unknown;
    if (!payload || typeof payload !== "object") {
      return null;
    }
    return payload as ChatEvent;
  } catch {
    return null;
  }
}

function extractConversationId(event: ChatEvent): string | null {
  const direct = event.conversationId ?? event.conversation_id;
  if (typeof direct === "string" && direct.trim()) {
    return direct;
  }

  if ("details" in event && event.details && typeof event.details === "object") {
    const nested = event.details as { conversationId?: string; conversation_id?: string };
    if (typeof nested.conversationId === "string" && nested.conversationId.trim()) {
      return nested.conversationId;
    }
    if (typeof nested.conversation_id === "string" && nested.conversation_id.trim()) {
      return nested.conversation_id;
    }
  }

  return null;
}

function isRetryableSendErrorCode(code: string): boolean {
  return (
    code === "THREAD_BUSY" ||
    code === "CONVERSATION_BUSY" ||
    code === "VALIDATION_ERROR" ||
    code === "NOT_FOUND"
  );
}

export default function ChatWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const selectedFromQuery = searchParams.get("conversationId");

  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const [isLoading, setLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    selectedFromQuery,
  );

  const [messagesByConversationId, setMessagesByConversationId] = useState<Record<string, ChatMessage[]>>({});
  const [streamDraftByConversationId, setStreamDraftByConversationId] = useState<Record<string, string>>({});
  const [busyByConversationId, setBusyByConversationId] = useState<Record<string, boolean>>({});
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [composerValue, setComposerValue] = useState("");
  const [sendErrorByConversationId, setSendErrorByConversationId] = useState<Record<string, string | null>>({});
  const [isCreatingConversation, setCreatingConversation] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const wsResolution = useMemo(() => {
    try {
      return { url: getWebSocketUrl(), error: null as string | null };
    } catch (error) {
      const message = error instanceof Error ? error.message : "WebSocket URL is not configured.";
      return { url: "", error: message };
    }
  }, []);

  const selectedConversation =
    conversations.find((item) => item.id === selectedConversationId) ?? null;

  const selectedTimelineMessages = useMemo(() => {
    if (!selectedConversationId) {
      return [];
    }

    const persisted = messagesByConversationId[selectedConversationId] ?? [];
    const streaming = streamDraftByConversationId[selectedConversationId];
    if (!streaming) {
      return persisted;
    }

    return [
      ...persisted,
      {
        id: `${selectedConversationId}-streaming`,
        role: "assistant" as const,
        content: streaming,
        createdAt: new Date().toISOString(),
        pending: true,
      },
    ];
  }, [messagesByConversationId, selectedConversationId, streamDraftByConversationId]);

  const selectedConversationBusy = selectedConversationId
    ? Boolean(busyByConversationId[selectedConversationId])
    : false;
  const selectedSendError = selectedConversationId ? (sendErrorByConversationId[selectedConversationId] ?? null) : null;

  const loadConversations = useCallback(
    async (mode: "initial" | "refresh" = "initial") => {
      if (mode === "initial") {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      try {
        const response = await fetch(`${apiBaseUrl}/conversations`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const normalized = extractConversations(payload)
          .map(normalizeConversation)
          .filter((item): item is ConversationItem => Boolean(item));

        setConversations(normalized);
        setErrorMessage(null);
      } catch (error) {
        if (SHOULD_USE_MOCKS && isLikelyNetworkFailure(error)) {
          setConversations(MOCK_CONVERSATIONS);
          setErrorMessage(null);
        } else {
          setErrorMessage("Unable to load conversations right now.");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBaseUrl],
  );

  const loadConversationMessages = useCallback(
    async (conversationId: string) => {
      setTimelineLoading(true);
      setTimelineError(null);

      try {
        const response = await fetch(`${apiBaseUrl}/conversations/${conversationId}`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const detail = extractConversationDetail(payload);
        setMessagesByConversationId((previous) => ({
          ...previous,
          [conversationId]: detail.messages,
        }));
      } catch {
        setTimelineError("Unable to load messages for this conversation.");
      } finally {
        setTimelineLoading(false);
      }
    },
    [apiBaseUrl],
  );

  useEffect(() => {
    void loadConversations("initial");
  }, [loadConversations]);

  useEffect(() => {
    setSelectedConversationId(selectedFromQuery);
  }, [selectedFromQuery]);

  useEffect(() => {
    if (!selectedConversationId) {
      setTimelineError(null);
      return;
    }

    if (messagesByConversationId[selectedConversationId]) {
      setTimelineError(null);
      return;
    }

    void loadConversationMessages(selectedConversationId);
  }, [loadConversationMessages, messagesByConversationId, selectedConversationId]);

  useEffect(() => {
    if (!listRef.current) {
      return;
    }

    const saved = window.sessionStorage.getItem("chat_sidebar_scroll_top");
    if (!saved) {
      return;
    }

    const parsed = Number.parseInt(saved, 10);
    if (!Number.isNaN(parsed)) {
      listRef.current.scrollTop = parsed;
    }
  }, [conversations.length]);

  const onConversationListScroll = useCallback(() => {
    if (!listRef.current) {
      return;
    }
    window.sessionStorage.setItem("chat_sidebar_scroll_top", String(listRef.current.scrollTop));
  }, []);

  const onSelectConversation = useCallback(
    (conversationId: string) => {
      setSelectedConversationId(conversationId);
      setDrawerOpen(false);
      router.push(`/chat?conversationId=${encodeURIComponent(conversationId)}`);
    },
    [router],
  );

  const onNewChat = useCallback(() => {
    setSelectedConversationId(null);
    setDrawerOpen(false);
    router.push("/chat");
  }, [router]);

  const appendOptimisticUserMessage = useCallback((conversationId: string, content: string): string => {
    const optimisticId = createClientMessageId("user");
    setMessagesByConversationId((previous) => ({
      ...previous,
      [conversationId]: [
        ...(previous[conversationId] ?? []),
        {
          id: optimisticId,
          role: "user",
          content,
          createdAt: new Date().toISOString(),
          deliveryStatus: "sending",
        },
      ],
    }));
    return optimisticId;
  }, []);

  const markMessageAsFailed = useCallback((conversationId: string, messageId: string) => {
    setMessagesByConversationId((previous) => {
      const conversationMessages = previous[conversationId] ?? [];
      return {
        ...previous,
        [conversationId]: conversationMessages.map((message) => {
          if (message.id !== messageId) {
            return message;
          }
          return {
            ...message,
            deliveryStatus: "failed",
          };
        }),
      };
    });
  }, []);

  const markMessageAsSent = useCallback((conversationId: string, messageId: string) => {
    setMessagesByConversationId((previous) => {
      const conversationMessages = previous[conversationId] ?? [];
      return {
        ...previous,
        [conversationId]: conversationMessages.map((message) => {
          if (message.id !== messageId) {
            return message;
          }
          const nextMessage = { ...message };
          delete nextMessage.deliveryStatus;
          return nextMessage;
        }),
      };
    });
  }, []);

  const markLatestSendingMessageAsFailed = useCallback((conversationId: string) => {
    setMessagesByConversationId((previous) => {
      const conversationMessages = previous[conversationId] ?? [];
      let failedOne = false;
      const updated = [...conversationMessages];
      for (let index = updated.length - 1; index >= 0; index -= 1) {
        if (updated[index].role === "user" && updated[index].deliveryStatus === "sending") {
          updated[index] = {
            ...updated[index],
            deliveryStatus: "failed",
          };
          failedOne = true;
          break;
        }
      }

      if (!failedOne) {
        return previous;
      }

      return {
        ...previous,
        [conversationId]: updated,
      };
    });
  }, []);

  const ensureConversationForSend = useCallback(async (): Promise<string | null> => {
    if (selectedConversationId) {
      return selectedConversationId;
    }

    setCreatingConversation(true);
    try {
      const response = await fetch(`${apiBaseUrl}/conversations`, {
        method: "POST",
        credentials: "include",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`);
      }

      const payload = (await response.json()) as unknown;
      const createdConversation = extractCreatedConversation(payload);
      if (!createdConversation) {
        throw new Error("Missing conversation payload");
      }

      setConversations((previous) => {
        const withoutDuplicate = previous.filter((item) => item.id !== createdConversation.id);
        return [createdConversation, ...withoutDuplicate];
      });
      setSelectedConversationId(createdConversation.id);
      setSendErrorByConversationId((previous) => ({
        ...previous,
        [createdConversation.id]: null,
      }));
      router.push(`/chat?conversationId=${encodeURIComponent(createdConversation.id)}`);
      return createdConversation.id;
    } catch {
      setTimelineError("Unable to create a new conversation right now.");
      return null;
    } finally {
      setCreatingConversation(false);
    }
  }, [apiBaseUrl, router, selectedConversationId]);


  const applyAssistantDone = useCallback((conversationId: string, content: string | null) => {
    setBusyByConversationId((previous) => ({
      ...previous,
      [conversationId]: false,
    }));

    setStreamDraftByConversationId((previous) => {
      const draft = previous[conversationId] ?? "";
      const finalContent = (content ?? "").trim() ? content : draft;
      const rest = { ...previous };
      delete rest[conversationId];

      if (!finalContent || !finalContent.trim()) {
        return rest;
      }

      setMessagesByConversationId((messageState) => {
        const current = messageState[conversationId] ?? [];
        const lastMessage = current[current.length - 1];
        if (lastMessage && lastMessage.pending && lastMessage.role === "assistant") {
          const replaced = [...current];
          replaced[replaced.length - 1] = {
            ...lastMessage,
            content: finalContent,
            pending: false,
            createdAt: new Date().toISOString(),
          };

          return {
            ...messageState,
            [conversationId]: replaced,
          };
        }

        return {
          ...messageState,
          [conversationId]: [
            ...current,
            {
              id: createClientMessageId("assistant"),
              role: "assistant",
              content: finalContent,
              createdAt: new Date().toISOString(),
            },
          ],
        };
      });

      return rest;
    });
  }, []);

  const onWebSocketMessage = useCallback(
    (messageEvent: MessageEvent<string>) => {
      const event = parseEventPayload(messageEvent.data);
      if (!event || typeof event.type !== "string") {
        return;
      }

      const conversationId = extractConversationId(event) ?? selectedConversationId;
      if (!conversationId) {
        return;
      }

      if (event.type === "assistant_delta") {
        const deltaEvent = event as AssistantDeltaEvent;
        const delta = typeof deltaEvent.delta === "string"
          ? deltaEvent.delta
          : typeof deltaEvent.content === "string"
            ? deltaEvent.content
            : "";

        if (!delta) {
          return;
        }

        setBusyByConversationId((previous) => ({
          ...previous,
          [conversationId]: true,
        }));

        setStreamDraftByConversationId((previous) => ({
          ...previous,
          [conversationId]: `${previous[conversationId] ?? ""}${delta}`,
        }));
        return;
      }

      if (event.type === "assistant_done") {
        const doneEvent = event as AssistantDoneEvent;
        const doneContent =
          typeof doneEvent.content === "string"
            ? doneEvent.content
            : typeof doneEvent.message === "string"
              ? doneEvent.message
              : typeof doneEvent.text === "string"
                ? doneEvent.text
                : null;

        applyAssistantDone(conversationId, doneContent);
        return;
      }

      if (event.type === "conversation_busy" || event.type === "thread_busy") {
        const busyEvent = event as ConversationBusyEvent;
        setBusyByConversationId((previous) => ({
          ...previous,
          [conversationId]: busyEvent.busy ?? true,
        }));
        return;
      }

      if (event.type === "error") {
        const errorEvent = event as ChatErrorEvent;
        const code = (errorEvent.code ?? "").toUpperCase();
        const isBusyError = code === "THREAD_BUSY" || code === "CONVERSATION_BUSY";

        if (isBusyError) {
          setBusyByConversationId((previous) => ({
            ...previous,
            [conversationId]: true,
          }));
        }

        if (errorEvent.details?.busy === false) {
          setBusyByConversationId((previous) => ({
            ...previous,
            [conversationId]: false,
          }));
        }

        if (isRetryableSendErrorCode(code)) {
          markLatestSendingMessageAsFailed(conversationId);
          setSendErrorByConversationId((previous) => ({
            ...previous,
            [conversationId]: errorEvent.message ?? "Message failed to send. Retry when ready.",
          }));
        }
      }
    },
    [applyAssistantDone, markLatestSendingMessageAsFailed, selectedConversationId],
  );

  const {
    connectionState,
    reconnectAttempts,
    sendJsonMessage,
    retryNow,
  } = useChatWebSocket({
    url: wsResolution.url,
    enabled: wsResolution.error === null,
    onMessage: onWebSocketMessage,
    onOpen: () => {
      if (selectedConversationId) {
        sendJsonMessage({
          type: "resume",
          conversationId: selectedConversationId,
        });
      }
    },
  });

  const submitMessage = useCallback(
    async (rawContent: string): Promise<boolean> => {
      const trimmedContent = rawContent.trim();
      if (!trimmedContent) {
        return false;
      }

      const conversationId = await ensureConversationForSend();
      if (!conversationId) {
        return false;
      }

      setSendErrorByConversationId((previous) => ({
        ...previous,
        [conversationId]: null,
      }));

      const optimisticId = appendOptimisticUserMessage(conversationId, trimmedContent);
      const sent = sendJsonMessage({
        type: "send_message",
        conversationId,
        content: trimmedContent,
      });

      if (!sent) {
        markMessageAsFailed(conversationId, optimisticId);
        setSendErrorByConversationId((previous) => ({
          ...previous,
          [conversationId]: "Message failed to send. Reconnect and retry.",
        }));
        return false;
      }

      markMessageAsSent(conversationId, optimisticId);
      return true;
    },
    [appendOptimisticUserMessage, ensureConversationForSend, markMessageAsFailed, markMessageAsSent, sendJsonMessage],
  );

  const onComposerSubmit = useCallback(async () => {
    const sent = await submitMessage(composerValue);
    if (sent) {
      setComposerValue("");
    }
  }, [composerValue, submitMessage]);

  const onRetryFailedMessage = useCallback(async (messageId: string) => {
    const conversationId = selectedConversationId;
    if (!conversationId) {
      return;
    }

    const failedMessage = (messagesByConversationId[conversationId] ?? []).find((message) => message.id === messageId);
    if (!failedMessage || failedMessage.role !== "user") {
      return;
    }

    setMessagesByConversationId((previous) => ({
      ...previous,
      [conversationId]: (previous[conversationId] ?? []).map((message) =>
        message.id === messageId
          ? {
              ...message,
              deliveryStatus: "sending",
            }
          : message,
      ),
    }));

    const sent = sendJsonMessage({
      type: "send_message",
      conversationId,
      content: failedMessage.content.trim(),
    });

    if (!sent) {
      markMessageAsFailed(conversationId, messageId);
      setSendErrorByConversationId((previous) => ({
        ...previous,
        [conversationId]: "Message failed to send. Reconnect and retry.",
      }));
      return;
    }

    markMessageAsSent(conversationId, messageId);
    setSendErrorByConversationId((previous) => ({
      ...previous,
      [conversationId]: null,
    }));
  }, [markMessageAsFailed, markMessageAsSent, messagesByConversationId, selectedConversationId, sendJsonMessage]);

  const canSubmitComposer =
    composerValue.trim().length > 0 &&
    !selectedConversationBusy &&
    !isCreatingConversation &&
    connectionState === "connected" &&
    wsResolution.error === null;

  useEffect(() => {
    if (!selectedConversationId || connectionState !== "connected") {
      return;
    }

    sendJsonMessage({
      type: "resume",
      conversationId: selectedConversationId,
    });
  }, [connectionState, selectedConversationId, sendJsonMessage]);

  return (
    <div className="min-h-screen min-h-dvh bg-background text-foreground md:grid md:grid-cols-[320px_1fr]">
      <aside className="hidden border-r border-border bg-muted/40 md:flex md:min-h-screen md:min-h-dvh md:flex-col">
        <SidebarContent
          conversations={conversations}
          selectedConversationId={selectedConversationId}
          busyByConversationId={busyByConversationId}
          isLoading={isLoading}
          isRefreshing={isRefreshing}
          errorMessage={errorMessage}
          listRef={listRef}
          onConversationListScroll={onConversationListScroll}
          onSelectConversation={onSelectConversation}
          onNewChat={onNewChat}
          onRetry={() => void loadConversations("refresh")}
        />
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur md:hidden">
          <button
            type="button"
            aria-label="Open conversation sidebar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-lg"
            onClick={() => setDrawerOpen(true)}
          >
            ☰
          </button>
          <p className="text-sm font-semibold tracking-[0.14em] uppercase">CodexChat</p>
          <ThemeToggle />
        </header>

        {isDrawerOpen ? (
          <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
            <button
              type="button"
              aria-label="Close conversation sidebar"
              className="absolute inset-0 bg-black/50"
              onClick={() => setDrawerOpen(false)}
            />
            <aside className="relative z-10 h-full w-screen border-r border-border bg-background">
              <SidebarContent
                conversations={conversations}
                selectedConversationId={selectedConversationId}
                busyByConversationId={busyByConversationId}
                isLoading={isLoading}
                isRefreshing={isRefreshing}
                errorMessage={errorMessage}
                listRef={listRef}
                onConversationListScroll={onConversationListScroll}
                onSelectConversation={onSelectConversation}
                onNewChat={onNewChat}
                onRetry={() => void loadConversations("refresh")}
                mobile
                onClose={() => setDrawerOpen(false)}
              />
            </aside>
          </div>
        ) : null}

        <main className="mx-auto flex min-h-[calc(100vh-56px)] min-h-[calc(100dvh-56px)] w-full max-w-5xl flex-col px-4 py-6 sm:px-6 md:min-h-screen md:min-h-dvh md:py-8">
          <section className="rounded-2xl border border-border bg-muted/30 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-semibold tracking-[0.14em] uppercase text-muted-foreground">
                Conversation
              </p>
              <ConnectionBadge
                state={connectionState}
                reconnectAttempts={reconnectAttempts}
                hasConfigError={Boolean(wsResolution.error)}
                onRetry={retryNow}
              />
            </div>

            {selectedConversation ? (
              <>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
                    {selectedConversation.title}
                  </h1>
                  {selectedConversationBusy ? (
                    <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      Busy
                    </span>
                  ) : null}
                </div>

                {wsResolution.error ? (
                  <p className="mt-2 text-sm text-muted-foreground">{wsResolution.error}</p>
                ) : null}

                <MessageTimeline
                  isLoading={timelineLoading}
                  errorMessage={timelineError}
                  messages={selectedTimelineMessages}
                  selectedConversationId={selectedConversationId}
                  onRetryFailedMessage={onRetryFailedMessage}
                  onRetry={() => selectedConversationId ? void loadConversationMessages(selectedConversationId) : undefined}
                />
              </>
            ) : (
              <>
                <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">New chat</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Start a new conversation from here. Select an existing chat in the sidebar to resume it.
                </p>
              </>
            )}

            <ComposerPanel
              value={composerValue}
              setValue={setComposerValue}
              onSubmit={onComposerSubmit}
              disabled={!canSubmitComposer}
              isBusy={selectedConversationBusy}
              isCreatingConversation={isCreatingConversation}
              connectionState={connectionState}
              hasConfigError={Boolean(wsResolution.error)}
              sendError={selectedSendError}
            />
          </section>
        </main>
      </div>
    </div>
  );
}

type SidebarContentProps = {
  conversations: ConversationItem[];
  selectedConversationId: string | null;
  busyByConversationId: Record<string, boolean>;
  isLoading: boolean;
  isRefreshing: boolean;
  errorMessage: string | null;
  listRef: React.RefObject<HTMLDivElement | null>;
  onConversationListScroll: () => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
  onRetry: () => void;
  mobile?: boolean;
  onClose?: () => void;
};

function SidebarContent({
  conversations,
  selectedConversationId,
  busyByConversationId,
  isLoading,
  isRefreshing,
  errorMessage,
  listRef,
  onConversationListScroll,
  onSelectConversation,
  onNewChat,
  onRetry,
  mobile = false,
  onClose,
}: SidebarContentProps) {
  return (
    <div className="flex h-full min-h-0 flex-col p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <Link href="/chat" className="text-sm font-semibold tracking-[0.18em] uppercase">
          CodexChat
        </Link>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {mobile ? (
            <button
              type="button"
              aria-label="Close sidebar"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-base"
              onClick={onClose}
            >
              ✕
            </button>
          ) : null}
        </div>
      </div>

      <button
        type="button"
        className="mt-4 w-full rounded-lg border border-border bg-background px-3 py-2 text-left text-sm font-medium transition hover:bg-muted"
        onClick={onNewChat}
      >
        + New chat
      </button>

      <p className="mt-6 text-xs font-semibold tracking-[0.16em] uppercase text-muted-foreground">Recent</p>

      <div
        ref={listRef}
        onScroll={onConversationListScroll}
        className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1"
      >
        {isLoading ? (
          <ConversationListLoading />
        ) : null}

        {!isLoading && errorMessage ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm">
            <p className="text-muted-foreground">{errorMessage}</p>
            <button
              type="button"
              className="mt-3 rounded-md border border-border px-3 py-1.5 text-sm font-medium transition hover:bg-muted"
              onClick={onRetry}
            >
              Retry
            </button>
          </div>
        ) : null}

        {!isLoading && !errorMessage && conversations.length === 0 ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm text-muted-foreground">
            No conversations yet - start a new chat
          </div>
        ) : null}

        {!isLoading && !errorMessage && conversations.length > 0
          ? conversations.map((conversation) => {
              const isSelected = selectedConversationId === conversation.id;
              const isBusy = Boolean(busyByConversationId[conversation.id]);

              return (
                <button
                  key={conversation.id}
                  type="button"
                  className={`w-full rounded-lg border px-3 py-2 text-left transition ${
                    isSelected
                      ? "border-foreground bg-background"
                      : "border-border bg-background hover:bg-muted"
                  }`}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium">{conversation.title}</p>
                    {isBusy ? (
                      <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                        Busy
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{formatUpdatedAt(conversation.updatedAt)}</p>
                </button>
              );
            })
          : null}
      </div>

      <div className="mt-4 border-t border-border pt-4">
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/settings"
            className="rounded-md px-2 py-1 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground"
          >
            Settings
          </Link>
          <form method="post" action="/logout">
            <button
              type="submit"
              className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium transition hover:bg-muted"
            >
              Log out
            </button>
          </form>
        </div>
        {isRefreshing ? <p className="mt-2 text-xs text-muted-foreground">Refreshing…</p> : null}
      </div>
    </div>
  );
}

function ConversationListLoading() {
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-border bg-background p-3">
        <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
        <div className="mt-2 h-2.5 w-1/3 animate-pulse rounded bg-muted" />
      </div>
      <div className="rounded-lg border border-border bg-background p-3">
        <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
        <div className="mt-2 h-2.5 w-1/4 animate-pulse rounded bg-muted" />
      </div>
      <div className="rounded-lg border border-border bg-background p-3">
        <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
        <div className="mt-2 h-2.5 w-2/5 animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}

type ConnectionBadgeProps = {
  state: "connecting" | "connected" | "reconnecting" | "disconnected";
  reconnectAttempts: number;
  hasConfigError: boolean;
  onRetry: () => void;
};

function ConnectionBadge({ state, reconnectAttempts, hasConfigError, onRetry }: ConnectionBadgeProps) {
  if (hasConfigError) {
    return (
      <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">
        WebSocket unavailable
      </span>
    );
  }

  if (state === "connected") {
    return null;
  }

  if (state === "disconnected") {
    return (
      <div className="flex items-center gap-2">
        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">
          Disconnected
        </span>
        <button
          type="button"
          className="rounded-md border border-border bg-background px-2 py-0.5 text-xs font-medium transition hover:bg-muted"
          onClick={onRetry}
        >
          Retry
        </button>
      </div>
    );
  }

  const label = state === "reconnecting" ? `Reconnecting… (${reconnectAttempts})` : "Connecting…";

  return (
    <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">
      {label}
    </span>
  );
}

type MessageTimelineProps = {
  isLoading: boolean;
  errorMessage: string | null;
  messages: ChatMessage[];
  selectedConversationId: string | null;
  onRetryFailedMessage: (messageId: string) => Promise<void>;
  onRetry: () => void;
};

function MessageTimeline({
  isLoading,
  errorMessage,
  messages,
  selectedConversationId,
  onRetryFailedMessage,
  onRetry,
}: MessageTimelineProps) {
  if (isLoading) {
    return (
      <div className="mt-5 space-y-3">
        <MessageSkeleton />
        <MessageSkeleton />
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="mt-5 rounded-xl border border-border bg-background p-4 text-sm">
        <p className="text-muted-foreground">{errorMessage}</p>
        <button
          type="button"
          className="mt-3 rounded-md border border-border px-3 py-1.5 font-medium transition hover:bg-muted"
          onClick={onRetry}
        >
          Retry
        </button>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="mt-5 rounded-xl border border-border bg-background p-4 text-sm text-muted-foreground">
        No messages yet.
      </div>
    );
  }

  return (
    <div className="mt-5 space-y-4">
      {messages.map((message) => (
        <MessageRow
          key={message.id}
          message={message}
          onRetry={
            selectedConversationId && message.deliveryStatus === "failed"
              ? () => {
                  void onRetryFailedMessage(message.id);
                }
              : undefined
          }
        />
      ))}
    </div>
  );
}

function MessageSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-background p-4">
      <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
      <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
      <div className="mt-2 h-3 w-5/6 animate-pulse rounded bg-muted" />
    </div>
  );
}

type ComposerPanelProps = {
  value: string;
  setValue: (value: string) => void;
  onSubmit: () => Promise<void>;
  disabled: boolean;
  isBusy: boolean;
  isCreatingConversation: boolean;
  connectionState: "connecting" | "connected" | "reconnecting" | "disconnected";
  hasConfigError: boolean;
  sendError: string | null;
};

function ComposerPanel({
  value,
  setValue,
  onSubmit,
  disabled,
  isBusy,
  isCreatingConversation,
  connectionState,
  hasConfigError,
  sendError,
}: ComposerPanelProps) {
  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey) {
        return;
      }

      event.preventDefault();
      if (!disabled) {
        void onSubmit();
      }
    },
    [disabled, onSubmit],
  );

  let helperText = "Enter to send. Shift+Enter for newline.";
  if (isCreatingConversation) {
    helperText = "Creating conversation…";
  } else if (isBusy) {
    helperText = "This conversation is busy.";
  } else if (hasConfigError || connectionState !== "connected") {
    helperText = "WebSocket is not connected.";
  }

  return (
    <div className="mt-5 border-t border-border pt-4">
      <label htmlFor="chat-composer" className="sr-only">
        Message
      </label>
      <textarea
        id="chat-composer"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        rows={3}
        placeholder="Send a message…"
        className="w-full resize-y rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/15"
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">{sendError ?? helperText}</p>
        <button
          type="button"
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled}
          onClick={() => void onSubmit()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

function roleLabel(role: ChatRole): string {
  if (role === "assistant") {
    return "Assistant";
  }

  if (role === "system") {
    return "System";
  }

  return "You";
}

function MessageRow({ message, onRetry }: { message: ChatMessage; onRetry?: () => void }) {
  const sharedClassName = "rounded-xl border p-4";

  const styleClassName =
    message.role === "assistant"
      ? "border-border bg-background"
      : message.role === "system"
        ? "border-border bg-muted/60"
        : "border-border bg-muted/20";

  return (
    <article className={`${sharedClassName} ${styleClassName}`}>
      <header className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold tracking-[0.12em] uppercase text-muted-foreground">
          {roleLabel(message.role)}
          {message.pending ? " (streaming)" : message.deliveryStatus === "sending" ? " (sending)" : ""}
        </p>
        <p className="text-xs text-muted-foreground">{formatMessageTimestamp(message.createdAt)}</p>
      </header>
      <div className="text-sm leading-6">
        <MessageMarkdown content={message.content} />
      </div>
      {message.deliveryStatus === "failed" ? (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2">
          <p className="text-xs text-muted-foreground">Failed to send</p>
          <button
            type="button"
            className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:bg-muted"
            onClick={onRetry}
          >
            Retry
          </button>
        </div>
      ) : null}
    </article>
  );
}
