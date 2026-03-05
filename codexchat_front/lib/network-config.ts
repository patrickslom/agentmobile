const API_PATH = "/api";
const WS_PATH = "/ws";

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function normalizeHttpBaseUrl(value: string): string {
  const normalized = trimTrailingSlash(value.trim());
  const parsed = new URL(normalized);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `Invalid API base URL protocol "${parsed.protocol}". Use http:// or https://.`,
    );
  }
  return normalized;
}

function normalizeWebSocketUrl(value: string): string {
  const normalized = trimTrailingSlash(value.trim());
  const parsed = new URL(normalized);
  if (parsed.protocol !== "ws:" && parsed.protocol !== "wss:") {
    throw new Error(
      `Invalid WebSocket URL protocol "${parsed.protocol}". Use ws:// or wss://.`,
    );
  }
  return normalized;
}

function getConfiguredOrigin(): string | null {
  const fromEnv = process.env.NEXT_PUBLIC_APP_ORIGIN;
  if (!fromEnv) {
    return null;
  }
  return normalizeHttpBaseUrl(fromEnv);
}

export function getApiBaseUrl(): string {
  const explicitApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (explicitApiBaseUrl) {
    return normalizeHttpBaseUrl(explicitApiBaseUrl);
  }

  const configuredOrigin = getConfiguredOrigin();
  if (configuredOrigin) {
    return `${configuredOrigin}${API_PATH}`;
  }

  return API_PATH;
}

export function getWebSocketUrl(): string {
  const explicitWebSocketUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (explicitWebSocketUrl) {
    return normalizeWebSocketUrl(explicitWebSocketUrl);
  }

  const configuredOrigin = getConfiguredOrigin();
  if (configuredOrigin) {
    const protocol = configuredOrigin.startsWith("https://") ? "wss" : "ws";
    const withoutScheme = configuredOrigin.replace(/^https?:\/\//, "");
    return `${protocol}://${withoutScheme}${WS_PATH}`;
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${WS_PATH}`;
  }

  throw new Error(
    "Unable to resolve WebSocket URL. Set NEXT_PUBLIC_APP_ORIGIN or NEXT_PUBLIC_WS_URL.",
  );
}

