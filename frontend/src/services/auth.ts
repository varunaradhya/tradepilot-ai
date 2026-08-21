import { api } from "./api";

const TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export type LoginCredentials = { email: string; password: string };
export type RegisterDetails = LoginCredentials & { full_name: string };
export type TokenResponse = { access_token: string; refresh_token: string; token_type: string };
type ForgotPasswordResponse = { message: string; debug_reset_token?: string };

export function getAccessToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function getRefreshToken(): string | null { return localStorage.getItem(REFRESH_TOKEN_KEY); }
export function isAuthenticated(): boolean { return getAccessToken() !== null || getRefreshToken() !== null; }
export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event("tradepilot:logout"));
}

export function saveToken(response: TokenResponse, notify = true): void {
  localStorage.setItem(TOKEN_KEY, response.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
  if (notify) window.dispatchEvent(new Event("tradepilot:login"));
}

export async function login(credentials: LoginCredentials): Promise<void> { saveToken(await api.post<TokenResponse>("/auth/login", credentials)); }
export async function register(details: RegisterDetails): Promise<void> {
  await api.post("/auth/register", details);
  await login({ email: details.email, password: details.password });
}
export async function requestPasswordReset(email: string): Promise<ForgotPasswordResponse> {
  return api.post<ForgotPasswordResponse>("/auth/forgot-password", { email });
}
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post<void>("/auth/reset-password", { token, new_password: newPassword });
}
