"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { getApiBaseUrl } from "@/lib/network-config";
import ToastStack, { type ToastItem, type ToastTone } from "@/components/ui/toast-stack";

type ConversationItem = {
  id: string;
  title: string;
  updatedAt: string | null;
};

type ApiConversation = {
  id?: string;
  title?: string | null;
  updated_at?: string;
  updatedAt?: string;
  created_at?: string;
  createdAt?: string;
};

type HeartbeatRun = {
  id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error_text: string | null;
  created_at: string;
};

type HeartbeatJob = {
  id: string;
  conversation_id: string;
  instruction_file_path: string;
  interval_minutes: number;
  next_run_at: string;
  last_run_at: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  is_archived: boolean;
  runs: HeartbeatRun[];
};

type HeartbeatJobsPayload = {
  heartbeat_jobs?: HeartbeatJob[];
};

type HeartbeatJobPayload = {
  heartbeat_job?: HeartbeatJob;
};

type ErrorPayload = {
  error?: {
    message?: string;
  };
  message?: string;
};

type EditJobState = {
  id: string;
  instructionFilePath: string;
  intervalMinutes: number;
  enabled: boolean;
};

type RunsModalState = {
  jobId: string;
  jobName: string;
  runs: HeartbeatRun[];
};

type DeleteJobModalState = {
  job: HeartbeatJob;
  jobName: string;
};

const INTERVAL_PRESETS = [5, 10, 15, 30, 60] as const;

