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

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const apiUrl = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const healthUrl = new URL("/health", apiUrl).toString();
const REQUEST_TIMEOUT_MS = 15_000;

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function request<T>(url: string, options: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const token = localStorage.getItem("access_token");
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

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const payload = (await response.json()) as { detail?: string | { message?: string } };
        if (typeof payload.detail === "string") message = payload.detail;
        else if (payload.detail?.message) message = payload.detail.message;
      } catch {
        // Keep the status-based fallback when the server does not return JSON.
      }

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        window.dispatchEvent(new Event("tradepilot:logout"));
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
