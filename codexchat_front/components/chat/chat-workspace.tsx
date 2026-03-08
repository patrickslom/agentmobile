"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  LogOut,
  Menu,
  PanelLeftClose,
  Paperclip,
  Search,
  SendHorizontal,
  Settings,
  SquarePen,
  X,
} from "lucide-react";
import WinkingLogo from "@/app/components/winking-logo";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import { getApiBaseUrl, getWebSocketUrl } from "@/lib/network-config";
import MessageMarkdown from "@/components/chat/message-markdown";
import type {
  AssistantDeltaEvent,
  AssistantDoneEvent,
  ChatErrorEvent,
  ChatMessage,
  ChatMessageFile,
  ChatRole,
  ConversationBusyEvent,
  MessageCreatedEvent,
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
  files?: unknown;
  client_message_id?: string | null;
  author_user_id?: string | null;
  author_display_name?: string | null;
  author_profile_picture_url?: string | null;
  is_current_user_author?: boolean | null;
};

type ApiMessageFile = {
  id?: string;
  original_name?: string;
  originalName?: string;
  storage_path?: string;
  storagePath?: string;
  download_path?: string;
  downloadPath?: string;
  mime_type?: string;
  mimeType?: string;
  size_bytes?: number;
  sizeBytes?: number;
};

type ConversationItem = {
  id: string;
  title: string;
  updatedAt: string | null;
};

type ConversationDetail = {
  messages: ChatMessage[];
};

type UploadedFileResponse = {
  id?: string;
  original_name?: string;
  originalName?: string;
  storage_path?: string;
  storagePath?: string;
  download_path?: string;
  downloadPath?: string;
  mime_type?: string;
  mimeType?: string;
  size_bytes?: number;
  sizeBytes?: number;
};

type AttachmentDraft = {
  id: string;
  file: File;
};

const DEFAULT_UPLOAD_LIMIT_MB = 15;
const ATTACHMENT_NAME_BASE_MAX_CHARS = 15;
const PREVIEWABLE_IMAGE_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
]);

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

function normalizeMessageFile(item: ApiMessageFile): ChatMessageFile | null {
  if (!item.id || typeof item.id !== "string") {
    return null;
  }

  const originalName = item.original_name ?? item.originalName;
  const storagePath = item.storage_path ?? item.storagePath;
  const downloadPath = item.download_path ?? item.downloadPath;

  if (
    typeof originalName !== "string" ||
    typeof storagePath !== "string" ||
    typeof downloadPath !== "string"
  ) {
    return null;
  }

  return {
    id: item.id,
    originalName,
    storagePath,
    downloadPath,
    mimeType:
      typeof item.mime_type === "string"
        ? item.mime_type
        : typeof item.mimeType === "string"
          ? item.mimeType
          : undefined,
    sizeBytes:
      typeof item.size_bytes === "number"
        ? item.size_bytes
        : typeof item.sizeBytes === "number"
          ? item.sizeBytes
          : undefined,
  };
}

function normalizeStringField(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }

  return normalized;
}

function normalizeBooleanField(value: unknown): boolean | undefined {
  if (value === true) {
    return true;
  }
  if (value === false) {
    return false;
  }

  return undefined;
}

function normalizeAuthorDisplayName(value: unknown): string {
  const normalized = normalizeStringField(value);
  if (!normalized) {
    return "Former User";
  }
  if (normalized.toLowerCase() === "you") {
    return "YOU";
  }
  return normalized;
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
    clientMessageId: normalizeStringField(item.client_message_id),
    authorUserId: normalizeStringField(item.author_user_id),
    authorDisplayName: normalizeAuthorDisplayName(item.author_display_name),
    authorProfilePictureUrl: normalizeStringField(item.author_profile_picture_url),
    isCurrentUserAuthor: normalizeBooleanField(item.is_current_user_author),
    createdAt: item.created_at ?? item.createdAt ?? new Date().toISOString(),
    files: Array.isArray(item.files)
      ? item.files
          .map((fileItem) => normalizeMessageFile(fileItem as ApiMessageFile))
          .filter((fileItem): fileItem is ChatMessageFile => Boolean(fileItem))
      : [],
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

function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "Unknown size";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kib = bytes / 1024;
  if (kib < 1024) {
    return `${kib.toFixed(1)} KB`;
  }

  const mib = kib / 1024;
  if (mib < 1024) {
    return `${mib.toFixed(1)} MB`;
  }

  return `${(mib / 1024).toFixed(1)} GB`;
}

function formatAttachmentName(filename: string): string {
  const trimmed = filename.trim();
  if (!trimmed) {
    return "file";
  }

  const lastDot = trimmed.lastIndexOf(".");
  const hasExtension = lastDot > 0 && lastDot < trimmed.length - 1;
  const baseName = hasExtension ? trimmed.slice(0, lastDot) : trimmed;
  const extension = hasExtension ? trimmed.slice(lastDot + 1) : "";

  if (baseName.length <= ATTACHMENT_NAME_BASE_MAX_CHARS) {
    return trimmed;
  }

  const truncatedBase = baseName.slice(0, ATTACHMENT_NAME_BASE_MAX_CHARS);
  return extension ? `${truncatedBase}...${extension}` : `${truncatedBase}...`;
}

