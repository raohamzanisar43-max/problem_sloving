import apiClient from './apiClient';
import { clearTokens, getAccessToken, setTokens } from './tokenStore';

export async function login(username: string, password: string): Promise<void> {
  const response = await apiClient.post('/auth/token/', { username, password });
  setTokens(response.data.access, response.data.refresh);
}

export function logout(): void {
  clearTokens();
}

export function isLoggedIn(): boolean {
  return Boolean(getAccessToken());
}
