/**
 * frontend/src/store/authStore.js
 *
 * Zustand auth store — IN-MEMORY ONLY (no persist).
 *
 * The access token lives only in JS memory. On page reload
 * there is no session restoration — user must log in again.
 * During SPA navigation, the Axios interceptor handles
 * silent token refresh via the HttpOnly cookie.
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
    set({ user, accessToken, isSessionLoading: false })
  },

  /**
   * Clear all auth state. Called on logout or session expiry.
   * Attempts to notify the backend (fire-and-forget) to revoke the session.
   */
  logout: () => {
    // Notify backend to revoke the refresh token (best-effort, non-blocking)
    try {
      import('../api/client').then(({ default: apiClient }) => {
        apiClient.post('/auth/logout', {}, { _silentError: true }).catch(() => {})
      }).catch(() => {})
    } catch {}

    Cookies.remove('csrf_token')
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
   * Bootstrap — no session persistence across page reloads.
   */
  bootstrapSession: async () => {
    // No session persistence across page reloads — user must log in each time
    set({ isSessionLoading: false })
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
