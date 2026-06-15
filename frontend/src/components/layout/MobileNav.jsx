import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Package, Upload, FileText, Bell } from 'lucide-react'
import useAuthStore from '../../store/authStore'

const TABS = [
  { to: '/',             icon: LayoutDashboard, label: 'Home',  end: true },
  { to: '/orders',       icon: Package,         label: 'Orders'           },
  { to: '/uploads',      icon: Upload,          label: 'Upload', staffOnly: true },
  { to: '/documents',    icon: FileText,        label: 'Docs'             },
  { to: '/notifications',icon: Bell,            label: 'Alerts'           },
]

export default function MobileNav() {
  const isCustomer = useAuthStore((s) => s.isCustomer())

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-agri-200 flex h-14">
      {TABS
        .filter((t) => !(t.staffOnly && isCustomer))
        .map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
                isActive ? 'text-forest-700' : 'text-slate-400'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={20} strokeWidth={isActive ? 2.5 : 1.8} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))
      }
    </nav>
  )
}
