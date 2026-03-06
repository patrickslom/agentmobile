"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { getApiBaseUrl } from "@/lib/network-config";
import ToastStack, { type ToastItem, type ToastTone } from "@/components/ui/toast-stack";

type AdminUser = {
  id: string;
  email: string;
  role: "user" | "admin";
  is_active: boolean;
  force_password_reset: boolean;
  created_at: string;
  updated_at: string;
};

type AdminUsersPayload = {
  users?: AdminUser[];
};

type AdminUserPayload = {
  user?: AdminUser;
};

type ErrorPayload = {
  error?: {
    message?: string;
  };
  message?: string;
};

type ResetModalState = {
  user: AdminUser;
  password: string;
  forcePasswordReset: boolean;
};

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

function makeToastId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }
  return parsed.toLocaleString();
}

export default function AdminSettingsPageClient() {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newUserForceReset, setNewUserForceReset] = useState(true);
  const [isCreating, setCreating] = useState(false);
  const [actionUserId, setActionUserId] = useState<string | null>(null);
  const [resetModal, setResetModal] = useState<ResetModalState | null>(null);

  const pushToast = useCallback((tone: ToastTone, title: string, description?: string) => {
    const id = makeToastId("toast");
    setToasts((previous) => [...previous, { id, title, description, tone }]);
    window.setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/admin/users`, {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      });

      if (response.status === 401) {
        router.replace("/login");
        return;
      }

      if (response.status === 403) {
        router.replace("/settings");
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        setPageError(parseErrorMessage(payload, `Unable to load users (${response.status})`));
        return;
      }

      const normalized = ((payload as AdminUsersPayload).users ?? []).slice();
      setUsers(normalized);
    } catch {
      setPageError("Unable to load users right now.");
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, router]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const upsertUser = useCallback((nextUser: AdminUser) => {
    setUsers((previous) => {
      const index = previous.findIndex((row) => row.id === nextUser.id);
      if (index < 0) {
        return [nextUser, ...previous];
      }
      const next = [...previous];
      next[index] = nextUser;
      return next;
    });
  }, []);

  async function onCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isCreating) {
      return;
    }

    setCreating(true);
    try {
      const response = await fetch(`${apiBaseUrl}/admin/users`, {
        method: "POST",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify({
          email: email.trim(),
          password,
          role: "user",
          force_password_reset: newUserForceReset,
        }),
      });

      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      if (response.status === 403) {
        router.replace("/settings");
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      if (!response.ok) {
        pushToast("error", "Create user failed", parseErrorMessage(payload, `Request failed (${response.status})`));
        return;
      }

      const created = (payload as AdminUserPayload).user;
      if (created) {
        upsertUser(created);
      }

      setEmail("");
      setPassword("");
      setNewUserForceReset(true);
      pushToast("success", "User created", "Temporary credentials are ready to share securely.");
    } catch {
      pushToast("error", "Create user failed", "Network error while creating user.");
    } finally {
      setCreating(false);
    }
  }

  const patchUser = useCallback(
    async (userId: string, body: Record<string, unknown>, successTitle: string, successDescription?: string) => {
      setActionUserId(userId);
      try {
        const response = await fetch(`${apiBaseUrl}/admin/users/${encodeURIComponent(userId)}`, {
          method: "PATCH",
          credentials: "include",
          headers: withCsrfHeader({
            "content-type": "application/json",
          }),
          body: JSON.stringify(body),
        });

        if (response.status === 401) {
          router.replace("/login");
          return false;
        }

        if (response.status === 403) {
          router.replace("/settings");
          return false;
        }

        const payload = (await response.json().catch(() => null)) as unknown;
        if (!response.ok) {
          pushToast("error", "Update failed", parseErrorMessage(payload, `Request failed (${response.status})`));
          return false;
        }

        const updated = (payload as AdminUserPayload).user;
        if (updated) {
          upsertUser(updated);
        }

        pushToast("success", successTitle, successDescription);
        return true;
      } catch {
        pushToast("error", "Update failed", "Network error while updating user.");
        return false;
      } finally {
        setActionUserId(null);
      }
    },
    [apiBaseUrl, pushToast, router, upsertUser],
  );

  const onResetPasswordSubmit = useCallback(async () => {
    if (!resetModal || !resetModal.password.trim()) {
      pushToast("error", "Missing password", "Enter a temporary password before submitting.");
      return;
    }

    const userId = resetModal.user.id;
    setActionUserId(userId);
    try {
      const response = await fetch(`${apiBaseUrl}/admin/users/${encodeURIComponent(userId)}/reset-password`, {
        method: "POST",
        credentials: "include",
        headers: withCsrfHeader({
          "content-type": "application/json",
        }),
        body: JSON.stringify({
          password: resetModal.password,
          force_password_reset: resetModal.forcePasswordReset,
        }),
      });

      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      if (response.status === 403) {
        router.replace("/settings");
        return;
      }

      if (response.ok) {
        pushToast("success", "Password reset", "Temporary password has been set for this user.");
        await loadUsers();
        setResetModal(null);
        return;
      }

      if (response.status === 404 || response.status === 405) {
        const patchWorked = await patchUser(
          userId,
          { force_password_reset: resetModal.forcePasswordReset },
          "Force reset flag updated",
          "Backend password reset endpoint is missing, so only force-reset was applied.",
        );

        if (patchWorked) {
          pushToast(
            "info",
            "Missing backend endpoint",
            "`POST /api/admin/users/:id/reset-password` is not implemented yet.",
          );
          setResetModal(null);
        }
        return;
      }

      const payload = (await response.json().catch(() => null)) as unknown;
      pushToast("error", "Password reset failed", parseErrorMessage(payload, `Request failed (${response.status})`));
    } catch {
      pushToast("error", "Password reset failed", "Network error while resetting password.");
    } finally {
      setActionUserId(null);
    }
  }, [apiBaseUrl, loadUsers, patchUser, pushToast, resetModal, router]);

  return (
    <>
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      <section className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        <header className="rounded-xl border border-border bg-muted p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Admin Settings</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Manage user access, account status, and onboarding credentials.
              </p>
            </div>
            <Link
              href="/settings"
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium transition hover:border-foreground"
            >
              Back to settings
            </Link>
          </div>
        </header>

        <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight">Create user</h2>
          <p className="mt-1 text-sm text-muted-foreground">Create a user with a temporary password.</p>

          <form className="mt-4 grid gap-3 sm:grid-cols-3" onSubmit={onCreateUser}>
            <label className="flex flex-col gap-2 text-sm font-medium sm:col-span-1">
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
                placeholder="user@example.com"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium sm:col-span-1">
              Temporary password
              <input
                type="text"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                className="rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
                placeholder="Minimum 8 characters"
              />
            </label>
            <div className="flex flex-col justify-end gap-2 sm:col-span-1">
              <label className="inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newUserForceReset}
                  onChange={(event) => setNewUserForceReset(event.target.checked)}
                  className="h-4 w-4 accent-foreground"
                />
                Force password reset on first login
              </label>
              <button
                type="submit"
                disabled={isCreating}
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? "Creating…" : "Create user"}
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-xl border border-border bg-background p-5 sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight">Users</h2>
          <p className="mt-1 text-sm text-muted-foreground">Email, role, status, and creation date.</p>

          {isLoading ? <p className="mt-4 text-sm text-muted-foreground">Loading users…</p> : null}
          {pageError ? (
            <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
              {pageError}
            </p>
          ) : null}

          {!isLoading && !pageError ? (
            <div className="mt-4 overflow-x-auto rounded-lg border border-border">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="bg-muted text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Email</th>
                    <th className="px-3 py-2">Role</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Created</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {users.map((user) => {
                    const isActioning = actionUserId === user.id;
                    return (
                      <tr key={user.id} className="align-top">
                        <td className="px-3 py-3 font-medium text-foreground">{user.email}</td>
                        <td className="px-3 py-3">
                          <select
                            value={user.role}
                            disabled={isActioning}
                            onChange={(event) => {
                              void patchUser(
                                user.id,
                                { role: event.target.value },
                                "User role updated",
                                `${user.email} is now ${event.target.value}.`,
                              );
                            }}
                            className="rounded-md border border-border bg-muted px-2 py-1 text-sm"
                          >
                            <option value="user">user</option>
                            <option value="admin">admin</option>
                          </select>
                        </td>
                        <td className="px-3 py-3">
                          <span
                            className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${
                              user.is_active
                                ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
                                : "border-zinc-400 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
                            }`}
                          >
                            {user.is_active ? "active" : "disabled"}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-muted-foreground">{formatDate(user.created_at)}</td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              disabled={isActioning}
                              onClick={() =>
                                void patchUser(
                                  user.id,
                                  { is_active: !user.is_active },
                                  user.is_active ? "User disabled" : "User enabled",
                                  `${user.email} is now ${user.is_active ? "disabled" : "enabled"}.`,
                                )
                              }
                              className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {user.is_active ? "Disable" : "Enable"}
                            </button>
                            <button
                              type="button"
                              disabled={isActioning}
                              onClick={() =>
                                setResetModal({
                                  user,
                                  password: "",
                                  forcePasswordReset: true,
                                })
                              }
                              className="rounded-md border border-border px-2 py-1 text-xs font-medium transition hover:border-foreground disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Reset password
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {users.length === 0 ? (
                    <tr>
                      <td className="px-3 py-4 text-sm text-muted-foreground" colSpan={5}>
                        No users found.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </section>

      {resetModal ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl border border-border bg-background p-5 shadow-lg">
            <h2 className="text-lg font-semibold tracking-tight">Reset password</h2>
            <p className="mt-1 text-sm text-muted-foreground">Set a temporary password for {resetModal.user.email}.</p>

            <label className="mt-4 flex flex-col gap-2 text-sm font-medium">
              Temporary password
              <input
                type="text"
                value={resetModal.password}
                onChange={(event) =>
                  setResetModal((previous) =>
                    previous
                      ? {
                          ...previous,
                          password: event.target.value,
                        }
                      : previous,
                  )
                }
                minLength={8}
                className="rounded-lg border border-border bg-muted px-3 py-2 text-sm outline-none transition focus:border-foreground"
              />
            </label>

            <label className="mt-3 inline-flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={resetModal.forcePasswordReset}
                onChange={(event) =>
                  setResetModal((previous) =>
                    previous
                      ? {
                          ...previous,
                          forcePasswordReset: event.target.checked,
                        }
                      : previous,
                  )
                }
                className="h-4 w-4 accent-foreground"
              />
              Force reset on next login
            </label>

            <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
              Backend currently lacks a dedicated reset endpoint, so this flow will show a warning and only apply force-reset fallback.
            </p>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm"
                onClick={() => setResetModal(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background"
                onClick={() => void onResetPasswordSubmit()}
              >
                Apply reset
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
