import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import AppShell from '../components/layout/AppShell'
import LoginPage from '../pages/auth/LoginPage'
import AdminDashboard from '../pages/dashboard/AdminDashboard'
import CustomerDashboard from '../pages/dashboard/CustomerDashboard'
import OrdersListPage from '../pages/orders/OrdersListPage'
import OrderDetailPage from '../pages/orders/OrderDetailPage'
import CreateOrderPage from '../pages/orders/CreateOrderPage'
import UploadPage from '../pages/uploads/UploadPage'
import DocumentVaultPage from '../pages/documents/DocumentVaultPage'
import NotificationsPage from '../pages/notifications/NotificationsPage'
import SettingsPage from '../pages/settings/SettingsPage'

/* Protected route — redirects to /login if no token */
function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated())
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}

/* Role-aware dashboard router */
function DashboardRouter() {
  const user = useAuthStore((s) => s.user)
  if (!user) return null
  return user.role === 'CUSTOMER'
    ? <CustomerDashboard />
    : <AdminDashboard />
}

/* Role guard component */
function RoleRoute({ allow, children }) {
  const user = useAuthStore((s) => s.user)
  if (!user || !allow.includes(user.role)) {
    return <Navigate to="/" replace />
  }
  return children
}

export { RoleRoute }

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<DashboardRouter />} />
            <Route path="orders" element={<OrdersListPage />} />
            <Route path="orders/new" element={
              <RoleRoute allow={['SUPER_ADMIN','ADMIN']}>
                <CreateOrderPage />
              </RoleRoute>
            } />
            <Route path="orders/:orderId" element={<OrderDetailPage />} />
            <Route path="uploads" element={
              <RoleRoute allow={['SUPER_ADMIN','ADMIN','WAREHOUSE','QA','DOCUMENTATION']}>
                <UploadPage />
              </RoleRoute>
            } />
            <Route path="documents" element={<DocumentVaultPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
