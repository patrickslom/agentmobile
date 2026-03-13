"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, MessageSquarePlus, Search } from "lucide-react";
import { getApiBaseUrl } from "@/lib/network-config";

type ApiConversation = {
  id?: string;
  title?: string | null;
  summary_short?: string | null;
  summaryShort?: string | null;
  updated_at?: string;
  updatedAt?: string;
  created_at?: string;
  createdAt?: string;
};

type ConversationItem = {
  id: string;
  title: string;
  summaryShort: string | null;
  updatedAt: string | null;
};

const RECENT_CHATS_PAGE_SIZE = 12;

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
    summaryShort:
      typeof item.summary_short === "string"
        ? item.summary_short.trim() || null
        : typeof item.summaryShort === "string"
          ? item.summaryShort.trim() || null
          : null,
    updatedAt: item.updated_at ?? item.updatedAt ?? item.created_at ?? item.createdAt ?? null,
  };
}

function formatUpdatedAt(value: string | null): string {
  if (!value) {
    return "No recent activity";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "No recent activity";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const match = document.cookie.match(/(?:^|;\s*)agentmobile_csrf=([^;]+)/);
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

export default function ChatHomePageClient() {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const [recentConversations, setRecentConversations] = useState<ConversationItem[]>([]);
  const [searchResults, setSearchResults] = useState<ConversationItem[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setLoading] = useState(true);
  const [isSearching, setSearching] = useState(false);
  const [isCreating, setCreating] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [visibleRecentCount, setVisibleRecentCount] = useState(RECENT_CHATS_PAGE_SIZE);

  const loadRecent = useCallback(async () => {
    setLoading(true);
    setPageError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/conversations`, {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Unable to load conversations (${response.status})`);
      }

      const payload = (await response.json()) as unknown;
      setRecentConversations(
        extractConversations(payload)
          .map((item) => normalizeConversation(item))
          .filter((item): item is ConversationItem => Boolean(item)),
      );
      setVisibleRecentCount(RECENT_CHATS_PAGE_SIZE);
    } catch (error) {
      setPageError(
        error instanceof Error && error.message
          ? error.message
          : "Unable to load conversations right now.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, router]);

  useEffect(() => {
    void loadRecent();
  }, [loadRecent]);

  useEffect(() => {
    const normalized = query.trim();
    if (!normalized) {
      setSearchResults([]);
      setSearchError(null);
      setSearching(false);
      setVisibleRecentCount(RECENT_CHATS_PAGE_SIZE);
      return;
    }

    const timer = window.setTimeout(async () => {
      setSearching(true);
      setSearchError(null);

      try {
        const response = await fetch(
          `${apiBaseUrl}/conversations/search?q=${encodeURIComponent(normalized)}`,
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
          },
        );

        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(`Search failed (${response.status})`);
        }

        const payload = (await response.json()) as unknown;
        setSearchResults(
          extractConversations(payload)
            .map((item) => normalizeConversation(item))
            .filter((item): item is ConversationItem => Boolean(item)),
        );
      } catch (error) {
        setSearchError(
          error instanceof Error && error.message ? error.message : "Unable to search right now.",
        );
      } finally {
        setSearching(false);
      }
    }, 220);

    return () => {
      window.clearTimeout(timer);
    };
  }, [apiBaseUrl, query, router]);

  const onCreateConversation = useCallback(async () => {
    if (isCreating) {
      return;
    }

    setCreating(true);
    try {
      const response = await fetch(`${apiBaseUrl}/conversations`, {
        method: "POST",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify({}),
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Create failed (${response.status})`);
      }

      const payload = (await response.json()) as {
        conversation?: { id?: string };
      };
      const conversationId = payload.conversation?.id;
      if (!conversationId) {
        throw new Error("Conversation payload is missing an id");
      }

      router.push(`/chat?conversationId=${encodeURIComponent(conversationId)}`);
    } catch (error) {
      setPageError(
        error instanceof Error && error.message
          ? error.message
          : "Unable to create a new chat right now.",
      );
    } finally {
      setCreating(false);
    }
  }, [apiBaseUrl, isCreating, router]);

  const showingSearchResults = query.trim().length > 0;
  const visibleConversations = showingSearchResults
    ? searchResults
    : recentConversations.slice(0, visibleRecentCount);
  const hasMoreRecentConversations =
    !showingSearchResults && visibleRecentCount < recentConversations.length;

  return (
    <section className="mx-auto flex min-w-0 w-full max-w-6xl flex-col gap-6 overflow-x-hidden">
      <header className="min-w-0 overflow-hidden rounded-[28px] border border-border/80 bg-background/92 p-6 shadow-[0_12px_40px_rgba(0,0,0,0.06)] backdrop-blur sm:p-8">
        <div className="flex min-w-0 flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
              Chat
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Search your conversations or start a fresh thread.
            </h1>
            <p className="mt-3 max-w-xl text-sm text-muted-foreground sm:text-base">
              This is the chat home for desktop and mobile. Find recent work fast, then jump back into the thread you need.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void onCreateConversation()}
            disabled={isCreating}
            className="inline-flex items-center justify-center gap-3 whitespace-nowrap rounded-2xl bg-foreground px-5 py-3 text-sm font-semibold text-background transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <MessageSquarePlus className="h-5 w-5" />
            {isCreating ? "Creating chat…" : "New chat"}
          </button>
        </div>

        <div className="mt-6 rounded-2xl border border-border bg-muted/50 p-2">
          <label htmlFor="chat-home-search" className="sr-only">
            Search chat history
          </label>
          <div className="flex items-center gap-3 rounded-2xl bg-background px-4 py-3">
            <Search className="h-5 w-5 text-muted-foreground" />
            <input
              id="chat-home-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search titles and message history"
              className="w-full border-0 bg-transparent text-sm outline-none sm:text-base"
            />
          </div>
        </div>
      </header>

      {pageError ? (
        <div className="rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
          {pageError}
        </div>
      ) : null}

      <section className="min-w-0 overflow-hidden rounded-[28px] border border-border/80 bg-background/88 p-5 shadow-[0_12px_40px_rgba(0,0,0,0.05)] backdrop-blur sm:p-6">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold tracking-tight">
              {query.trim() ? "Search results" : "Recent chats"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {query.trim()
                ? "Open any result to continue the conversation."
                : "Your latest conversations appear here for fast re-entry."}
            </p>
          </div>
          {isSearching ? (
            <span className="text-sm text-muted-foreground">Searching…</span>
          ) : null}
        </div>

        {searchError ? (
          <div className="mt-5 rounded-2xl border border-border bg-muted/60 px-4 py-3 text-sm text-muted-foreground">
            {searchError}
          </div>
        ) : null}

        {isLoading ? (
          <div className="mt-5 grid gap-3">
            <div className="rounded-2xl border border-border bg-muted/50 p-4">
              <div className="h-4 w-32 animate-pulse rounded bg-border/60" />
              <div className="mt-3 h-3 w-full animate-pulse rounded bg-border/50" />
            </div>
            <div className="rounded-2xl border border-border bg-muted/50 p-4">
              <div className="h-4 w-40 animate-pulse rounded bg-border/60" />
              <div className="mt-3 h-3 w-3/4 animate-pulse rounded bg-border/50" />
            </div>
          </div>
        ) : null}

        {!isLoading && visibleConversations.length === 0 ? (
          <div className="mt-5 rounded-2xl border border-dashed border-border bg-muted/40 px-5 py-10 text-center">
            <p className="text-base font-medium text-foreground">
              {query.trim() ? "No matching conversations yet." : "No conversations yet."}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {query.trim()
                ? "Try a different search term or start a new chat."
                : "Create your first chat to begin building history."}
            </p>
          </div>
        ) : null}

        {!isLoading && visibleConversations.length > 0 ? (
          <div className="mt-5 grid gap-3">
            {visibleConversations.map((conversation) => (
              <Link
                key={conversation.id}
                href={`/chat?conversationId=${encodeURIComponent(conversation.id)}`}
                className="group min-w-0 overflow-hidden rounded-2xl border border-border bg-background px-4 py-4 transition hover:border-foreground/35 hover:shadow-[0_10px_28px_rgba(0,0,0,0.08)] sm:px-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold text-foreground">
                      {conversation.title}
                    </p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      {formatUpdatedAt(conversation.updatedAt)}
                    </p>
                    {conversation.summaryShort ? (
                      <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
                        {conversation.summaryShort}
                      </p>
                    ) : (
                      <p className="mt-3 text-sm text-muted-foreground">
                        Open this thread to continue the conversation.
                      </p>
                    )}
                  </div>
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition group-hover:text-foreground">
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </Link>
            ))}

            {hasMoreRecentConversations ? (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() =>
                    setVisibleRecentCount((current) => current + RECENT_CHATS_PAGE_SIZE)
                  }
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm font-medium transition hover:border-foreground/35 hover:bg-muted/40"
                >
                  Load more chats
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </section>
  );
}
