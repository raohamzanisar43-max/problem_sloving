import axios from 'axios';

// Same-origin by default (production is served behind one nginx); override for local dev,
// e.g. VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('novu_radar_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;