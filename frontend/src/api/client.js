/**
 * frontend/src/api/client.js
 *
 * Axios API client with security hardening:
 *   - withCredentials: true (sends HttpOnly cookies automatically)
 *   - CSRF double-submit: reads csrf_token cookie, sends X-CSRF-Token header
 *   - Silent token refresh on 401 (cookie-based, no token in JS)
 *   - Global API error normalization
 *   - Auto-toast for common error scenarios
 */

import axios from 'axios'
import useAuthStore from '../store/authStore'
import { toast } from 'sonner'
import Cookies from 'js-cookie'

// Use relative API base URL to leverage Nginx reverse proxy
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/**
 * Decode base64 JWT payload to check expiry.
 */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // CRITICAL: Send HttpOnly cookies (refresh_token, csrf_token)
})

// ── Request Interceptor ─────────────────────────────────────────────────────
// Attach JWT access token + CSRF token on every request

apiClient.interceptors.request.use(
  async (config) => {
    let { accessToken, logout, setAccessToken } = useAuthStore.getState()

    // Proactive silent refresh: if token is near expiry (< 30s), refresh first (Task 18)
    if (accessToken) {
      const payload = parseJwt(accessToken)
      if (payload && payload.exp) {
        const isNearExpiry = (payload.exp * 1000) - Date.now() < 30000 // 30s buffer
        if (isNearExpiry) {
          try {
            const res = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
              withCredentials: true,
            })
            accessToken = res.data.access_token
            setAccessToken(accessToken)
          } catch (err) {
            accessToken = null
            logout()
          }
        }
      }
    }

    // Attach access token from in-memory store
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }

    // Attach CSRF token for non-GET requests (double-submit pattern) using js-cookie (Task 18)
    const method = (config.method || '').toUpperCase()
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const csrfToken = Cookies.get('csrf_token')
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

// ── Response Interceptor ────────────────────────────────────────────────────
// Handle 401 with silent refresh, normalize all errors

let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // ── 401: Attempt silent token refresh ──────────────────────────────────
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't retry refresh or login requests themselves
      if (originalRequest.url?.includes('/auth/refresh') ||
          originalRequest.url?.includes('/auth/login')) {
        useAuthStore.getState().logout()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return apiClient(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Attempt to refresh — cookie is sent automatically
        const res = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
          withCredentials: true,
        })

        const newAccessToken = res.data.access_token
        useAuthStore.getState().setAccessToken(newAccessToken)

        processQueue(null, newAccessToken)

        // Retry the original request with the new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        useAuthStore.getState().logout()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // ── Global error normalization ─────────────────────────────────────────
    if (!originalRequest._silentError) {
      _handleApiError(error)
    }

    return Promise.reject(error)
  }
)

/**
 * Normalize and display API errors via toast.
 * Callers can opt out by setting config._silentError = true.
 */
function _handleApiError(error) {
  if (!error.response) {
    // Network error (no response from server)
    toast.error('Network error — please check your connection.')
    return
  }

  const status = error.response.status
  const data = error.response.data
  const message = data?.error?.message || data?.detail || 'Something went wrong.'

  switch (status) {
    case 401:
      // Already handled by refresh logic above — only toast if refresh failed
      if (error.config?._retry) {
        toast.error('Session expired. Please log in again.')
      }
      break
    case 403:
      toast.error(message || 'You do not have permission to do this.')
      break
    case 404:
      // Don't auto-toast 404s — callers handle these contextually
      break
    case 422:
      // Validation errors
      toast.error(message || 'Please check your input and try again.')
      break
    case 429:
      toast.error(message || 'Too many requests. Please wait a moment.')
      break
    case 500:
      toast.error('Server error — please try again later.')
      break
    default:
      if (status >= 400) {
        toast.error(message)
      }
  }
}

export default apiClient