function isPreviewableImage(file: ChatMessageFile): boolean {
  if (!file.mimeType) {
    return false;
  }
  return PREVIEWABLE_IMAGE_MIME_TYPES.has(file.mimeType.toLowerCase());
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

function isAuthFailureStatus(status: number): boolean {
  return status === 401 || status === 403;
}

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const match = document.cookie.match(/(?:^|;\s*)codexchat_csrf=([^;]+)/);
  if (!match?.[1]) {
    return null;
  }

  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

function withCsrfHeader(headers?: HeadersInit): HeadersInit | undefined {
  const token = readCsrfToken();
  if (!token) {
    return headers;
  }

  const next = new Headers(headers);
  next.set("x-csrf-token", token);
  return next;
}

function createClientMessageId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function parseIntroQuotes(markdown: string): string[] {
  return markdown
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => Boolean(line) && !line.startsWith("#"))
    .map((line) => {
      if (line.startsWith("- ")) {
        return line.slice(2).trim();
      }
      const numbered = line.match(/^\d+\.\s+(.*)$/);
      if (numbered?.[1]) {
        return numbered[1].trim();
      }
      return line;
    })
    .filter((line) => Boolean(line));
}

function pickRandomQuote(quotes: string[]): string {
  if (quotes.length === 0) {
    return "What are we building today?";
  }
  const index = Math.floor(Math.random() * quotes.length);
  return quotes[index];
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
    code === "NOT_FOUND" ||
    code === "THREAD_RESUME_FAILED"
  );
}

