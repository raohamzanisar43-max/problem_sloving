import apiClient from './apiClient';

const ACCESS_TOKEN_KEY = 'novu_radar_access_token';
const REFRESH_TOKEN_KEY = 'novu_radar_refresh_token';

export async function login(username: string, password: string): Promise<void> {
  const response = await apiClient.post('/auth/token/', { username, password });
  localStorage.setItem(ACCESS_TOKEN_KEY, response.data.access);
  localStorage.setItem(REFRESH_TOKEN_KEY, response.data.refresh);
}

export function logout(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));
}