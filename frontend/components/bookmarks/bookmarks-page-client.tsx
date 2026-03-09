"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Bookmark, ExternalLink, Trash2 } from "lucide-react";
import ToastStack, { type ToastItem, type ToastTone } from "@/components/ui/toast-stack";
import { getApiBaseUrl } from "@/lib/network-config";

type BookmarkItem = {
  id: string;
  user_id: string;
  owner_display_name: string;
  owner_profile_picture_url?: string | null;
  is_current_user_owner: boolean;
  message_id: string;
  conversation_id: string;
  conversation_title: string;
  conversation_summary_short?: string | null;
  message_preview: string;
  message_created_at: string;
  created_at: string;
};

type BookmarkPayload = {
  bookmarks?: BookmarkItem[];
};

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

function createToastId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function parseErrorMessage(raw: unknown, fallback: string): string {
  if (!raw || typeof raw !== "object") {
    return fallback;
  }

  const payload = raw as {
    error?: {
      message?: string;
    };
    message?: string;
  };
  const message = payload.error?.message ?? payload.message;
  if (typeof message !== "string" || !message.trim()) {
    return fallback;
  }

  return message;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export default function BookmarksPageClient() {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [isLoading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [deletingMessageId, setDeletingMessageId] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const pushToast = useCallback((tone: ToastTone, title: string, description?: string) => {
    const id = createToastId("bookmark-page-toast");
    setToasts((previous) => [...previous, { id, tone, title, description }]);
    window.setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  const loadBookmarks = useCallback(async (nextScope: "mine" | "all") => {
    setLoading(true);
    setPageError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/bookmarks?scope=${encodeURIComponent(nextScope)}`, {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to load bookmarks (${response.status})`);
      }

      const payload = (await response.json()) as BookmarkPayload;
      setBookmarks(Array.isArray(payload.bookmarks) ? payload.bookmarks : []);
    } catch (error) {
      const fallback = "Unable to load bookmarks right now.";
      setPageError(error instanceof Error && error.message ? error.message : fallback);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, router]);

  useEffect(() => {
    void loadBookmarks(scope);
  }, [loadBookmarks, scope]);

  const removeBookmark = useCallback(
    async (messageId: string) => {
      setDeletingMessageId(messageId);

      try {
        const response = await fetch(`${apiBaseUrl}/bookmarks/${encodeURIComponent(messageId)}`, {
          method: "DELETE",
          credentials: "include",
          cache: "no-store",
          headers: withCsrfHeader(),
        });

        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as unknown;
          throw new Error(parseErrorMessage(payload, `Delete failed (${response.status})`));
        }

        setBookmarks((previous) =>
          previous.filter(
            (bookmark) => !(bookmark.message_id === messageId && bookmark.is_current_user_owner),
          ),
        );
        pushToast("success", "Bookmark removed");
      } catch (error) {
        pushToast(
          "error",
          "Unable to remove bookmark",
          error instanceof Error && error.message ? error.message : "Network error while removing bookmark.",
        );
      } finally {
        setDeletingMessageId(null);
      }
    },
    [apiBaseUrl, pushToast, router],
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(0,0,0,0.04),_transparent_34%),linear-gradient(180deg,#fafaf9_0%,#f4f4f0_100%)] px-4 py-6 text-foreground sm:px-6">
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to chat
            </Link>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">Bookmarks</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Browse your own saved assistant responses or the full team bookmark stream.
            </p>
          </div>
          <Link
            href="/settings"
            className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium transition hover:bg-muted"
          >
            Settings
          </Link>
        </div>

        <div className="mt-6 inline-flex rounded-xl border border-border bg-background p-1">
          <button
            type="button"
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              scope === "mine" ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setScope("mine")}
          >
            My bookmarks
          </button>
          <button
            type="button"
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              scope === "all" ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setScope("all")}
          >
            All bookmarks
          </button>
        </div>

        {isLoading ? (
          <div className="mt-8 space-y-3">
            <div className="rounded-2xl border border-border bg-background p-5">
              <div className="h-4 w-1/4 animate-pulse rounded bg-muted" />
              <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
              <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-muted" />
            </div>
            <div className="rounded-2xl border border-border bg-background p-5">
              <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
              <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
              <div className="mt-2 h-3 w-1/2 animate-pulse rounded bg-muted" />
            </div>
          </div>
        ) : null}

        {!isLoading && pageError ? (
          <div className="mt-8 rounded-2xl border border-border bg-background p-5">
            <p className="text-sm text-muted-foreground">{pageError}</p>
            <button
              type="button"
              className="mt-4 rounded-lg border border-border px-4 py-2 text-sm font-medium transition hover:bg-muted"
              onClick={() => void loadBookmarks(scope)}
            >
              Retry
            </button>
          </div>
        ) : null}

        {!isLoading && !pageError && bookmarks.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-dashed border-border bg-background/80 p-8 text-center">
            <Bookmark className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm text-muted-foreground">
              {scope === "mine"
                ? "No bookmarks yet. Save an assistant response from chat to see it here."
                : "No bookmarks exist yet across the team."}
            </p>
          </div>
        ) : null}

        {!isLoading && !pageError && bookmarks.length > 0 ? (
          <div className="mt-8 grid gap-4">
            {bookmarks.map((bookmark) => (
              <article
                key={bookmark.id}
                className="rounded-2xl border border-border bg-background/95 p-5 shadow-sm"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      {bookmark.owner_profile_picture_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={bookmark.owner_profile_picture_url}
                          alt={bookmark.owner_display_name}
                          className="h-9 w-9 rounded-full border border-border object-cover"
                        />
                      ) : (
                        <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-muted text-xs font-semibold text-muted-foreground">
                          {bookmark.owner_display_name.slice(0, 1).toUpperCase()}
                        </span>
                      )}
                      <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                          {bookmark.conversation_title}
                        </p>
                        <p className="mt-1 text-sm font-medium">
                          {bookmark.is_current_user_owner ? "Saved by you" : `Saved by ${bookmark.owner_display_name}`}
                        </p>
                      </div>
                    </div>
                    {bookmark.conversation_summary_short ? (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {bookmark.conversation_summary_short}
                      </p>
                    ) : null}
                    <p className="mt-3 text-sm leading-6">{bookmark.message_preview}</p>
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span>Bookmarked {formatTimestamp(bookmark.created_at)}</span>
                      <span>Message from {formatTimestamp(bookmark.message_created_at)}</span>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Link
                      href={`/chat?conversationId=${encodeURIComponent(bookmark.conversation_id)}&messageId=${encodeURIComponent(bookmark.message_id)}`}
                      className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium transition hover:bg-muted"
                    >
                      Open
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                    {bookmark.is_current_user_owner ? (
                      <button
                        type="button"
                        disabled={deletingMessageId === bookmark.message_id}
                        className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium transition hover:bg-muted disabled:cursor-wait disabled:opacity-60"
                        onClick={() => void removeBookmark(bookmark.message_id)}
                      >
                        <Trash2 className="h-4 w-4" />
                        Remove
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