function mergeMessagesById(messages: ChatMessage[]): ChatMessage[] {
  const merged = new Map<string, ChatMessage>();

  for (const message of messages) {
    const existing = merged.get(message.id);
    merged.set(message.id, existing ? { ...existing, ...message } : message);
  }

  return Array.from(merged.values()).sort(
    (left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime(),
  );
}

function upsertMessage(messages: ChatMessage[], message: ChatMessage): ChatMessage[] {
  const existingIndex = messages.findIndex((entry) => entry.id === message.id);
  if (existingIndex === -1) {
    return mergeMessagesById([...messages, message]);
  }

  const next = [...messages];
  next[existingIndex] = {
    ...next[existingIndex],
    ...message,
  };
  return mergeMessagesById(next);
}

export default function ChatWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const selectedFromQuery = searchParams.get("conversationId");

  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoading, setLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [conversationSearchQuery, setConversationSearchQuery] = useState("");
  const [debouncedConversationSearchQuery, setDebouncedConversationSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ConversationItem[]>([]);
  const [isSearchLoading, setSearchLoading] = useState(false);
  const [searchErrorMessage, setSearchErrorMessage] = useState<string | null>(null);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    selectedFromQuery,
  );

  const [messagesByConversationId, setMessagesByConversationId] = useState<Record<string, ChatMessage[]>>({});
  const [streamDraftByConversationId, setStreamDraftByConversationId] = useState<Record<string, string>>({});
  const [busyByConversationId, setBusyByConversationId] = useState<Record<string, boolean>>({});
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [composerValue, setComposerValue] = useState("");
  const [attachmentDrafts, setAttachmentDrafts] = useState<AttachmentDraft[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [isUploadingAttachments, setUploadingAttachments] = useState(false);
  const [uploadLimitMb, setUploadLimitMb] = useState(DEFAULT_UPLOAD_LIMIT_MB);
  const [sendErrorByConversationId, setSendErrorByConversationId] = useState<Record<string, string | null>>({});
  const [isCreatingConversation, setCreatingConversation] = useState(false);
  const [composerBottomOffset, setComposerBottomOffset] = useState(0);
  const [introQuote, setIntroQuote] = useState("What are we building today?");
  const [hasMounted, setHasMounted] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const wsResolution = useMemo(() => {
    if (!hasMounted) {
      return { url: "", error: null as string | null };
    }

    try {
      return { url: getWebSocketUrl(), error: null as string | null };
    } catch (error) {
      const message = error instanceof Error ? error.message : "WebSocket URL is not configured.";
      return { url: "", error: message };
    }
  }, [hasMounted]);

  const normalizedSearchQuery = debouncedConversationSearchQuery.trim();
  const isSearchActive = normalizedSearchQuery.length > 0;
  const visibleConversations = isSearchActive ? searchResults : conversations;
  const shouldShowIntroQuote = !selectedConversationId;

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
  const uploadLimitBytes = uploadLimitMb * 1024 * 1024;

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

        if (isAuthFailureStatus(response.status)) {
          router.replace("/login");
          return;
        }

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
    [apiBaseUrl, router],
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

        if (isAuthFailureStatus(response.status)) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const detail = extractConversationDetail(payload);
        setMessagesByConversationId((previous) => ({
          ...previous,
          [conversationId]: mergeMessagesById(detail.messages),
        }));
      } catch {
        setTimelineError("Unable to load messages for this conversation.");
      } finally {
        setTimelineLoading(false);
      }
    },
    [apiBaseUrl, router],
  );

  useEffect(() => {
    setHasMounted(true);
  }, []);

  useEffect(() => {
    void loadConversations("initial");
  }, [loadConversations]);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      setDebouncedConversationSearchQuery(conversationSearchQuery);
    }, 300);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [conversationSearchQuery]);

  const searchRequestIdRef = useRef(0);

  const searchConversations = useCallback(async (query: string) => {
    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
      setSearchResults([]);
      setSearchErrorMessage(null);
      setSearchLoading(false);
      return;
    }

    const requestId = searchRequestIdRef.current + 1;
    searchRequestIdRef.current = requestId;
    setSearchLoading(true);
    setSearchErrorMessage(null);

    try {
      const response = await fetch(
        `${apiBaseUrl}/conversations/search?q=${encodeURIComponent(normalizedQuery)}`,
        {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        },
      );

      if (isAuthFailureStatus(response.status)) {
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`);
      }

      const payload = (await response.json()) as unknown;
      const normalized = extractConversations(payload)
        .map(normalizeConversation)
        .filter((item): item is ConversationItem => Boolean(item));

      if (searchRequestIdRef.current === requestId) {
        setSearchResults(normalized);
      }
    } catch {
      if (searchRequestIdRef.current === requestId) {
        setSearchErrorMessage("Unable to search conversations right now.");
      }
    } finally {
      if (searchRequestIdRef.current === requestId) {
        setSearchLoading(false);
      }
    }
  }, [apiBaseUrl, router]);

  useEffect(() => {
    void searchConversations(debouncedConversationSearchQuery);
  }, [debouncedConversationSearchQuery, searchConversations]);

  useEffect(() => {
    let isMounted = true;

    const loadUploadLimit = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/settings`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });
        if (isAuthFailureStatus(response.status)) {
          router.replace("/login");
          return;
        }
        if (!response.ok) {
          return;
        }

        const payload = (await response.json()) as {
          settings?: {
            upload_limit_mb_default?: unknown;
          };
        };
        const uploadLimitValue = payload.settings?.upload_limit_mb_default;
        if (typeof uploadLimitValue !== "number" || uploadLimitValue < 1) {
          return;
        }

        if (isMounted) {
          setUploadLimitMb(uploadLimitValue);
        }
      } catch {
        // Keep default fallback when settings are unavailable.
      }
    };

    void loadUploadLimit();
    return () => {
      isMounted = false;
    };
  }, [apiBaseUrl, router]);

  useEffect(() => {
    setSelectedConversationId(selectedFromQuery);
  }, [selectedFromQuery]);

  useEffect(() => {
    setAttachmentDrafts((previous) => {
      const valid = previous.filter((draft) => draft.file.size <= uploadLimitBytes);
      if (valid.length !== previous.length) {
        setAttachmentError(`One or more files exceeded the ${uploadLimitMb} MB limit and were removed.`);
      }
      return valid;
    });
  }, [uploadLimitBytes, uploadLimitMb]);

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

  const onPickAttachments = useCallback((pickedFiles: FileList | null) => {
    if (!pickedFiles || pickedFiles.length === 0) {
      return;
    }

    const incoming = Array.from(pickedFiles);
    const rejectedNames: string[] = [];

    setAttachmentDrafts((previous) => {
      const next = [...previous];
      for (const file of incoming) {
        if (file.size > uploadLimitBytes) {
          rejectedNames.push(file.name);
          continue;
        }

        const duplicate = next.some(
          (draft) =>
            draft.file.name === file.name &&
            draft.file.size === file.size &&
            draft.file.lastModified === file.lastModified,
        );
        if (duplicate) {
          continue;
        }

        next.push({
          id: createClientMessageId("attachment"),
          file,
        });
      }
      return next;
    });

    if (rejectedNames.length > 0) {
      const sample = rejectedNames.slice(0, 2).join(", ");
      const suffix = rejectedNames.length > 2 ? ` (+${rejectedNames.length - 2} more)` : "";
      setAttachmentError(`File exceeds ${uploadLimitMb} MB: ${sample}${suffix}`);
      return;
    }

    setAttachmentError(null);
  }, [uploadLimitBytes, uploadLimitMb]);

  const onRemoveAttachment = useCallback((attachmentId: string) => {
    setAttachmentDrafts((previous) => previous.filter((draft) => draft.id !== attachmentId));
    setAttachmentError(null);
  }, []);

  const appendOptimisticUserMessage = useCallback((
    conversationId: string,
    content: string,
    files: ChatMessageFile[],
  ): string => {
    const optimisticId = createClientMessageId("user");
    setMessagesByConversationId((previous) => ({
      ...previous,
      [conversationId]: [
        ...(previous[conversationId] ?? []),
        {
          id: optimisticId,
          role: "user",
          content,
          clientMessageId: optimisticId,
          authorUserId: "local-user",
          authorDisplayName: "YOU",
          isCurrentUserAuthor: true,
          createdAt: new Date().toISOString(),
          files,
          deliveryStatus: "sending",
        },
      ],
    }));
    return optimisticId;
  }, []);

  const uploadAttachments = useCallback(async (
    conversationId: string,
    drafts: AttachmentDraft[],
  ): Promise<ChatMessageFile[]> => {
    if (drafts.length === 0) {
      return [];
    }

    const formData = new FormData();
    for (const draft of drafts) {
      formData.append("files", draft.file);
    }

    const response = await fetch(`${apiBaseUrl}/conversations/${conversationId}/files`, {
      method: "POST",
      credentials: "include",
      headers: withCsrfHeader(),
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed with ${response.status}`);
    }

    const payload = (await response.json()) as { files?: UploadedFileResponse[] };
    const uploadedRows = Array.isArray(payload.files) ? payload.files : [];

    return uploadedRows
      .map((item) => normalizeMessageFile({
        id: item.id,
        original_name: item.original_name ?? item.originalName,
        storage_path: item.storage_path ?? item.storagePath,
        download_path: item.download_path ?? item.downloadPath,
        mime_type: item.mime_type ?? item.mimeType,
        size_bytes: item.size_bytes ?? item.sizeBytes,
      }))
      .filter((item): item is ChatMessageFile => Boolean(item));
  }, [apiBaseUrl]);

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
        headers: withCsrfHeader({
          "Content-Type": "application/json",
        }),
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


  const applyAssistantDone = useCallback((
    conversationId: string,
    messageId: string | null,
    content: string | null,
  ) => {
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
        if (messageId) {
          return {
            ...messageState,
            [conversationId]: upsertMessage(current, {
              id: messageId,
              role: "assistant",
              content: finalContent,
              createdAt: new Date().toISOString(),
            }),
          };
        }

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

  const applyCreatedMessage = useCallback((conversationId: string, rawMessage: unknown) => {
    if (!rawMessage || typeof rawMessage !== "object") {
      return;
    }

    const normalized = normalizeMessage(rawMessage as ApiConversationMessage);
    if (!normalized) {
      return;
    }

    setMessagesByConversationId((previous) => {
      const current = previous[conversationId] ?? [];
      const clientMessageId = normalized.clientMessageId;

      if (clientMessageId) {
        const optimisticIndex = current.findIndex(
          (message) =>
            message.clientMessageId === clientMessageId ||
            (message.id === clientMessageId && message.deliveryStatus !== undefined),
        );

        if (optimisticIndex !== -1) {
          const next = [...current];
          next[optimisticIndex] = {
            ...next[optimisticIndex],
            ...normalized,
            pending: false,
            deliveryStatus: undefined,
            isCurrentUserAuthor:
              normalized.isCurrentUserAuthor ?? next[optimisticIndex].isCurrentUserAuthor,
          };
          return {
            ...previous,
            [conversationId]: mergeMessagesById(next),
          };
        }
      }

      return {
        ...previous,
        [conversationId]: upsertMessage(current, normalized),
      };
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

        applyAssistantDone(
          conversationId,
          typeof doneEvent.message_id === "string" ? doneEvent.message_id : null,
          doneContent,
        );
        return;
      }

      if (event.type === "message_created") {
        const createdEvent = event as MessageCreatedEvent;
        applyCreatedMessage(conversationId, createdEvent.message);
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
    [applyAssistantDone, applyCreatedMessage, markLatestSendingMessageAsFailed, selectedConversationId],
  );

  const {
    connectionState,
    reconnectAttempts,
    sendJsonMessage,
    retryNow,
  } = useChatWebSocket({
    url: wsResolution.url,
    enabled: hasMounted && wsResolution.error === null,
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
      setAttachmentError(null);

      let uploadedFiles: ChatMessageFile[] = [];
      if (attachmentDrafts.length > 0) {
        try {
          setUploadingAttachments(true);
          uploadedFiles = await uploadAttachments(conversationId, attachmentDrafts);
        } catch {
          setSendErrorByConversationId((previous) => ({
            ...previous,
            [conversationId]: "Files failed to upload. Remove invalid files and retry.",
          }));
          return false;
        } finally {
          setUploadingAttachments(false);
        }
      }

      const optimisticId = appendOptimisticUserMessage(conversationId, trimmedContent, uploadedFiles);
      const sent = sendJsonMessage({
        type: "send_message",
        conversationId,
        content: trimmedContent,
        file_ids: uploadedFiles.map((file) => file.id),
        client_message_id: optimisticId,
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
      setAttachmentDrafts([]);
      setAttachmentError(null);
      return true;
    },
    [
      appendOptimisticUserMessage,
      attachmentDrafts,
      ensureConversationForSend,
      markMessageAsFailed,
      markMessageAsSent,
      sendJsonMessage,
      uploadAttachments,
    ],
  );

  const onComposerSubmit = useCallback(async () => {
    const sent = await submitMessage(composerValue);
    if (sent) {
      setComposerValue("");
      const activeElement = document.activeElement;
      if (activeElement instanceof HTMLElement) {
        activeElement.blur();
      }
      setComposerBottomOffset(0);
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
      file_ids: (failedMessage.files ?? []).map((file) => file.id),
      client_message_id: failedMessage.clientMessageId ?? failedMessage.id,
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
    !isUploadingAttachments &&
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

  useEffect(() => {
    let mounted = true;

    const loadIntroQuote = async () => {
      try {
        const response = await fetch("/content/chat-intro-quotes.md", {
          method: "GET",
          cache: "no-store",
        });
        if (!response.ok) {
          return;
        }

        const markdown = await response.text();
        const parsed = parseIntroQuotes(markdown);
        if (mounted) {
          setIntroQuote(pickRandomQuote(parsed));
        }
      } catch {
        // Keep fallback quote on load failure.
      }
    };

    void loadIntroQuote();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const saved = window.localStorage.getItem("chat_sidebar_collapsed");
    if (saved === "1") {
      setSidebarCollapsed(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem("chat_sidebar_collapsed", isSidebarCollapsed ? "1" : "0");
  }, [isSidebarCollapsed]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const viewport = window.visualViewport;
    if (!viewport) {
      return;
    }

    const updateBottomOffset = () => {
      const keyboardInset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
      setComposerBottomOffset(Math.round(keyboardInset));
    };

    updateBottomOffset();
    viewport.addEventListener("resize", updateBottomOffset);
    viewport.addEventListener("scroll", updateBottomOffset);
    window.addEventListener("resize", updateBottomOffset);
    window.addEventListener("orientationchange", updateBottomOffset);

    return () => {
      viewport.removeEventListener("resize", updateBottomOffset);
      viewport.removeEventListener("scroll", updateBottomOffset);
      window.removeEventListener("resize", updateBottomOffset);
      window.removeEventListener("orientationchange", updateBottomOffset);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const updateAutoScrollIntent = () => {
      const viewportBottom = window.scrollY + window.innerHeight;
      const pageHeight = document.documentElement.scrollHeight;
      shouldAutoScrollRef.current = pageHeight - viewportBottom < 220;
    };

    updateAutoScrollIntent();
    window.addEventListener("scroll", updateAutoScrollIntent, { passive: true });
    return () => {
      window.removeEventListener("scroll", updateAutoScrollIntent);
    };
  }, []);

  useEffect(() => {
    if (!selectedConversationId || timelineLoading || !shouldAutoScrollRef.current) {
      return;
    }

    window.requestAnimationFrame(() => {
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: "auto",
      });
    });
  }, [selectedConversationId, selectedTimelineMessages, timelineLoading]);

  const onSearchAction = useCallback(() => {
    setSidebarCollapsed(false);
    window.requestAnimationFrame(() => {
      searchInputRef.current?.focus();
    });
  }, []);

  return (
    <div
      className={`min-h-screen min-h-dvh bg-background text-foreground md:grid ${
        isSidebarCollapsed ? "md:grid-cols-[78px_1fr]" : "md:grid-cols-[320px_1fr]"
      }`}
    >
      <aside className="hidden border-r border-border bg-muted/40 md:sticky md:top-0 md:flex md:h-screen md:flex-col">
        {isSidebarCollapsed ? (
          <CollapsedSidebarContent
            onExpand={() => setSidebarCollapsed(false)}
            onSearchAction={onSearchAction}
            onNewChat={onNewChat}
          />
        ) : (
          <SidebarContent
            conversations={visibleConversations}
            searchQuery={conversationSearchQuery}
            isSearchActive={isSearchActive}
            isSearchLoading={isSearchLoading}
            searchErrorMessage={searchErrorMessage}
            selectedConversationId={selectedConversationId}
            busyByConversationId={busyByConversationId}
            isLoading={isLoading}
            isRefreshing={isRefreshing}
            errorMessage={errorMessage}
            listRef={listRef}
            searchInputRef={searchInputRef}
            onConversationListScroll={onConversationListScroll}
            onSelectConversation={onSelectConversation}
            onNewChat={onNewChat}
            onSearchChange={setConversationSearchQuery}
            onRetrySearch={() => void searchConversations(debouncedConversationSearchQuery)}
            onRetry={() => void loadConversations("refresh")}
            onCollapse={() => setSidebarCollapsed(true)}
          />
        )}
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur md:hidden">
          <button
            type="button"
            aria-label="Open conversation sidebar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-lg"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu className="h-4 w-4" />
          </button>
          <Link href="/chat" className="inline-flex items-center gap-2">
            <WinkingLogo size={24} />
            <span className="text-sm font-semibold tracking-[0.14em] uppercase">CodexChat</span>
          </Link>
          <span className="h-9 w-9" aria-hidden />
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
                conversations={visibleConversations}
                searchQuery={conversationSearchQuery}
                isSearchActive={isSearchActive}
                isSearchLoading={isSearchLoading}
                searchErrorMessage={searchErrorMessage}
                selectedConversationId={selectedConversationId}
                busyByConversationId={busyByConversationId}
                isLoading={isLoading}
                isRefreshing={isRefreshing}
                errorMessage={errorMessage}
                listRef={listRef}
                searchInputRef={searchInputRef}
                onConversationListScroll={onConversationListScroll}
                onSelectConversation={onSelectConversation}
                onNewChat={onNewChat}
                onSearchChange={setConversationSearchQuery}
                onRetrySearch={() => void searchConversations(debouncedConversationSearchQuery)}
                onRetry={() => void loadConversations("refresh")}
                mobile
                onClose={() => setDrawerOpen(false)}
              />
            </aside>
          </div>
        ) : null}

        <main className="mx-auto flex min-h-[calc(100vh-56px)] min-h-[calc(100dvh-56px)] w-full max-w-5xl flex-col px-4 py-6 pb-72 sm:px-6 md:min-h-screen md:min-h-dvh md:py-8 md:pb-72">
          <div className="mb-3 flex justify-end">
            <ConnectionBadge
              state={connectionState}
              reconnectAttempts={reconnectAttempts}
              hasConfigError={Boolean(wsResolution.error)}
              onRetry={retryNow}
            />
          </div>

          {wsResolution.error && selectedConversationId ? (
            <p className="mb-3 text-sm text-muted-foreground">{wsResolution.error}</p>
          ) : null}

          {shouldShowIntroQuote ? (
            <div className="mt-6 rounded-xl border border-border bg-muted/30 px-5 py-6 text-center sm:px-6">
              <p
                className="text-lg font-medium tracking-tight text-foreground sm:text-xl"
                suppressHydrationWarning
              >
                {introQuote}
              </p>
            </div>
          ) : (
            <MessageTimeline
              isLoading={timelineLoading}
              errorMessage={timelineError}
              messages={selectedTimelineMessages}
              selectedConversationId={selectedConversationId}
              onRetryFailedMessage={onRetryFailedMessage}
              onRetry={() => selectedConversationId ? void loadConversationMessages(selectedConversationId) : undefined}
            />
          )}
        </main>
        <ComposerPanel
          value={composerValue}
          setValue={setComposerValue}
          onSubmit={onComposerSubmit}
          disabled={!canSubmitComposer}
          isBusy={selectedConversationBusy}
          isCreatingConversation={isCreatingConversation}
          isUploadingAttachments={isUploadingAttachments}
          connectionState={connectionState}
          hasConfigError={Boolean(wsResolution.error)}
          sendError={selectedSendError}
          selectedAttachments={attachmentDrafts}
          attachmentError={attachmentError}
          onPickAttachments={onPickAttachments}
          onRemoveAttachment={onRemoveAttachment}
          bottomOffset={composerBottomOffset}
          sidebarCollapsed={isSidebarCollapsed}
        />
      </div>
    </div>
  );
}

type SidebarContentProps = {
  conversations: ConversationItem[];
  searchQuery: string;
  isSearchActive: boolean;
  isSearchLoading: boolean;
  searchErrorMessage: string | null;
  selectedConversationId: string | null;
  busyByConversationId: Record<string, boolean>;
  isLoading: boolean;
  isRefreshing: boolean;
  errorMessage: string | null;
  listRef: React.RefObject<HTMLDivElement | null>;
  searchInputRef?: React.RefObject<HTMLInputElement | null>;
  onConversationListScroll: () => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
  onSearchChange: (value: string) => void;
  onRetrySearch: () => void;
  onRetry: () => void;
  onCollapse?: () => void;
  mobile?: boolean;
  onClose?: () => void;
};

function SidebarContent({
  conversations,
  searchQuery,
  isSearchActive,
  isSearchLoading,
  searchErrorMessage,
  selectedConversationId,
  busyByConversationId,
  isLoading,
  isRefreshing,
  errorMessage,
  listRef,
  searchInputRef,
  onConversationListScroll,
  onSelectConversation,
  onNewChat,
  onSearchChange,
  onRetrySearch,
  onRetry,
  onCollapse,
  mobile = false,
  onClose,
}: SidebarContentProps) {
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <Link href="/chat" className="inline-flex items-center gap-2 text-sm font-semibold tracking-[0.18em] uppercase">
          <WinkingLogo size={24} />
          <span>CodexChat</span>
        </Link>
        <div className="flex items-center gap-2">
          {!mobile ? (
            <button
              type="button"
              aria-label="Collapse sidebar"
              className="inline-flex h-9 w-9 items-center justify-center text-base text-muted-foreground transition hover:text-foreground"
              onClick={onCollapse}
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          ) : null}
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

      <div className="mt-4">
        <label htmlFor="conversation-search" className="sr-only">
          Search conversations
        </label>
        <input
          ref={searchInputRef}
          id="conversation-search"
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search conversations"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/15"
        />
      </div>

      <p className="mt-6 text-xs font-semibold tracking-[0.16em] uppercase text-muted-foreground">
        {isSearchActive ? "Search results" : "Recent"}
      </p>

      <div
        ref={listRef}
        onScroll={onConversationListScroll}
        className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1"
      >
        {!isSearchActive && isLoading ? (
          <ConversationListLoading />
        ) : null}

        {!isSearchActive && !isLoading && errorMessage ? (
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

        {isSearchActive && isSearchLoading ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm text-muted-foreground">
            Searching conversations…
          </div>
        ) : null}

        {isSearchActive && !isSearchLoading && searchErrorMessage ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm">
            <p className="text-muted-foreground">{searchErrorMessage}</p>
            <button
              type="button"
              className="mt-3 rounded-md border border-border px-3 py-1.5 text-sm font-medium transition hover:bg-muted"
              onClick={onRetrySearch}
            >
              Retry search
            </button>
          </div>
        ) : null}

        {!isSearchActive && !isLoading && !errorMessage && conversations.length === 0 ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm text-muted-foreground">
            No conversations yet - start a new chat
          </div>
        ) : null}

        {isSearchActive && !isSearchLoading && !searchErrorMessage && conversations.length === 0 ? (
          <div className="rounded-xl border border-border bg-background p-3 text-sm text-muted-foreground">
            No matches found.
          </div>
        ) : null}

        {((!isSearchActive && !isLoading && !errorMessage) ||
          (isSearchActive && !isSearchLoading && !searchErrorMessage)) &&
        conversations.length > 0
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
                  <p className="mt-1 text-xs text-muted-foreground" suppressHydrationWarning>
                    {formatUpdatedAt(conversation.updatedAt)}
                  </p>
                </button>
              );
            })
          : null}
      </div>

      <div className="mt-4 shrink-0 border-t border-border bg-muted/40 pt-4">
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/settings"
            className="inline-flex items-center gap-2 rounded-md px-2 py-1 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground"
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>
          <form method="post" action="/logout">
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm font-medium transition hover:bg-muted"
            >
              <LogOut className="h-4 w-4" />
              Log out
            </button>
          </form>
        </div>
        {isRefreshing ? <p className="mt-2 text-xs text-muted-foreground">Refreshing…</p> : null}
      </div>
    </div>
  );
}

type CollapsedSidebarContentProps = {
  onExpand: () => void;
  onSearchAction: () => void;
  onNewChat: () => void;
};

function CollapsedSidebarContent({
  onExpand,
  onSearchAction,
  onNewChat,
}: CollapsedSidebarContentProps) {
  return (
    <div className="flex h-full min-h-0 flex-col items-center gap-2 p-3">
      <button
        type="button"
        aria-label="Expand sidebar"
        className="mt-1 inline-flex h-10 w-10 items-center justify-center"
        onClick={onExpand}
      >
        <WinkingLogo size={28} />
      </button>

      <div className="mt-2 flex flex-col items-center gap-2">
        <button
          type="button"
          aria-label="Search conversations"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition hover:bg-muted"
          onClick={onSearchAction}
          title="Search conversations"
        >
          <Search className="h-4 w-4" />
        </button>
        <button
          type="button"
          aria-label="New chat"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition hover:bg-muted"
          onClick={onNewChat}
          title="New chat"
        >
          <SquarePen className="h-4 w-4" />
        </button>
        <Link
          href="/settings"
          aria-label="Settings"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition hover:bg-muted"
          title="Settings"
        >
          <Settings className="h-4 w-4" />
        </Link>
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
  isUploadingAttachments: boolean;
  connectionState: "connecting" | "connected" | "reconnecting" | "disconnected";
  hasConfigError: boolean;
  sendError: string | null;
  selectedAttachments: AttachmentDraft[];
  attachmentError: string | null;
  onPickAttachments: (files: FileList | null) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  bottomOffset: number;
  sidebarCollapsed: boolean;
};

function ComposerPanel({
  value,
  setValue,
  onSubmit,
  disabled,
  isBusy,
  isCreatingConversation,
  isUploadingAttachments,
  connectionState,
  hasConfigError,
  sendError,
  selectedAttachments,
  attachmentError,
  onPickAttachments,
  onRemoveAttachment,
  bottomOffset,
  sidebarCollapsed,
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

  const statusText =
    sendError ??
    attachmentError ??
    (isCreatingConversation
      ? "Creating conversation…"
      : isUploadingAttachments
        ? "Uploading attachments…"
        : isBusy
          ? "This conversation is busy."
          : hasConfigError || connectionState !== "connected"
            ? "WebSocket is not connected."
            : null);

  return (
    <div
      className={`fixed inset-x-0 z-30 ${sidebarCollapsed ? "md:left-[78px]" : "md:left-[320px]"}`}
      style={{ bottom: `${bottomOffset + 10}px` }}
    >
      <div className="mx-auto w-full max-w-5xl px-4 sm:px-6">
        <div className="rounded-[999px] border border-border bg-background/95 p-2 shadow-2xl backdrop-blur">
          <label htmlFor="chat-composer" className="sr-only">
            Message
          </label>
          <div className="flex items-center gap-2">
            <label className="inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition hover:text-foreground">
              <span className="sr-only">Attach files</span>
              <Paperclip className="h-4 w-4" />
              <input
                type="file"
                className="sr-only"
                multiple
                onChange={(event) => {
                  onPickAttachments(event.target.files);
                  event.currentTarget.value = "";
                }}
              />
            </label>
            <textarea
              id="chat-composer"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Send a message…"
              className="max-h-40 min-h-10 w-full resize-none rounded-full border border-border bg-background px-4 py-2 text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/15"
            />
            <button
              type="button"
              aria-label="Send message"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
              disabled={disabled}
              onClick={() => void onSubmit()}
            >
              <SendHorizontal className="h-4 w-4" />
            </button>
          </div>
          {selectedAttachments.length > 0 ? (
            <ul className="mt-3 flex flex-wrap gap-2">
              {selectedAttachments.map((draft) => (
                <li key={draft.id} className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-xs">
                  <span title={draft.file.name}>{formatAttachmentName(draft.file.name)}</span>
                  <span className="text-muted-foreground">{formatFileSize(draft.file.size)}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${draft.file.name}`}
                    className="rounded-full border border-border p-1 leading-none transition hover:bg-muted"
                    onClick={() => onRemoveAttachment(draft.id)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {statusText ? <p className="mt-2 px-1 text-center text-xs text-muted-foreground">{statusText}</p> : null}
        </div>
      </div>
    </div>
  );
}

function StreamingTrail() {
  const [frame, setFrame] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setFrame((previous) => (previous % 3) + 1);
    }, 420);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  return (
    <span className="inline-block min-w-4 text-muted-foreground" aria-hidden>
      {".".repeat(frame)}
    </span>
  );
}

