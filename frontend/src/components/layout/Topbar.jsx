import { useEffect, useState, useRef } from 'react'
import { Bell, Search, Check, FileText, Package, Clock, Eye, LogOut, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import useNotificationStore from '../../store/notificationStore'
import { toast } from 'sonner'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export default function Topbar() {
  const { user, logout } = useAuthStore()
  const { notifications, unreadCount, startPolling, stopPolling, markAsRead, markAllRead } = useNotificationStore()
  const navigate = useNavigate()
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // Handle click outside for notification dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Handle click outside for profile dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleLogout() {
    setProfileOpen(false)
    logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  const handleNotificationClick = async (n) => {
    setNotifOpen(false)
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
        return <Package className="w-4 h-4 text-forest-700" />
      default:
        return <Bell className="w-4 h-4 text-slate-400" />
    }
  }

  return (
    <header className="sticky top-0 z-30 h-14 bg-white/95 backdrop-blur-sm border-b border-agri-200 flex items-center justify-between px-4 md:px-6">
      {/* Mobile brand */}
      <div className="flex items-center gap-2 md:hidden">
        <img src="/fittree-logo.png" alt="Fittree International LLP" className="h-7 w-auto object-contain" />
        <span className="font-heading font-bold text-forest-800 text-base">Live-Trace</span>
      </div>

      {/* Desktop search placeholder */}
      <div className="hidden md:flex items-center gap-2 bg-agri-50 rounded-lg px-3 py-1.5 w-64 border border-agri-200">
        <Search size={15} className="text-slate-400 shrink-0" />
        <input
          type="text"
          placeholder="Search orders..."
          className="bg-transparent text-sm text-slate-700 placeholder-slate-400 outline-none w-full font-body"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => { setNotifOpen(!notifOpen); setProfileOpen(false) }}
            className={`relative w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 hover:bg-agri-100 hover:text-forest-700 transition-colors ${
              notifOpen ? 'bg-agri-100 text-forest-700' : ''
            }`}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-forest-700 rounded-full ring-2 ring-white" />
            )}
          </button>

          {notifOpen && (
          <div className="absolute right-0 top-11 w-80 bg-white border border-agri-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-agri-100 bg-agri-50">
              <span className="font-heading font-semibold text-slate-900 text-sm">Notifications</span>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllRead()}
                  className="text-xs font-semibold text-forest-700 hover:text-forest-800 flex items-center gap-1 transition-colors"
                >
                  <Check size={12} /> Mark all read
                </button>
              )}
            </div>

            {/* List */}
            <div className="max-h-[300px] overflow-y-auto divide-y divide-agri-100 font-body">
              {notifications.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-xs">
                  No notifications yet.
                </div>
              ) : (
                notifications.slice(0, 5).map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3 cursor-pointer hover:bg-agri-50/50 transition-colors flex gap-3 ${
                      !n.read ? 'bg-forest-50' : ''
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-agri-100 flex items-center justify-center shrink-0 mt-0.5">
                      {getIcon(n.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-medium text-xs text-slate-800 truncate block font-heading">
                          {n.title}
                        </span>
                        <span className="text-[9px] text-slate-400 shrink-0 flex items-center gap-0.5">
                          <Clock size={8} /> {dayjs(n.created_at).fromNow()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                        {n.message}
                      </p>
                      {n.order_code && (
                        <span className="inline-block mt-1 text-[9px] bg-agri-100 text-slate-600 px-1.5 py-0.5 rounded font-heading">
                          {n.order_code}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-agri-100 p-2 text-center bg-agri-50/20">
              <button
                onClick={() => {
                  setNotifOpen(false)
                  navigate('/notifications')
                }}
                className="text-xs font-semibold text-slate-600 hover:text-forest-700 flex items-center justify-center gap-1.5 py-1 w-full transition-colors"
              >
                <Eye size={12} /> View all notifications
              </button>
            </div>
            </div>
          )}
        </div>

        {/* Profile avatar + dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => { setProfileOpen(!profileOpen); setNotifOpen(false) }}
            className="w-9 h-9 rounded-full bg-forest-700 hover:bg-forest-800 flex items-center justify-center text-white text-xs font-bold font-heading cursor-pointer transition-colors"
          >
            {user?.full_name?.slice(0, 2).toUpperCase() ?? 'U'}
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-11 w-56 bg-white border border-agri-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
              {/* User info */}
              <div className="px-4 py-3 border-b border-agri-100">
                <p className="font-heading font-semibold text-sm text-slate-900 truncate">{user?.full_name}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                <span className="inline-block mt-1 text-[10px] font-semibold uppercase bg-forest-50 text-forest-700 px-1.5 py-0.5 rounded">
                  {user?.role?.replace('_', ' ')}
                </span>
              </div>

              {/* Menu items */}
              <div className="p-1.5 space-y-0.5">
                <button
                  onClick={() => { setProfileOpen(false); navigate('/settings') }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-agri-50 transition-colors"
                >
                  <User size={15} />
                  My Profile
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                >
                  <LogOut size={15} />
                  Log Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
