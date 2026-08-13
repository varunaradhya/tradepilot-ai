import { api } from "./api";

const TOKEN_KEY = "access_token";

export type LoginCredentials = { email: string; password: string };
export type RegisterDetails = LoginCredentials & { full_name: string };
type TokenResponse = { access_token: string; token_type: string };

export function getAccessToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function isAuthenticated(): boolean { return getAccessToken() !== null; }
export function logout(): void { localStorage.removeItem(TOKEN_KEY); window.dispatchEvent(new Event("tradepilot:logout")); }

function saveToken(response: TokenResponse): void {
  localStorage.setItem(TOKEN_KEY, response.access_token);
  window.dispatchEvent(new Event("tradepilot:login"));
}

export async function login(credentials: LoginCredentials): Promise<void> { saveToken(await api.post<TokenResponse>("/auth/login", credentials)); }
export async function register(details: RegisterDetails): Promise<void> {
  await api.post("/auth/register", details);
  await login({ email: details.email, password: details.password });
}
