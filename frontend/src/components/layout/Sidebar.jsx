import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Package, Upload, FileText,
  Bell, Settings, LogOut, Truck
} from 'lucide-react'
import useAuthStore from '../../store/authStore'
import { toast } from 'sonner'

const ROLE_NAV = {
  SUPER_ADMIN:   ['dashboard','orders','uploads','documents','notifications','settings'],
  ADMIN:         ['dashboard','orders','uploads','documents','notifications','settings'],
  WAREHOUSE:     ['dashboard','orders','uploads','documents','notifications','settings'],
  QA:            ['dashboard','orders','uploads','documents','notifications','settings'],
  DOCUMENTATION: ['dashboard','orders','uploads','documents','notifications','settings'],
  CUSTOMER:      ['dashboard','orders','documents','notifications','settings'],
}

const NAV_ITEMS = [
  { key: 'dashboard',     label: 'Dashboard',  icon: LayoutDashboard, to: '/' },
  { key: 'orders',        label: 'Orders',      icon: Package,         to: '/orders' },
  { key: 'uploads',       label: 'Uploads',     icon: Upload,          to: '/uploads' },
  { key: 'documents',     label: 'Documents',   icon: FileText,        to: '/documents' },
  { key: 'notifications', label: 'Alerts',      icon: Bell,            to: '/notifications' },
  { key: 'settings',      label: 'Settings',    icon: Settings,        to: '/settings' },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const allowedKeys = ROLE_NAV[user?.role] ?? []
  const visibleItems = NAV_ITEMS.filter((i) => allowedKeys.includes(i.key))

  function handleLogout() {
    logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  return (
    <aside className="hidden md:flex flex-col w-60 min-h-screen bg-white border-r border-beige-200 shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-beige-200">
        <div className="w-9 h-9 rounded-xl bg-saffron-500 flex items-center justify-center shadow-sm">
          <Truck className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="font-heading font-bold text-gray-900 text-base leading-tight">Live-Trace</p>
          <p className="text-[11px] text-beige-500 font-body">Export Dashboard</p>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {visibleItems.map(({ key, label, icon: Icon, to }) => (
          <NavLink
            key={key}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-saffron-50 text-saffron-700 border border-saffron-200'
                  : 'text-gray-500 hover:bg-beige-100 hover:text-gray-800'
              }`
            }
          >
            <Icon className="w-4.5 h-4.5 shrink-0" size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User profile + logout */}
      <div className="px-3 py-4 border-t border-beige-200 space-y-2">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-cardamom-500 flex items-center justify-center text-white text-xs font-bold font-heading shrink-0">
            {user?.full_name?.slice(0, 2).toUpperCase() ?? 'U'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{user?.full_name}</p>
            <p className="text-[11px] text-gray-400 capitalize">{user?.role?.toLowerCase().replace('_', ' ')}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut size={16} />
          Log Out
        </button>
      </div>
    </aside>
  )
}
