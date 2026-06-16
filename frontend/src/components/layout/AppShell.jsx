import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import MobileNav from './MobileNav'

export default function AppShell() {
  return (
    <div className="flex min-h-screen bg-agri-texture">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 p-4 md:p-6 pb-20 md:pb-6 overflow-auto animate-fade-in">
          <Outlet />
        </main>
        <footer className="hidden md:block px-6 py-3 border-t border-agri-200 bg-white">
          <div className="flex items-center justify-between text-xs text-slate-400 font-body">
            <span>&copy; {new Date().getFullYear()} Fittree International LLP</span>
            <span>Powered by Live-Trace</span>
          </div>
        </footer>
      </div>
      <MobileNav />
    </div>
  )
}
