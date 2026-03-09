"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getApiBaseUrl } from "@/lib/network-config";
import ToastStack, { type ToastItem, type ToastTone } from "@/components/ui/toast-stack";

type WarningPayload = {
  id: string;
  title: string;
  content: string;
  severity: "info" | "warning" | "critical";
  metadata?: Record<string, unknown>;
};

type SharedWorkspaceWarning = {
  enabled: boolean;
  content: string;
};

type SettingsResponse = {
  execution_mode_default: "regular" | "yolo";
  execution_mode_options: string[];
  upload_limit_mb_default: number;
  heartbeat_enabled_default: boolean;
  heartbeat_cap_default: number;
  heartbeat_unlimited_default: boolean;
  theme_preference: "light" | "dark";
  theme_preference_source: "user" | "default";
  theme_options: string[];
  destructive_operations_warning: WarningPayload;
  yolo_mode_warning: WarningPayload;
  shared_workspace_warning: SharedWorkspaceWarning;
  warnings: WarningPayload[];
};

type SettingsApiPayload = {
  settings?: SettingsResponse;
};

type ErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
  code?: string;
  message?: string;
};

type SettingsPatchBody = {
  execution_mode_default?: "regular" | "yolo";
  upload_limit_mb_default?: number;
  heartbeat_enabled_default?: boolean;
  heartbeat_cap_default?: number;
  heartbeat_unlimited_default?: boolean;
  theme_preference?: "light" | "dark";
};