function parseErrorMessage(raw: unknown, fallback: string): string {
  if (!raw || typeof raw !== "object") {
    return fallback;
  }

  const payload = raw as ErrorPayload;
  const message = payload.error?.message ?? payload.message;
  if (typeof message !== "string" || !message.trim()) {
    return fallback;
  }

  return message;
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

function makeToastId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

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

function formatDateTime(value: string | null): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

function jobNameFromPath(path: string, fallbackId: string): string {
  const trimmed = path.trim();
  if (!trimmed) {
    return `Job ${fallbackId.slice(0, 8)}`;
  }

  const segments = trimmed.split("/").filter(Boolean);
  if (segments.length === 0) {
    return trimmed;
  }

  return segments[segments.length - 1] ?? trimmed;
}

function findLatestRun(job: HeartbeatJob): HeartbeatRun | null {
  if (!Array.isArray(job.runs) || job.runs.length === 0) {
    return null;
  }

  return job.runs[0] ?? null;
}

function truncateLabel(value: string, maxLength: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }

  return `${trimmed.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

export default function HeartbeatJobsPageClient() {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const [jobs, setJobs] = useState<HeartbeatJob[]>([]);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [isLoadingJobs, setLoadingJobs] = useState(true);
  const [isLoadingConversations, setLoadingConversations] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const [createConversationSearch, setCreateConversationSearch] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [instructionFilePath, setInstructionFilePath] = useState("");
  const [intervalMinutes, setIntervalMinutes] = useState<number>(10);
  const [enabled, setEnabled] = useState(true);
  const [isCreating, setCreating] = useState(false);

  const [editState, setEditState] = useState<EditJobState | null>(null);
  const [isSavingEdit, setSavingEdit] = useState(false);
  const [isDeletingId, setDeletingId] = useState<string | null>(null);
  const [runsModal, setRunsModal] = useState<RunsModalState | null>(null);
  const [deleteJobModal, setDeleteJobModal] = useState<DeleteJobModalState | null>(null);

  const pushToast = useCallback((tone: ToastTone, title: string, description?: string) => {
    const id = makeToastId("toast");
    setToasts((previous) => [...previous, { id, tone, title, description }]);
    window.setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    setPageError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/heartbeat-jobs`, {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        setPageError(parseErrorMessage(payload, `Unable to load heartbeat jobs (${response.status})`));
        return;
      }

      const nextJobs = ((payload as HeartbeatJobsPayload).heartbeat_jobs ?? []).slice();
      setJobs(nextJobs);
    } catch {
      setPageError("Unable to load heartbeat jobs right now.");
    } finally {
      setLoadingJobs(false);
    }
  }, [apiBaseUrl, router]);

  const loadConversations = useCallback(async () => {
    setLoadingConversations(true);
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

      const payload = (await response.json()) as unknown;
      if (!response.ok) {
        throw new Error(`Unable to load conversations (${response.status})`);
      }

      const normalized = extractConversations(payload)
        .map(normalizeConversation)
        .filter((item): item is ConversationItem => Boolean(item));

      setConversations(normalized);
      if (normalized.length > 0) {
        setSelectedConversationId((previous) => previous || normalized[0].id);
      }
    } catch {
      pushToast("error", "Unable to load conversations", "Create/edit forms need conversations to continue.");
    } finally {
      setLoadingConversations(false);
    }
  }, [apiBaseUrl, pushToast, router]);

  useEffect(() => {
    void Promise.all([loadJobs(), loadConversations()]);
  }, [loadConversations, loadJobs]);

  const filteredConversations = useMemo(() => {
    const query = createConversationSearch.trim().toLowerCase();
    if (!query) {
      return conversations;
    }

    return conversations.filter((conversation) => {
      const title = conversation.title.toLowerCase();
      return title.includes(query) || conversation.id.toLowerCase().includes(query);
    });
  }, [conversations, createConversationSearch]);

  async function onCreateJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isCreating) {
      return;
    }

    if (!selectedConversationId) {
      pushToast("error", "Conversation required", "Select a conversation before creating a heartbeat job.");
      return;
    }

    if (!instructionFilePath.trim()) {
      pushToast("error", "Markdown path required", "Provide an absolute markdown file path.");
      return;
    }

    setCreating(true);
    try {
      const response = await fetch(`${apiBaseUrl}/heartbeat-jobs`, {
        method: "POST",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify({
          conversation_id: selectedConversationId,
          instruction_file_path: instructionFilePath.trim(),
          interval_minutes: intervalMinutes,
          enabled,
        }),
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        pushToast("error", "Create heartbeat job failed", parseErrorMessage(payload, `Request failed (${response.status})`));
        return;
      }

      const created = (payload as HeartbeatJobPayload).heartbeat_job;
      if (created) {
        setJobs((previous) => [...previous, { ...created, runs: [] }]);
      }

      setInstructionFilePath("");
      setIntervalMinutes(10);
      setEnabled(true);
      pushToast("success", "Heartbeat job created", "The job is now scheduled and visible in the list.");
      await loadJobs();
    } catch {
      pushToast("error", "Create heartbeat job failed", "Network error while creating heartbeat job.");
    } finally {
      setCreating(false);
    }
  }

  const onSaveEdit = useCallback(async () => {
    if (!editState || isSavingEdit) {
      return;
    }

    if (!editState.instructionFilePath.trim()) {
      pushToast("error", "Markdown path required", "Provide an absolute markdown file path.");
      return;
    }

    setSavingEdit(true);
    try {
      const response = await fetch(`${apiBaseUrl}/heartbeat-jobs/${encodeURIComponent(editState.id)}`, {
        method: "PATCH",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify({
          instruction_file_path: editState.instructionFilePath.trim(),
          interval_minutes: editState.intervalMinutes,
          enabled: editState.enabled,
        }),
      });

      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        pushToast("error", "Update heartbeat job failed", parseErrorMessage(payload, `Request failed (${response.status})`));
        return;
      }

      pushToast("success", "Heartbeat job updated");
      setEditState(null);
      await loadJobs();
    } catch {
      pushToast("error", "Update heartbeat job failed", "Network error while updating heartbeat job.");
    } finally {
      setSavingEdit(false);
    }
  }, [apiBaseUrl, editState, isSavingEdit, loadJobs, pushToast, router]);

  const onDeleteJob = useCallback(
    async (job: HeartbeatJob) => {
      if (isDeletingId) {
        return;
      }

      setDeletingId(job.id);
      try {
        const response = await fetch(`${apiBaseUrl}/heartbeat-jobs/${encodeURIComponent(job.id)}`, {
          method: "DELETE",
          credentials: "include",
          headers: withCsrfHeader(),
        });

        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }

        const payload = (await response.json().catch(() => null)) as unknown;
        if (!response.ok) {
          pushToast("error", "Delete heartbeat job failed", parseErrorMessage(payload, `Request failed (${response.status})`));
          return;
        }

        setJobs((previous) => previous.filter((item) => item.id !== job.id));
        pushToast("success", "Heartbeat job deleted");
      } catch {
        pushToast("error", "Delete heartbeat job failed", "Network error while deleting heartbeat job.");
      } finally {
        setDeletingId(null);
      }
    },
    [apiBaseUrl, isDeletingId, pushToast, router],
  );

  const onConfirmDeleteJob = useCallback(async () => {
    if (!deleteJobModal) {
      return;
    }

    await onDeleteJob(deleteJobModal.job);
    setDeleteJobModal(null);
  }, [deleteJobModal, onDeleteJob]);

  return (
    <>
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      <section className="mx-auto w-full max-w-6xl min-w-0 space-y-6 overflow-x-hidden px-4 py-6 sm:px-6 sm:py-8">
        <header className="min-w-0 overflow-hidden rounded-xl border border-border bg-muted p-5 sm:p-6">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h1 className="text-2xl font-semibold tracking-tight">Heartbeats</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Schedule markdown instruction files to run in selected conversations.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void loadJobs()}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium transition hover:border-foreground"
              >
                Refresh jobs
              </button>
            </div>
          </div>
        </header>

        <section className="min-w-0 overflow-hidden rounded-xl border border-border bg-background p-5 sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight">Create job</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Choose a conversation, set markdown path, interval preset, and enabled state.
          </p>

          <form className="mt-4 grid gap-4" onSubmit={onCreateJob}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-2 text-sm font-medium">
                Search conversation
                <input
                  type="search"
                  value={createConversationSearch}
                  onChange={(event) => setCreateConversationSearch(event.target.value)}
                  placeholder="Search by title or conversation ID"
                  className="w-full min-w-0 rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium">
                Conversation
                <select
                  value={selectedConversationId}
                  onChange={(event) => setSelectedConversationId(event.target.value)}
                  disabled={isLoadingConversations || filteredConversations.length === 0}
                  className="w-full min-w-0 rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {filteredConversations.length === 0 ? (
                    <option value="">No conversations found</option>
                  ) : null}
                  {filteredConversations.map((conversation) => (
                    <option
                      key={conversation.id}
                      value={conversation.id}
                      title={conversation.title}
                    >
                      {truncateLabel(conversation.title, 28)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="flex flex-col gap-2 text-sm font-medium">
              Markdown instruction file path
              <input
                type="text"
                value={instructionFilePath}
                onChange={(event) => setInstructionFilePath(event.target.value)}
                required
                placeholder="/abs/path/to/instructions.md"
                className="w-full min-w-0 rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <fieldset className="rounded-lg border border-border bg-muted p-3">
                <legend className="px-1 text-sm font-medium text-foreground">Interval presets (minutes)</legend>
                <div className="mt-2 flex flex-wrap gap-2">
                  {INTERVAL_PRESETS.map((preset) => {
                    const isSelected = intervalMinutes === preset;
                    return (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => setIntervalMinutes(preset)}
                        className={`rounded-md border px-3 py-1.5 text-sm font-medium transition ${
                          isSelected
                            ? "border-foreground bg-background text-foreground"
                            : "border-border text-muted-foreground hover:border-foreground"
                        }`}
                      >
                        {preset}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <label className="inline-flex items-center gap-2 self-end rounded-lg border border-border bg-muted px-3 py-2 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(event) => setEnabled(event.target.checked)}
                  className="h-4 w-4 accent-foreground"
                />
                Enabled
              </label>
            </div>

            <div>
              <button
                type="submit"
                disabled={isCreating || isLoadingConversations || filteredConversations.length === 0}
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? "Creating…" : "Create heartbeat job"}
              </button>
            </div>
          </form>
        </section>

        <section className="min-w-0 overflow-hidden rounded-xl border border-border bg-background p-5 sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight">Jobs</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Compact list with latest run status/time and quick edit/delete actions.
          </p>

          {isLoadingJobs ? <p className="mt-4 text-sm text-muted-foreground">Loading heartbeat jobs…</p> : null}
          {pageError ? (
            <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
              {pageError}
            </p>
          ) : null}

          {!isLoadingJobs && !pageError ? (
            <>
              <div className="mt-4 grid gap-3 md:hidden">
                {jobs.map((job) => {
                  const latestRun = findLatestRun(job);
                  const isDeleting = isDeletingId === job.id;
                  const conversationTitle = conversations.find((row) => row.id === job.conversation_id)?.title;
                  return (
                    <article key={job.id} className="rounded-xl border border-border bg-muted/35 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="break-words font-medium text-foreground">
                            {jobNameFromPath(job.instruction_file_path, job.id)}
                          </p>
                          <p className="mt-1 break-all text-xs text-muted-foreground">
                            {job.instruction_file_path}
                          </p>
                        </div>
                        <span
                          className={`shrink-0 rounded-full border px-2 py-0.5 text-xs ${
                            job.enabled
                              ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100"
                              : "border-zinc-400 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
                          }`}
                        >
                          {job.enabled ? "enabled" : "disabled"}
                        </span>
                      </div>

                      <div className="mt-3 grid gap-2 text-xs text-muted-foreground">
                        <p className="break-words">
                          Conversation: {conversationTitle ? conversationTitle : job.conversation_id}
                        </p>
                        <p>Every {job.interval_minutes} min</p>
                        <p>Next: {formatDateTime(job.next_run_at)}</p>
                        <p>Last run: {latestRun ? formatDateTime(latestRun.finished_at ?? latestRun.started_at ?? latestRun.created_at) : "No runs yet"}</p>
                        {latestRun ? (
                          <p className="break-words">
                            Latest status: <span className="font-medium text-foreground">{latestRun.status}</span>
                          </p>
                        ) : null}
                        {latestRun?.error_text ? (
                          <p className="break-words text-red-700 dark:text-red-300">{latestRun.error_text}</p>
                        ) : null}
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            setEditState({
                              id: job.id,
                              instructionFilePath: job.instruction_file_path,
                              intervalMinutes: job.interval_minutes,
                              enabled: job.enabled,
                            })
                          }
                          className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setRunsModal({
                              jobId: job.id,
                              jobName: jobNameFromPath(job.instruction_file_path, job.id),
                              runs: job.runs,
                            })
                          }
                          className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground"
                        >
                          View runs
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setDeleteJobModal({
                              job,
                              jobName: jobNameFromPath(job.instruction_file_path, job.id),
                            })
                          }
                          disabled={isDeleting}
                          className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 transition hover:border-red-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-800 dark:text-red-300"
                        >
                          {isDeleting ? "Deleting…" : "Delete"}
                        </button>
                      </div>
                    </article>
                  );
                })}
                {jobs.length === 0 ? (
                  <div className="rounded-xl border border-border bg-muted/35 px-4 py-5 text-sm text-muted-foreground">
                    No heartbeat jobs yet.
                  </div>
                ) : null}
              </div>

              <div className="mt-4 hidden overflow-x-auto rounded-lg border border-border md:block">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="bg-muted text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Job name</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Schedule</th>
                    <th className="px-3 py-2">Last run</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {jobs.map((job) => {
                    const latestRun = findLatestRun(job);
                    const isDeleting = isDeletingId === job.id;
                    const conversationTitle = conversations.find((row) => row.id === job.conversation_id)?.title;
                    return (
                      <tr key={job.id} className="align-top">
                        <td className="px-3 py-3">
                          <p className="font-medium text-foreground">{jobNameFromPath(job.instruction_file_path, job.id)}</p>
                          <p className="text-xs text-muted-foreground">{job.instruction_file_path}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {conversationTitle ? `${conversationTitle}` : job.conversation_id}
                          </p>
                        </td>
                        <td className="px-3 py-3">
                          <span
                            className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${
                              job.enabled
                                ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100"
                                : "border-zinc-400 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
                            }`}
                          >
                            {job.enabled ? "enabled" : "disabled"}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">
                          <p>Every {job.interval_minutes} min</p>
                          <p>Next: {formatDateTime(job.next_run_at)}</p>
                        </td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">
                          {latestRun ? (
                            <>
                              <p className="font-medium text-foreground">{latestRun.status}</p>
                              <p>{formatDateTime(latestRun.finished_at ?? latestRun.started_at ?? latestRun.created_at)}</p>
                              {latestRun.error_text ? (
                                <p className="mt-1 max-w-xs truncate text-red-700 dark:text-red-300" title={latestRun.error_text}>
                                  {latestRun.error_text}
                                </p>
                              ) : null}
                            </>
                          ) : (
                            <p>No runs yet</p>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                setEditState({
                                  id: job.id,
                                  instructionFilePath: job.instruction_file_path,
                                  intervalMinutes: job.interval_minutes,
                                  enabled: job.enabled,
                                })
                              }
                              className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setRunsModal({
                                  jobId: job.id,
                                  jobName: jobNameFromPath(job.instruction_file_path, job.id),
                                  runs: job.runs,
                                })
                              }
                              className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground"
                            >
                              View runs
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setDeleteJobModal({
                                  job,
                                  jobName: jobNameFromPath(job.instruction_file_path, job.id),
                                })
                              }
                              disabled={isDeleting}
                              className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 transition hover:border-red-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-800 dark:text-red-300"
                            >
                              {isDeleting ? "Deleting…" : "Delete"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {jobs.length === 0 ? (
                    <tr>
                      <td className="px-3 py-4 text-sm text-muted-foreground" colSpan={5}>
                        No heartbeat jobs yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
              </div>
            </>
          ) : null}
        </section>
      </section>

      {editState ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md overflow-hidden rounded-xl border border-border bg-background p-5 shadow-lg">
            <h2 className="text-lg font-semibold tracking-tight">Edit heartbeat job</h2>
            <p className="mt-1 text-sm text-muted-foreground">Update markdown path, interval preset, and enabled state.</p>

            <label className="mt-4 flex flex-col gap-2 text-sm font-medium">
              Markdown instruction file path
              <input
                type="text"
                value={editState.instructionFilePath}
                onChange={(event) =>
                  setEditState((previous) =>
                    previous
                      ? {
                          ...previous,
                          instructionFilePath: event.target.value,
                        }
                      : previous,
                  )
                }
                className="w-full min-w-0 rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
              />
            </label>

            <fieldset className="mt-3 rounded-lg border border-border bg-muted p-3">
              <legend className="px-1 text-sm font-medium text-foreground">Interval presets (minutes)</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {INTERVAL_PRESETS.map((preset) => {
                  const isSelected = editState.intervalMinutes === preset;
                  return (
                    <button
                      key={preset}
                      type="button"
                      onClick={() =>
                        setEditState((previous) =>
                          previous
                            ? {
                                ...previous,
                                intervalMinutes: preset,
                              }
                            : previous,
                        )
                      }
                      className={`rounded-md border px-3 py-1.5 text-sm font-medium transition ${
                        isSelected
                          ? "border-foreground bg-background text-foreground"
                          : "border-border text-muted-foreground hover:border-foreground"
                      }`}
                    >
                      {preset}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <label className="mt-3 inline-flex items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                checked={editState.enabled}
                onChange={(event) =>
                  setEditState((previous) =>
                    previous
                      ? {
                          ...previous,
                          enabled: event.target.checked,
                        }
                      : previous,
                  )
                }
                className="h-4 w-4 accent-foreground"
              />
              Enabled
            </label>

            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm"
                onClick={() => setEditState(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background"
                onClick={() => void onSaveEdit()}
                disabled={isSavingEdit}
              >
                {isSavingEdit ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {runsModal ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-2xl overflow-hidden rounded-xl border border-border bg-background p-5 shadow-lg">
            <h2 className="text-lg font-semibold tracking-tight">Run history: {runsModal.jobName}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Showing the latest runs returned by the API (status, timestamps, and errors).
            </p>

            <div className="mt-4 max-h-[50vh] overflow-auto rounded-lg border border-border">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="bg-muted text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Started</th>
                    <th className="px-3 py-2">Finished</th>
                    <th className="px-3 py-2">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runsModal.runs.map((run) => (
                    <tr key={run.id}>
                      <td className="px-3 py-2 font-medium text-foreground">{run.status}</td>
                      <td className="px-3 py-2 text-muted-foreground">{formatDateTime(run.started_at)}</td>
                      <td className="px-3 py-2 text-muted-foreground">{formatDateTime(run.finished_at)}</td>
                      <td className="px-3 py-2 text-muted-foreground">{run.error_text || "-"}</td>
                    </tr>
                  ))}
                  {runsModal.runs.length === 0 ? (
                    <tr>
                      <td className="px-3 py-3 text-muted-foreground" colSpan={4}>
                        No run history yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm"
                onClick={() => setRunsModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteJobModal ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md overflow-hidden rounded-xl border border-border bg-background p-5 shadow-lg">
            <h2 className="text-lg font-semibold tracking-tight">Delete heartbeat job?</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              This will archive <span className="font-medium text-foreground">{deleteJobModal.jobName}</span> and stop future runs.
            </p>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm"
                onClick={() => setDeleteJobModal(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background"
                onClick={() => void onConfirmDeleteJob()}
              >
                Confirm delete
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
