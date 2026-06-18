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
  (config) => {
    const { accessToken } = useAuthStore.getState()

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }

    // Attach CSRF token for non-GET requests (double-submit pattern)
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
let isLoggingOut = false
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
      // Don't retry refresh, login, or logout requests themselves
      if (originalRequest.url?.includes('/auth/refresh') ||
          originalRequest.url?.includes('/auth/login')) {
        useAuthStore.getState().logout()
        return Promise.reject(error)
      }
      // Logout endpoint: user is already being logged out, just surface the error
      if (originalRequest.url?.includes('/auth/logout')) {
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
        const csrfToken = Cookies.get('csrf_token')
        const res = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
          withCredentials: true,
          headers: {
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
          },
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
  let message = 'Something went wrong.'
  if (data?.error?.message) {
    message = data.error.message
  } else if (Array.isArray(data?.detail)) {
    message = data.detail.map((d) => d.msg).join('; ') || 'Validation error'
  } else if (data?.detail) {
    message = data.detail
  }

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