type SettingsPageClientProps = {
  isAdmin: boolean;
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

function dateToastId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function warningCardClasses(severity: WarningPayload["severity"]): string {
  if (severity === "critical") {
    return "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100";
  }
  if (severity === "warning") {
    return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100";
  }
  return "border-zinc-300 bg-muted text-foreground dark:border-zinc-700";
}

export default function SettingsPageClient({ isAdmin }: SettingsPageClientProps) {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [draft, setDraft] = useState<SettingsResponse | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [isSaving, setSaving] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showYoloConfirm, setShowYoloConfirm] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const pushToast = useCallback((tone: ToastTone, title: string, description?: string) => {
    const id = dateToastId("toast");
    setToasts((previous) => [...previous, { id, tone, title, description }]);
    window.setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadSettings = async () => {
      setLoading(true);
      setPageError(null);
      try {
        const response = await fetch(`${apiBaseUrl}/settings`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });

        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to load settings (${response.status})`);
        }

        const payload = (await response.json()) as SettingsApiPayload;
        if (!payload.settings) {
          throw new Error("Settings payload is missing");
        }

        if (!mounted) {
          return;
        }

        setSettings(payload.settings);
        setDraft(payload.settings);
      } catch (error) {
        if (!mounted) {
          return;
        }
        const fallback = "Unable to load settings right now.";
        const message = error instanceof Error && error.message ? error.message : fallback;
        setPageError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    void loadSettings();

    return () => {
      mounted = false;
    };
  }, [apiBaseUrl, router]);

  const hasUnsavedChanges = useMemo(() => {
    if (!draft || !settings) {
      return false;
    }

    return (
      draft.execution_mode_default !== settings.execution_mode_default ||
      draft.upload_limit_mb_default !== settings.upload_limit_mb_default ||
      draft.heartbeat_enabled_default !== settings.heartbeat_enabled_default ||
      draft.heartbeat_cap_default !== settings.heartbeat_cap_default ||
      draft.heartbeat_unlimited_default !== settings.heartbeat_unlimited_default ||
      draft.theme_preference !== settings.theme_preference
    );
  }, [draft, settings]);

  const onExecutionModeChange = useCallback(
    (value: "regular" | "yolo") => {
      if (!draft) {
        return;
      }
      if (value === "yolo" && draft.execution_mode_default !== "yolo") {
        setShowYoloConfirm(true);
        return;
      }
      setDraft({
        ...draft,
        execution_mode_default: value,
      });
    },
    [draft],
  );

  const applyPatch = useCallback(async () => {
    if (!draft || !settings) {
      return;
    }

    const payload: SettingsPatchBody = {};

    if (draft.execution_mode_default !== settings.execution_mode_default) {
      payload.execution_mode_default = draft.execution_mode_default;
    }
    if (draft.upload_limit_mb_default !== settings.upload_limit_mb_default) {
      payload.upload_limit_mb_default = draft.upload_limit_mb_default;
    }
    if (draft.heartbeat_enabled_default !== settings.heartbeat_enabled_default) {
      payload.heartbeat_enabled_default = draft.heartbeat_enabled_default;
    }
    if (draft.heartbeat_cap_default !== settings.heartbeat_cap_default) {
      payload.heartbeat_cap_default = draft.heartbeat_cap_default;
    }
    if (draft.heartbeat_unlimited_default !== settings.heartbeat_unlimited_default) {
      payload.heartbeat_unlimited_default = draft.heartbeat_unlimited_default;
    }
    if (draft.theme_preference !== settings.theme_preference) {
      payload.theme_preference = draft.theme_preference;
    }

    const globalFields: Array<keyof SettingsPatchBody> = [
      "execution_mode_default",
      "upload_limit_mb_default",
      "heartbeat_enabled_default",
      "heartbeat_cap_default",
      "heartbeat_unlimited_default",
    ];

    if (!isAdmin) {
      let filteredAny = false;
      for (const field of globalFields) {
        if (field in payload) {
          delete payload[field];
          filteredAny = true;
        }
      }
      if (filteredAny) {
        pushToast(
          "info",
          "Admin access required",
          "Execution, heartbeat, and upload defaults require an admin account.",
        );
      }
    }

    if (Object.keys(payload).length === 0) {
      pushToast("info", "No changes to save");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${apiBaseUrl}/settings`, {
        method: "PATCH",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        router.replace("/login");
        return;
      }

      const responseJson = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        pushToast(
          "error",
          "Unable to save settings",
          parseErrorMessage(responseJson, `Request failed (${response.status})`),
        );
        return;
      }

      const nextPayload = responseJson as SettingsApiPayload;
      if (!nextPayload.settings) {
        pushToast("error", "Unable to save settings", "Updated settings payload was missing.");
        return;
      }

      setSettings(nextPayload.settings);
      setDraft(nextPayload.settings);
      pushToast("success", "Settings saved", "Your preferences were updated successfully.");
    } catch {
      pushToast("error", "Unable to save settings", "Network error while saving settings.");
    } finally {
      setSaving(false);
    }
  }, [apiBaseUrl, draft, isAdmin, pushToast, router, settings]);

  const heartbeatCapMode = draft?.heartbeat_unlimited_default ? "unlimited" : "limited";

  return (
    <>
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      <section className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        <header className="rounded-xl border border-border bg-muted p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Configure appearance, execution defaults, upload limits, and safety warnings.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/settings/heartbeats"
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium transition hover:border-foreground"
              >
                Open heartbeat jobs
              </Link>
              {isAdmin ? (
                <Link
                  href="/settings/admin"
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium transition hover:border-foreground"
                >
                  Open admin settings
                </Link>
              ) : null}
            </div>
          </div>
        </header>

        {!isAdmin ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
            Global defaults require an admin account. You can still change your own theme preference.
          </div>
        ) : null}

        {isLoading ? <p className="text-sm text-muted-foreground">Loading settings…</p> : null}
        {pageError ? (
          <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
            {pageError}
          </div>
        ) : null}

        {draft ? (
          <>
            <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
              <h2 className="text-lg font-semibold tracking-tight">Appearance</h2>
              <p className="mt-1 text-sm text-muted-foreground">Choose your default theme for the interface.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {draft.theme_options.map((themeOption) => {
                  const isSelected = draft.theme_preference === themeOption;
                  return (
                    <button
                      key={themeOption}
                      type="button"
                      onClick={() =>
                        setDraft((previous) =>
                          previous
                            ? {
                                ...previous,
                                theme_preference: themeOption as "light" | "dark",
                              }
                            : previous,
                        )
                      }
                      className={`rounded-lg border px-4 py-3 text-left text-sm font-medium transition ${
                        isSelected
                          ? "border-foreground bg-muted text-foreground"
                          : "border-border text-muted-foreground hover:border-foreground"
                      }`}
                    >
                      {themeOption[0]?.toUpperCase()}
                      {themeOption.slice(1)}
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
              <h2 className="text-lg font-semibold tracking-tight">Execution</h2>
              <p className="mt-1 text-sm text-muted-foreground">Select the default execution mode for new chats.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {draft.execution_mode_options.map((mode) => {
                  const isSelected = draft.execution_mode_default === mode;
                  return (
                    <button
                      key={mode}
                      type="button"
                      disabled={!isAdmin || isSaving}
                      onClick={() => onExecutionModeChange(mode as "regular" | "yolo")}
                      className={`rounded-lg border px-4 py-3 text-left text-sm font-medium transition ${
                        isSelected
                          ? "border-foreground bg-muted text-foreground"
                          : "border-border text-muted-foreground hover:border-foreground"
                      } disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      {mode === "regular" ? "Regular" : "YOLO"}
                    </button>
                  );
                })}
              </div>
              {draft.execution_mode_default === "yolo" ? (
                <article
                  className={`mt-4 rounded-lg border px-4 py-3 text-sm ${warningCardClasses(
                    draft.yolo_mode_warning.severity,
                  )}`}
                >
                  <p className="font-semibold">{draft.yolo_mode_warning.title}</p>
                  <p className="mt-1 text-xs leading-relaxed opacity-90">{draft.yolo_mode_warning.content}</p>
                </article>
              ) : null}
            </section>

            <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
              <h2 className="text-lg font-semibold tracking-tight">Uploads</h2>
              <p className="mt-1 text-sm text-muted-foreground">Set max file size per upload (MB).</p>
              <label className="mt-4 flex max-w-xs flex-col gap-2 text-sm font-medium text-foreground">
                Upload limit (MB)
                <input
                  type="number"
                  min={1}
                  value={draft.upload_limit_mb_default}
                  onChange={(event) => {
                    const parsed = Number.parseInt(event.target.value, 10);
                    if (Number.isNaN(parsed) || parsed < 1) {
                      return;
                    }
                    setDraft((previous) =>
                      previous
                        ? {
                            ...previous,
                            upload_limit_mb_default: parsed,
                          }
                        : previous,
                    );
                  }}
                  disabled={!isAdmin || isSaving}
                  className="rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-foreground disabled:cursor-not-allowed disabled:opacity-50"
                />
              </label>
            </section>

            <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
              <h2 className="text-lg font-semibold tracking-tight">Heartbeats</h2>
              <p className="mt-1 text-sm text-muted-foreground">Set default heartbeat behavior and cap controls.</p>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="flex items-center justify-between gap-3 rounded-lg border border-border bg-muted px-4 py-3 text-sm">
                  <span className="font-medium">Enable by default</span>
                  <input
                    type="checkbox"
                    checked={draft.heartbeat_enabled_default}
                    onChange={(event) =>
                      setDraft((previous) =>
                        previous
                          ? {
                              ...previous,
                              heartbeat_enabled_default: event.target.checked,
                            }
                          : previous,
                      )
                    }
                    disabled={!isAdmin || isSaving}
                    className="h-4 w-4 accent-foreground"
                  />
                </label>

                <div className="rounded-lg border border-border bg-muted px-4 py-3">
                  <p className="text-sm font-medium text-foreground">Heartbeat cap mode</p>
                  <div className="mt-2 flex flex-wrap gap-4 text-sm">
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="radio"
                        checked={heartbeatCapMode === "limited"}
                        onChange={() =>
                          setDraft((previous) =>
                            previous
                              ? {
                                  ...previous,
                                  heartbeat_unlimited_default: false,
                                  heartbeat_cap_default:
                                    previous.heartbeat_cap_default > 0
                                      ? previous.heartbeat_cap_default
                                      : 10,
                                }
                              : previous,
                          )
                        }
                        disabled={!isAdmin || isSaving}
                        className="h-4 w-4 accent-foreground"
                      />
                      Limited
                    </label>
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="radio"
                        checked={heartbeatCapMode === "unlimited"}
                        onChange={() =>
                          setDraft((previous) =>
                            previous
                              ? {
                                  ...previous,
                                  heartbeat_unlimited_default: true,
                                }
                              : previous,
                          )
                        }
                        disabled={!isAdmin || isSaving}
                        className="h-4 w-4 accent-foreground"
                      />
                      Unlimited
                    </label>
                  </div>
                </div>
              </div>

              <label className="mt-4 flex max-w-xs flex-col gap-2 text-sm font-medium text-foreground">
                Heartbeat cap (default 10)
                <input
                  type="number"
                  min={1}
                  value={draft.heartbeat_cap_default}
                  onChange={(event) => {
                    const parsed = Number.parseInt(event.target.value, 10);
                    if (Number.isNaN(parsed) || parsed < 1) {
                      return;
                    }
                    setDraft((previous) =>
                      previous
                        ? {
                            ...previous,
                            heartbeat_cap_default: parsed,
                            heartbeat_unlimited_default: false,
                          }
                        : previous,
                    );
                  }}
                  disabled={!isAdmin || isSaving || heartbeatCapMode === "unlimited"}
                  className="rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-foreground disabled:cursor-not-allowed disabled:opacity-50"
                />
              </label>
            </section>

            <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
              <h2 className="text-lg font-semibold tracking-tight">Safety</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Review warnings before enabling higher-risk operation modes.
              </p>

              <div className="mt-4 space-y-3">
                {draft.warnings.map((warning) => (
                  <article
                    key={warning.id}
                    className={`rounded-lg border px-4 py-3 text-sm ${warningCardClasses(warning.severity)}`}
                  >
                    <p className="font-semibold">{warning.title}</p>
                    <p className="mt-1 text-xs leading-relaxed opacity-90">{warning.content}</p>
                  </article>
                ))}

                {draft.shared_workspace_warning.enabled ? (
                  <article className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
                    <p className="font-semibold">Shared Workspace Notice</p>
                    <p className="mt-1 text-xs leading-relaxed">{draft.shared_workspace_warning.content}</p>
                  </article>
                ) : null}
              </div>
            </section>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void applyPatch()}
                disabled={isSaving || !hasUnsavedChanges}
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? "Saving…" : "Save settings"}
              </button>
              <button
                type="button"
                onClick={() => setDraft(settings)}
                disabled={isSaving || !hasUnsavedChanges}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:border-foreground disabled:cursor-not-allowed disabled:opacity-60"
              >
                Reset changes
              </button>
            </div>
          </>
        ) : null}
      </section>

      {showYoloConfirm ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl border border-border bg-background p-5 shadow-lg">
            <h2 className="text-lg font-semibold tracking-tight">Enable YOLO mode?</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              YOLO mode reduces confirmation safeguards and increases risk of destructive actions.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm"
                onClick={() => setShowYoloConfirm(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background"
                onClick={() => {
                  setDraft((previous) =>
                    previous
                      ? {
                          ...previous,
                          execution_mode_default: "yolo",
                        }
                      : previous,
                  );
                  setShowYoloConfirm(false);
                }}
              >
                Confirm YOLO
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
