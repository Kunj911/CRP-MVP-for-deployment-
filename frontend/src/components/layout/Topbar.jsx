import { useEffect, useState, useRef } from 'react'
import { Bell, Search, Truck, Check, FileText, Package, Clock, Eye } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import useNotificationStore from '../../store/notificationStore'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export default function Topbar() {
  const user = useAuthStore((s) => s.user)
  const { notifications, unreadCount, startPolling, stopPolling, markAsRead, markAllRead } = useNotificationStore()
  const navigate = useNavigate()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleNotificationClick = async (n) => {
    setDropdownOpen(false)
    if (!n.read) {
      await markAsRead(n.id)
    }
    if (n.related_order_id) {
      navigate(`/orders/${n.related_order_id}`)
    } else {
      navigate('/notifications')
    }
  }

  const getIcon = (type) => {
    switch (type) {
      case 'document':
        return <FileText className="w-4 h-4 text-indigo-500" />
      case 'order':
      case 'shipment':
        return <Package className="w-4 h-4 text-saffron-500" />
      default:
        return <Bell className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <header className="sticky top-0 z-30 h-14 bg-white border-b border-beige-200 flex items-center justify-between px-4 md:px-6">
      {/* Mobile brand */}
      <div className="flex items-center gap-2 md:hidden">
        <div className="w-8 h-8 rounded-lg bg-saffron-500 flex items-center justify-center">
          <Truck className="w-4 h-4 text-white" />
        </div>
        <span className="font-heading font-bold text-gray-900 text-base">Live-Trace</span>
      </div>

      {/* Desktop search placeholder */}
      <div className="hidden md:flex items-center gap-2 bg-beige-100 rounded-lg px-3 py-1.5 w-64">
        <Search size={15} className="text-gray-400 shrink-0" />
        <input
          type="text"
          placeholder="Search orders..."
          className="bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none w-full font-body"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 relative" ref={dropdownRef}>
        {/* Notification bell */}
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className={`relative w-9 h-9 rounded-lg flex items-center justify-center text-gray-500 hover:bg-beige-100 hover:text-saffron-600 transition-colors ${
            dropdownOpen ? 'bg-beige-100 text-saffron-600' : ''
          }`}
        >
          <Bell size={18} />
          {/* Unread indicator */}
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-saffron-500 rounded-full" />
          )}
        </button>

        {/* Dropdown Menu */}
        {dropdownOpen && (
          <div className="absolute right-0 top-11 w-80 bg-white border border-beige-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-beige-100 bg-beige-50/50">
              <span className="font-heading font-semibold text-gray-900 text-sm">Notifications</span>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllRead()}
                  className="text-xs font-semibold text-saffron-600 hover:text-saffron-700 flex items-center gap-1 transition-colors"
                >
                  <Check size={12} /> Mark all read
                </button>
              )}
            </div>

            {/* List */}
            <div className="max-h-[300px] overflow-y-auto divide-y divide-beige-100 font-body">
              {notifications.length === 0 ? (
                <div className="py-8 text-center text-gray-400 text-xs">
                  No notifications yet.
                </div>
              ) : (
                notifications.slice(0, 5).map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3 cursor-pointer hover:bg-beige-50/50 transition-colors flex gap-3 ${
                      !n.read ? 'bg-saffron-50/30' : ''
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-beige-100 flex items-center justify-center shrink-0 mt-0.5">
                      {getIcon(n.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-medium text-xs text-gray-800 truncate block font-heading">
                          {n.title}
                        </span>
                        <span className="text-[9px] text-gray-400 shrink-0 flex items-center gap-0.5">
                          <Clock size={8} /> {dayjs(n.created_at).fromNow()}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                        {n.message}
                      </p>
                      {n.order_code && (
                        <span className="inline-block mt-1 text-[9px] bg-beige-100 text-gray-600 px-1.5 py-0.5 rounded font-heading">
                          {n.order_code}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-beige-100 p-2 text-center bg-beige-50/20">
              <button
                onClick={() => {
                  setDropdownOpen(false)
                  navigate('/notifications')
                }}
                className="text-xs font-semibold text-gray-600 hover:text-saffron-600 flex items-center justify-center gap-1.5 py-1 w-full transition-colors"
              >
                <Eye size={12} /> View all notifications
              </button>
            </div>
          </div>
        )}

        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-cardamom-500 flex items-center justify-center text-white text-xs font-bold font-heading cursor-pointer">
          {user?.full_name?.slice(0, 2).toUpperCase() ?? 'U'}
        </div>
      </div>
    </header>
  )
}
