import axios, { type InternalAxiosRequestConfig } from 'axios';
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokenStore';

// Same-origin by default (production is served behind one nginx); override for local dev,
// e.g. VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// One refresh at a time: parallel requests that all hit a 401 share the same attempt.
let refreshing: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  const refresh = getRefreshToken();
  if (!refresh) return Promise.reject(new Error('No refresh token'));
  refreshing ??= axios
    .post(`${API_BASE_URL}/auth/token/refresh/`, { refresh })
    .then((res) => {
      setTokens(res.data.access, res.data.refresh);
      return res.data.access as string;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

function endSession(): void {
  clearTokens();
  if (window.location.pathname !== '/login') window.location.assign('/login');
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original: RetriableConfig | undefined = error.config;
    const isAuthCall = original?.url?.includes('/auth/token');
    if (error.response?.status !== 401 || !original || original._retried || isAuthCall) {
      return Promise.reject(error);
    }
    original._retried = true;
    try {
      const access = await refreshAccessToken();
      original.headers.Authorization = `Bearer ${access}`;
      return apiClient(original);
    } catch {
      // The session is really over: send the user to sign in instead of showing an empty app.
      endSession();
      return Promise.reject(error);
    }
  },
);

export default apiClient;
