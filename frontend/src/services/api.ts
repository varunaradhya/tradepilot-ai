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
  constructor(public readonly status: number, message: string) { super(message); }
}

const apiUrl = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);
const healthUrl = new URL("/health", apiUrl).toString();

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try { message = (await response.json() as { detail?: string }).detail ?? message; } catch { /* non-JSON response */ }
    if (response.status === 401) { localStorage.removeItem("access_token"); window.dispatchEvent(new Event("tradepilot:logout")); }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function get<T>(url: string): Promise<T> { return request<T>(url); }

export async function apiRequest<T>(path: string): Promise<T> {
  return get<T>(`${apiUrl}${path}`);
}

export const api = {
  getHealth: () => get<HealthStatus>(healthUrl),
  getUsers: () => get<User[]>(`${apiUrl}/users/`),
  get: apiRequest,
  post: <T>(path: string, body?: unknown) => request<T>(`${apiUrl}${path}`, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(`${apiUrl}${path}`, { method: "DELETE" }),
};
