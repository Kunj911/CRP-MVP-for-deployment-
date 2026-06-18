import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import AppShell from '../components/layout/AppShell'

const LoginPage = lazy(() => import('../pages/auth/LoginPage'))
const AdminDashboard = lazy(() => import('../pages/dashboard/AdminDashboard'))
const CustomerDashboard = lazy(() => import('../pages/dashboard/CustomerDashboard'))
const OrdersListPage = lazy(() => import('../pages/orders/OrdersListPage'))
const OrderDetailPage = lazy(() => import('../pages/orders/OrderDetailPage'))
const CreateOrderPage = lazy(() => import('../pages/orders/CreateOrderPage'))
const UploadPage = lazy(() => import('../pages/uploads/UploadPage'))
const DocumentVaultPage = lazy(() => import('../pages/documents/DocumentVaultPage'))
const NotificationsPage = lazy(() => import('../pages/notifications/NotificationsPage'))
const SettingsPage = lazy(() => import('../pages/settings/SettingsPage'))
const CustomersPage = lazy(() => import('../pages/customers/CustomersPage'))

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
      <Suspense
        fallback={
          <div className="min-h-screen bg-agri-50 flex items-center justify-center">
            <div className="w-10 h-10 border-3 border-forest-700 border-t-transparent rounded-full animate-spin" />
          </div>
        }
      >
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
              <Route path="customers" element={<CustomersPage />} />
              <Route path="documents" element={<DocumentVaultPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
