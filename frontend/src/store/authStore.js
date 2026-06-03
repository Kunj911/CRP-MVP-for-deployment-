/**
 * frontend/src/store/authStore.js
 *
 * Zustand auth store — IN-MEMORY ONLY (no persist).
 *
 * Security hardening:
 *   - refreshToken REMOVED — only exists as HttpOnly cookie
 *   - persist middleware REMOVED — no auth data in localStorage
 *   - Session bootstrap flow via bootstrapSession()
 *   - isSessionLoading state for app startup
 *
 * The access token lives only in JS memory. On page reload,
 * the app calls GET /auth/me with the HttpOnly refresh cookie
 * to restore the session (see App.jsx bootstrapSession).
 */

import { create } from 'zustand'
import Cookies from 'js-cookie'
import useNotificationStore from './notificationStore'

const useAuthStore = create((set, get) => ({
  // ── State ──────────────────────────────────────────────────────────────────
  user: null,
  accessToken: null,
  isSessionLoading: true,  // true until bootstrap completes

  // ── Actions ────────────────────────────────────────────────────────────────

  /**
   * Set user + access token after successful login.
   * NOTE: No refreshToken parameter — it's HttpOnly cookie only.
   */
  login: (user, accessToken) => {
    Cookies.set('session_exists', 'true', { expires: 7, secure: true, sameSite: 'lax' })
    set({ user, accessToken, isSessionLoading: false })
  },

  /**
   * Clear all auth state. Called on logout or session expiry.
   */
  logout: () => {
    Cookies.remove('session_exists')
    // Stop background notification polling to prevent memory leaks and 401 spam
    useNotificationStore.getState().stopPolling()
    set({ user: null, accessToken: null, isSessionLoading: false })
  },

  /**
   * Update access token (e.g., after silent refresh).
   */
  setAccessToken: (token) => set({ accessToken: token }),

  /**
   * Set session loading state.
   */
  setSessionLoading: (loading) => set({ isSessionLoading: loading }),

  /**
   * Bootstrap session from server on app startup.
   * Attempts to restore session via refresh cookie + /auth/me.
   */
  bootstrapSession: async () => {
    // If no session exists, skip refresh call to avoid useless 401s (Task 18)
    if (!Cookies.get('session_exists')) {
      set({ user: null, accessToken: null, isSessionLoading: false })
      return
    }

    set({ isSessionLoading: true })
    try {
      // Import dynamically to avoid circular dependency
      const { default: apiClient } = await import('../api/client')

      // First, try to refresh the access token using the HttpOnly cookie
      const refreshRes = await apiClient.post('/auth/refresh')
      const newAccessToken = refreshRes.data.access_token

      // Then fetch user profile
      const meRes = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${newAccessToken}` }
      })

      set({
        user: meRes.data,
        accessToken: newAccessToken,
        isSessionLoading: false,
      })
    } catch {
      // No valid session — user needs to log in, clear indicator
      Cookies.remove('session_exists')
      set({ user: null, accessToken: null, isSessionLoading: false })
    }
  },

  // ── Computed helpers ───────────────────────────────────────────────────────
  isAuthenticated: () => !!get().accessToken,

  // Role helpers
  isAdmin:    () => ['SUPER_ADMIN', 'ADMIN'].includes(get().user?.role),
  isStaff:    () => ['SUPER_ADMIN', 'ADMIN', 'WAREHOUSE', 'QA', 'DOCUMENTATION'].includes(get().user?.role),
  isCustomer: () => get().user?.role === 'CUSTOMER',
  isWarehouse:() => get().user?.role === 'WAREHOUSE',
  isQA:       () => get().user?.role === 'QA',
  isDocs:     () => get().user?.role === 'DOCUMENTATION',
}))

export default useAuthStore
