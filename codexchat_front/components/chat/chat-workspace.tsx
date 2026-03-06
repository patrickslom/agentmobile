"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import ThemeToggle from "@/app/components/theme-toggle";
import { getApiBaseUrl } from "@/lib/network-config";

type ApiConversation = {
  id?: string;
  title?: string | null;
  updated_at?: string;
  updatedAt?: string;
  created_at?: string;
  createdAt?: string;
};

type ConversationItem = {
  id: string;
  title: string;
  updatedAt: string | null;
};

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

  const listRef = useRef<HTMLDivElement | null>(null);
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

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
      } catch {
        setErrorMessage("Unable to load conversations right now.");
      } finally {
        setLoading(false);
        setRefreshing(false);
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

  const selectedConversation =
    conversations.find((item) => item.id === selectedConversationId) ?? null;

  return (
    <div className="min-h-screen min-h-dvh bg-background text-foreground md:grid md:grid-cols-[320px_1fr]">
      <aside className="hidden border-r border-border bg-muted/40 md:flex md:min-h-screen md:min-h-dvh md:flex-col">
        <SidebarContent
          conversations={conversations}
          selectedConversationId={selectedConversationId}
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
            <aside className="relative z-10 h-full w-[min(100vw,24rem)] border-r border-border bg-background">
              <SidebarContent
                conversations={conversations}
                selectedConversationId={selectedConversationId}
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
            <p className="text-xs font-semibold tracking-[0.14em] uppercase text-muted-foreground">
              Conversation
            </p>
            {selectedConversation ? (
              <>
                <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">
                  {selectedConversation.title}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Resumed from sidebar selection. Message timeline and streaming will render here.
                </p>
              </>
            ) : (
              <>
                <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">New chat</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Start a new conversation from here. Select an existing chat in the sidebar to resume it.
                </p>
              </>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

type SidebarContentProps = {
  conversations: ConversationItem[];
  selectedConversationId: string | null;
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
                  <p className="truncate text-sm font-medium">{conversation.title}</p>
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
