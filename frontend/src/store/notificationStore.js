import { create } from 'zustand'
import { notificationsApi } from '../api'

function normalizeNotification(notification) {
  return {
    id: notification.id,
    type: notification.notification_type || 'system',
    title: notification.title || 'Notification',
    message: notification.message || '',
    order_code: notification.order_code || (notification.related_order_id ? `Order #${notification.related_order_id}` : (notification.order_id ? `Order #${notification.order_id}` : '')),
    created_at: notification.created_at,
    read: notification.is_read ?? false,
    related_order_id: notification.related_order_id || notification.order_id,
    related_document_id: notification.related_document_id,
  }
}

const useNotificationStore = create((set, get) => ({
  notifications: [],
  unreadCount: 0,
  hasFetched: false,
  isLoading: false,
  error: null,
  pollerId: null,

  fetchNotifications: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await notificationsApi.list({ limit: 50 })
      const data = Array.isArray(res.data?.data) ? res.data.data : []
      const notifications = data.map(normalizeNotification)
      set({
        notifications,
        unreadCount: notifications.filter((n) => !n.read).length,
        hasFetched: true,
        isLoading: false,
      })
    } catch (error) {
      set({ error, isLoading: false })
    }
  },

  markAsRead: async (id) => {
    try {
      await notificationsApi.markAsRead(id)
      // Optimistically update
      const updated = get().notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      )
      set({
        notifications: updated,
        unreadCount: Math.max(0, get().unreadCount - 1),
      })
    } catch (error) {
      console.error(`Failed to mark notification ${id} as read:`, error)
    }
  },

  markAllRead: async () => {
    try {
      await notificationsApi.markAllRead()
      // Optimistically update
      const updated = get().notifications.map((n) => ({ ...n, read: true }))
      set({
        notifications: updated,
        unreadCount: 0,
      })
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error)
    }
  },

  startPolling: () => {
    if (get().pollerId) return

    get().fetchNotifications()
    const pollerId = window.setInterval(() => {
      get().fetchNotifications()
    }, 15000) // Poll every 15s

    set({ pollerId })
  },

  stopPolling: () => {
    const pollerId = get().pollerId
    if (pollerId) {
      window.clearInterval(pollerId)
      set({ pollerId: null })
    }
  },
}))

export default useNotificationStore
