import { Bell, Check, Package, FileText, CheckCircle2, Clock } from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import Button from '../../components/ui/Button'
import useNotificationStore from '../../store/notificationStore'
import { useNavigate } from 'react-router-dom'

// Extend dayjs for relative time (e.g. "2 hours ago")
dayjs.extend(relativeTime)

function NotificationIcon({ type }) {
  if (type === 'document') return <FileText size={18} className="text-indigo-500" />
  if (type === 'order' || type === 'shipment') return <TruckIcon />
  return <Bell size={18} className="text-gray-400" />
}

function TruckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-saffron-500">
      <rect width="15" height="13" x="1" y="3" rx="2" /><path d="M16 8h4l3 3v5h-7V8z" /><circle cx="5.5" cy="18.5" r="2.5" /><circle cx="18.5" cy="18.5" r="2.5" />
    </svg>
  )
}

export default function NotificationsPage() {
  const { notifications, isLoading, unreadCount, markAsRead, markAllRead } = useNotificationStore()
  const navigate = useNavigate()

  const handleNotificationClick = async (notif) => {
    if (!notif.read) {
      await markAsRead(notif.id)
    }
    if (notif.related_order_id) {
      navigate(`/orders/${notif.related_order_id}`)
    }
  }

  return (
    <div className="max-w-3xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-xl text-gray-900">Notifications</h1>
          <p className="text-sm text-gray-500 font-body">
            {isLoading ? 'Refreshing alerts...' : 'Recent alerts and updates.'}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            icon={Check}
            onClick={() => markAllRead()}
          >
            Mark all as read
          </Button>
        )}
      </div>

      {/* List */}
      <div className="bg-white rounded-xl border border-beige-200 shadow-card divide-y divide-beige-100 overflow-hidden">
        {notifications.length > 0 ? (
          notifications.map((notif) => (
            <div 
              key={notif.id} 
              onClick={() => handleNotificationClick(notif)}
              className={`p-4 flex gap-4 cursor-pointer hover:bg-beige-50/20 transition-colors ${
                notif.read ? 'bg-white' : 'bg-saffron-50/30'
              }`}
            >
              {/* Icon */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                notif.read ? 'bg-beige-100' : 'bg-white shadow-sm border border-saffron-100'
              }`}>
                <NotificationIcon type={notif.type} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start gap-2 mb-1">
                  <h3 className={`text-sm font-heading ${notif.read ? 'text-gray-700 font-medium' : 'text-gray-900 font-bold'}`}>
                    {notif.title} 
                    {notif.order_code && (
                      <span className="text-xs font-normal text-gray-400 font-body ml-2">· {notif.order_code}</span>
                    )}
                  </h3>
                  <span className="text-[11px] text-gray-400 font-body shrink-0 flex items-center gap-1">
                    <Clock size={10} /> {dayjs(notif.created_at).fromNow()}
                  </span>
                </div>
                <p className={`text-sm font-body ${notif.read ? 'text-gray-500' : 'text-gray-700'}`}>
                  {notif.message}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="py-16 text-center">
            <Bell size={36} className="text-beige-300 mx-auto mb-3" />
            <p className="text-sm text-gray-400 font-body">You have no notifications.</p>
          </div>
        )}
      </div>
    </div>
  )
}
