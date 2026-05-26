import { Bell, Search, Truck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

export default function Topbar() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

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
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <button
          onClick={() => navigate('/notifications')}
          className="relative w-9 h-9 rounded-lg flex items-center justify-center text-gray-500 hover:bg-beige-100 hover:text-saffron-600 transition-colors"
        >
          <Bell size={18} />
          {/* Unread indicator */}
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-saffron-500 rounded-full" />
        </button>

        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-cardamom-500 flex items-center justify-center text-white text-xs font-bold font-heading cursor-pointer">
          {user?.full_name?.slice(0, 2).toUpperCase() ?? 'U'}
        </div>
      </div>
    </header>
  )
}