function messageLabel(message: ChatMessage): string {
  if (message.role === "assistant") {
    return "Assistant";
  }

  if (message.role === "system") {
    return "System";
  }

  if (message.isCurrentUserAuthor === true) {
    return "YOU";
  }

  return message.authorDisplayName ?? "Former User";
}

function messageAvatarFallback(message: ChatMessage): string {
  const source = message.authorDisplayName?.trim() || "U";
  if (!source) {
    return "U";
  }
  return source[0].toUpperCase();
}

function MessageRow({ message, onRetry }: { message: ChatMessage; onRetry?: () => void }) {
  const isOwnUserMessage = message.role === "user" && message.isCurrentUserAuthor === true;
  const rowClassName = isOwnUserMessage ? "flex justify-end" : "flex justify-start";
  const cardClassName =
    message.role === "assistant"
      ? "w-full rounded-xl border border-border bg-background p-4"
      : message.role === "system"
        ? "w-full rounded-xl border border-border bg-muted/60 p-4"
        : "w-full max-w-[70%] rounded-2xl bg-muted/20 p-4";
  const label = messageLabel(message);
  const showAvatar = message.role === "user";

  return (
    <div className={rowClassName}>
      <article className={cardClassName}>
        <header className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {showAvatar ? (
              message.authorProfilePictureUrl ? (
                // next/image proxy fetch can drop auth cookie for protected file endpoints.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={message.authorProfilePictureUrl}
                  alt={label}
                  className="h-6 w-6 rounded-full border border-border object-cover"
                />
              ) : (
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground">
                  {messageAvatarFallback(message)}
                </span>
              )
            ) : null}
            <p className="text-xs font-semibold tracking-[0.12em] uppercase text-muted-foreground">
              {label}
              {message.pending ? " (streaming)" : message.deliveryStatus === "sending" ? " (sending)" : ""}
            </p>
          </div>
          <p className="text-xs text-muted-foreground" suppressHydrationWarning>
            {formatMessageTimestamp(message.createdAt)}
          </p>
        </header>
        <div className="text-sm leading-6">
          <MessageMarkdown content={message.content} />
          {message.role === "assistant" && message.pending ? <StreamingTrail /> : null}
        </div>
        {message.files && message.files.length > 0 ? (
          <div className="mt-3 rounded-md border border-border bg-background/70 p-3">
            <p className="text-[11px] font-semibold tracking-[0.1em] uppercase text-muted-foreground">
              Attached files
            </p>
            <ul className="mt-2 space-y-2">
              {message.files.map((file) => (
                <li key={file.id} className="text-xs">
                  {isPreviewableImage(file) ? (
                    <a
                      href={file.downloadPath}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mb-2 inline-block"
                      aria-label={`Open image ${file.originalName}`}
                    >
                      {/* next/image proxy fetch can drop auth cookie for protected file endpoints. */}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={file.downloadPath}
                        alt={file.originalName}
                        loading="lazy"
                        className="h-20 w-20 rounded-md border border-border object-cover"
                      />
                    </a>
                  ) : null}
                  <a
                    href={file.downloadPath}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-foreground underline underline-offset-2"
                    title={file.originalName}
                  >
                    {formatAttachmentName(file.originalName)}
                  </a>
                  <p className="mt-0.5 break-all text-muted-foreground">{file.storagePath}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
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
    </div>
  );
}
