import axios from 'axios'

/**
 * Novu Opportunity Radar — Django REST Framework (DRF) API Client
 * Version: 1.0 (Production DRF Integration)
 * 
 * Provides unified HTTP interaction with backend Django endpoints:
 *   - JWT Authentication with auto-refresh (/api/v1/auth/token/)
 *   - Opportunities Queue & Detail (/api/v1/opportunities/)
 *   - Deterministic 100-pt Scoring, Provenance & Evidence inspection
 *   - Sales Pipeline Kanban stages (/api/v1/opportunities/pipeline/)
 *   - Duplicate Candidate Review & Soft-merge (/api/v1/duplicates/)
 *   - Manual Observation Capture with instant qualification (/api/v1/observations/)
 *   - Source Health & Observability (/api/v1/sources/, /api/v1/runs/)
 *   - Search Terms & Qualification Rules (/api/v1/search-terms/)
 *   - Operating Settings (/api/v1/settings/)
 *   - Formula-Safe CSV Exports (/api/v1/exports/opportunities.csv)
 *   - Cloud Workbook Sync (/api/v1/sync/jobs/, /api/v1/sync/targets/)
 */

const API_BASE = '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Demo credentials helper for quick testing & role switching
export const DEMO_CREDENTIALS = {
  admin: 'admin123',
  manager: 'manager123',
  executive: 'exec123',
  executive_b: 'exec123',
}

export const USERS = [
  { id: 1, username: 'admin', display_name: 'Administrator', role: 'admin' },
  { id: 2, username: 'manager', display_name: 'Sales Manager', role: 'sales_manager' },
  { id: 3, username: 'executive', display_name: 'Sales Executive A', role: 'sales_executive' },
  { id: 4, username: 'executive_b', display_name: 'Sales Executive B', role: 'sales_executive' },
]

export const SUPPORTED_CATEGORIES = [
  'CUSTOM_DEV', 'MOBILE_APP', 'WEBSITE', 'ERP', 'CRM', 'LMS',
  'AI_AUTOMATION', 'STAFF_AUGMENTATION', 'MANAGED_IT', 'CLOUD_DEVOPS', 'CYBERSECURITY'
]

// Attach Bearer JWT token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh expired JWT token on 401
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/token/') &&
      !originalRequest.url?.includes('/auth/token/refresh/')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        isRefreshing = false
        logout()
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${API_BASE}/auth/token/refresh/`, {
          refresh: refreshToken,
        })
        localStorage.setItem('access_token', data.access)
        api.defaults.headers.common.Authorization = `Bearer ${data.access}`
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        processQueue(null, data.access)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        logout()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ----------------------------------------------------------------------------
// Authentication & User Management
// ----------------------------------------------------------------------------

export async function login(username, password) {
  const { data } = await api.post('/auth/token/', { username, password })
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  const me = await getMe()
  localStorage.setItem('current_user', JSON.stringify(me))
  return { ...data, user: me }
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('current_user')
}

export async function getMe() {
  const { data } = await api.get('/me/')
  return data
}

export async function getUsers() {
  const { data } = await api.get('/users/')
  return data.results || data
}

export async function switchUserRole(username) {
  const password = DEMO_CREDENTIALS[username] || 'admin123'
  return login(username, password)
}

// ----------------------------------------------------------------------------
// Opportunities Queue & Details
// ----------------------------------------------------------------------------

export async function getOpportunities(params = {}) {
  const { data } = await api.get('/opportunities/', { params })
  return data
}

export async function getOpportunity(id) {
  const { data } = await api.get(`/opportunities/${id}/`)
  return data
}

export async function updateOpportunity(id, payload) {
  const { data } = await api.patch(`/opportunities/${id}/`, payload)
  return data
}

export async function createDraft(opportunityId, content = '') {
  const payload = content ? { content } : {}
  const { data } = await api.post(`/opportunities/${opportunityId}/drafts/`, payload)
  return data
}

export async function getDrafts(opportunityId) {
  const { data } = await api.get(`/opportunities/${opportunityId}/draft-list/`)
  return data.results || data
}

export async function getActivities(opportunityId) {
  const { data } = await api.get(`/opportunities/${opportunityId}/activities/`)
  return data.results || data
}

export async function getStats() {
  const { data } = await api.get('/opportunities/stats/')
  return data
}

export async function getPipeline() {
  const { data } = await api.get('/opportunities/pipeline/')
  return data
}

// ----------------------------------------------------------------------------
// Duplicates Detection & Review
// ----------------------------------------------------------------------------

export async function getDuplicates(params = {}) {
  const { data } = await api.get('/duplicates/', { params })
  return data
}

export async function getDuplicateCount() {
  try {
    const data = await getDuplicates({ decision: 'pending' })
    const list = data.results || data
    return Array.isArray(list) ? list.length : (data.count || 0)
  } catch {
    return 0
  }
}

export async function resolveDuplicate(candidateId, decision) {
  const { data } = await api.post(`/duplicates/${candidateId}/resolve/`, { decision })
  return data
}

// ----------------------------------------------------------------------------
// Manual Capture & Observations
// ----------------------------------------------------------------------------

export async function captureObservation(observationData) {
  const { data } = await api.post('/observations/', observationData)
  return data
}

export async function getObservations(params = {}) {
  const { data } = await api.get('/observations/', { params })
  return data
}

// ----------------------------------------------------------------------------
// Sources & Collection Runs
// ----------------------------------------------------------------------------

export async function getSources() {
  const { data } = await api.get('/sources/')
  return data
}

export async function updateSource(id, payload) {
  const { data } = await api.patch(`/sources/${id}/`, payload)
  return data
}

export async function getRuns(params = {}) {
  const { data } = await api.get('/runs/', { params })
  return data
}

export async function triggerRun(sourceId) {
  const { data } = await api.post('/runs/', { source_id: sourceId })
  return data
}

export async function getSearchTerms(params = {}) {
  const { data } = await api.get('/search-terms/', { params })
  return data
}

// ----------------------------------------------------------------------------
// Operating Settings
// ----------------------------------------------------------------------------

export async function getSettings() {
  const { data } = await api.get('/settings/')
  return data
}

export async function updateSettings(settingsPayload) {
  const { data } = await api.patch('/settings/', settingsPayload)
  return data
}

// ----------------------------------------------------------------------------
// Cloud Workbook Sync & Outbox
// ----------------------------------------------------------------------------

export async function getSyncJobs(params = {}) {
  const { data } = await api.get('/sync/jobs/', { params })
  return data
}

export async function createSyncJob(targetId = null) {
  const payload = targetId ? { target_id: targetId } : {}
  const { data } = await api.post('/sync/jobs/', payload)
  return data
}

export async function getSyncTargets() {
  const { data } = await api.get('/sync/targets/')
  return data
}

export async function getOutbox(params = {}) {
  const { data } = await api.get('/outbox/', { params })
  return data
}

export async function getContacts(params = {}) {
  const { data } = await api.get('/contacts/', { params })
  return data
}

// ----------------------------------------------------------------------------
// CSV Export Action (Formula Injection Protected)
// ----------------------------------------------------------------------------

export function exportCsvUrl(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      searchParams.append(k, v)
    }
  })
  const qs = searchParams.toString()
  return `${API_BASE}/exports/opportunities.csv${qs ? `?${qs}` : ''}`
}

export async function downloadCsv(params = {}) {
  const response = await api.get('/exports/opportunities.csv', {
    params,
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Novu_Opportunity_Radar_Export_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
  return { success: true }
}
