"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const GENERIC_AUTH_ERROR = "Invalid email or password";
const LOCKOUT_FALLBACK_ERROR = "Too many attempts. Try again later.";

type LoginErrorResponse = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
};

function getRetryMinutes(details: Record<string, unknown>): number | null {
  const minuteCandidates = [
    details.retry_after_minutes,
    details.retry_minutes,
    details.minutes,
  ];
  for (const candidate of minuteCandidates) {
    if (typeof candidate === "number" && candidate > 0) {
      return Math.ceil(candidate);
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed > 0) {
        return Math.ceil(parsed);
      }
    }
  }

  const secondCandidates = [
    details.retry_after_seconds,
    details.retry_seconds,
    details.seconds,
  ];
  for (const candidate of secondCandidates) {
    if (typeof candidate === "number" && candidate > 0) {
      return Math.ceil(candidate / 60);
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed > 0) {
        return Math.ceil(parsed / 60);
      }
    }
  }

  const retryAtCandidates = [details.retry_at, details.ban_until];
  for (const candidate of retryAtCandidates) {
    if (typeof candidate !== "string") {
      continue;
    }
    const target = new Date(candidate);
    if (Number.isNaN(target.getTime())) {
      continue;
    }
    const diffMs = target.getTime() - Date.now();
    if (diffMs > 0) {
      return Math.ceil(diffMs / 60_000);
    }
  }

  return null;
}

function getErrorCode(payload: LoginErrorResponse | null): string | null {
  const code = payload?.error?.code ?? payload?.code;
  if (typeof code !== "string" || code.length === 0) {
    return null;
  }
  return code.toUpperCase();
}

function buildErrorMessage(status: number, payload: LoginErrorResponse | null): string {
  const code = getErrorCode(payload);
  if (status === 429 || code === "RATE_LIMITED" || code === "AUTH_LOCKED") {
    const details = payload?.error?.details ?? payload?.details ?? {};
    const retryMinutes = getRetryMinutes(details);
    if (retryMinutes !== null) {
      const minuteLabel = retryMinutes === 1 ? "minute" : "minutes";
      return `Too many attempts. Try again in ${retryMinutes} ${minuteLabel}.`;
    }
    return LOCKOUT_FALLBACK_ERROR;
  }
  return GENERIC_AUTH_ERROR;
}

export default function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      if (response.ok) {
        router.push("/chat");
        router.refresh();
        return;
      }

      let payload: LoginErrorResponse | null = null;
      try {
        payload = (await response.json()) as LoginErrorResponse;
      } catch {
        payload = null;
      }
      setErrorMessage(buildErrorMessage(response.status, payload));
    } catch {
      setErrorMessage(GENERIC_AUTH_ERROR);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
      <label className="flex flex-col gap-2 text-sm">
        <span className="font-semibold text-foreground">Email</span>
        <input
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          className="w-full appearance-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-950 shadow-sm outline-none transition placeholder:text-zinc-500 focus:border-zinc-950 focus:ring-2 focus:ring-zinc-950/10 sm:text-sm"
        />
      </label>

      <label className="flex flex-col gap-2 text-sm">
        <span className="font-semibold text-foreground">Password</span>
        <input
          type="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter your password"
          className="w-full appearance-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-base text-zinc-950 shadow-sm outline-none transition placeholder:text-zinc-500 focus:border-zinc-950 focus:ring-2 focus:ring-zinc-950/10 sm:text-sm"
        />
      </label>

      {errorMessage ? (
        <p className="rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-700">
          {errorMessage}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-2 rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition enabled:hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {isSubmitting ? "Signing in..." : "Sign in"}
      </button>
    </form>
  );
}
