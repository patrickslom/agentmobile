import { cookies, headers } from "next/headers";

export const SESSION_COOKIE_KEYS = [
  "codexchat_session",
  "session",
  "session_id",
  "auth_session",
] as const;

type SessionUser = {
  id?: string;
  email?: string;
  role?: string;
};

export async function hasSessionCookie(): Promise<boolean> {
  const cookieStore = await cookies();
  return SESSION_COOKIE_KEYS.some((cookieKey) =>
    Boolean(cookieStore.get(cookieKey)?.value),
  );
}

function getConfiguredApiBaseUrl(): string | null {
  const explicitApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (explicitApiBaseUrl) {
    try {
      const parsed = new URL(explicitApiBaseUrl);
      if (
        (parsed.protocol === "http:" || parsed.protocol === "https:") &&
        Boolean(parsed.host)
      ) {
        return explicitApiBaseUrl.replace(/\/$/, "");
      }
    } catch {
      // Ignore invalid explicit API URL and fall back to inferred host URL.
    }
  }

  const appOrigin = process.env.NEXT_PUBLIC_APP_ORIGIN?.trim();
  if (appOrigin) {
    try {
      const parsed = new URL(appOrigin);
      if (
        (parsed.protocol === "http:" || parsed.protocol === "https:") &&
        Boolean(parsed.host)
      ) {
        return `${appOrigin.replace(/\/$/, "")}/api`;
      }
    } catch {
      // Ignore invalid app origin and fall back to inferred host URL.
    }
  }

  return null;
}

export async function resolveServerApiBaseUrl(): Promise<string | null> {
  const configured = getConfiguredApiBaseUrl();
  if (configured) {
    return configured;
  }

  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  if (!host) {
    return null;
  }

  const proto = headerStore.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}/api`;
}

export async function getAuthenticatedUser(): Promise<SessionUser | null> {
  if (!(await hasSessionCookie())) {
    return null;
  }

  const apiBaseUrl = await resolveServerApiBaseUrl();
  if (!apiBaseUrl) {
    return null;
  }

  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();

  try {
    const response = await fetch(`${apiBaseUrl}/me`, {
      method: "GET",
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    const payload = (await response.json()) as { user?: SessionUser } & SessionUser;
    return payload.user ?? payload;
  } catch {
    return null;
  }
}

export async function isAuthenticatedAdmin(): Promise<boolean> {
  const user = await getAuthenticatedUser();
  return user?.role === "admin";
}
