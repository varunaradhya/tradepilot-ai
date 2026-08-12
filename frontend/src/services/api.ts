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

const apiUrl = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);
const healthUrl = new URL("/health", apiUrl).toString();

async function get<T>(url: string): Promise<T> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getHealth: () => get<HealthStatus>(healthUrl),
  getUsers: () => get<User[]>(`${apiUrl}/users/`),
};
