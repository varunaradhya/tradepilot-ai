export type HealthStatus = {
  status: string;
};

export type User = {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
  updated_at: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const apiUrl = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const healthUrl = new URL("/health", apiUrl).toString();
const REQUEST_TIMEOUT_MS = 15_000;
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
let refreshPromise: Promise<boolean> | null = null;

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${apiUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const payload = (await response.json()) as TokenResponse;
      if (!payload.access_token || !payload.refresh_token) return false;
      localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

function clearAuthentication(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event("tradepilot:logout"));
}

async function request<T>(url: string, options: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS, allowRefresh = true): Promise<T> {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (response.status === 401 && allowRefresh && !url.endsWith("/auth/login") && !url.endsWith("/auth/refresh")) {
      const refreshed = await refreshAccessToken();
      if (refreshed) return request<T>(url, options, timeoutMs, false);
      clearAuthentication();
    }

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const payload = (await response.json()) as { detail?: string | { message?: string } };
        if (typeof payload.detail === "string") message = payload.detail;
        else if (payload.detail?.message) message = payload.detail.message;
      } catch {
        // Keep the status-based fallback when the server does not return JSON.
      }
      throw new ApiError(response.status, message);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (isAbortError(error)) {
      throw new ApiError(408, "The request timed out. Please check the backend or try again.");
    }
    if (error instanceof TypeError) {
      throw new ApiError(0, "TradePilot backend is unreachable. Check that the API is running and try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function get<T>(url: string, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  return request<T>(url, {}, timeoutMs);
}

export async function apiRequest<T>(path: string, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  return get<T>(`${apiUrl}${path}`, timeoutMs);
}

export const api = {
  getHealth: () => get<HealthStatus>(healthUrl),
  getUsers: () => get<User[]>(`${apiUrl}/users/`),
  get: <T>(path: string, timeoutMs = REQUEST_TIMEOUT_MS) => apiRequest<T>(path, timeoutMs),
  post: <T>(path: string, body?: unknown, timeoutMs = REQUEST_TIMEOUT_MS) =>
    request<T>(`${apiUrl}${path}`, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }, timeoutMs),
  put: <T>(path: string, body?: unknown, timeoutMs = REQUEST_TIMEOUT_MS) =>
    request<T>(`${apiUrl}${path}`, {
      method: "PUT",
      body: body === undefined ? undefined : JSON.stringify(body),
    }, timeoutMs),
  delete: <T>(path: string, timeoutMs = REQUEST_TIMEOUT_MS) => request<T>(`${apiUrl}${path}`, { method: "DELETE" }, timeoutMs),
};
