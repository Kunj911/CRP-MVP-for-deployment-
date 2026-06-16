import { useEffect } from 'react'
import { Toaster } from 'sonner'
import AppRouter from './router/index.jsx'
import ErrorBoundary from './components/ui/ErrorBoundary.jsx'
import useAuthStore from './store/authStore'

/**
 * App root component with security hardening:
 *   - ErrorBoundary: catches runtime errors, prevents blank screens
 *   - Session bootstrap: restores auth state on page reload via HttpOnly cookie
 *   - Loading state: shows spinner until bootstrap completes
 */
export default function App() {
  const isSessionLoading = useAuthStore((s) => s.isSessionLoading)
  const bootstrapSession = useAuthStore((s) => s.bootstrapSession)

  // On mount: attempt to restore session from HttpOnly refresh cookie
  useEffect(() => {
    bootstrapSession()
  }, [bootstrapSession])

  // Show loading screen while session bootstrap is in progress
  if (isSessionLoading) {
    return (
      <div className="min-h-screen bg-agri-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <img src="/fittree-logo.png" alt="Fittree International LLP" className="h-10 w-auto object-contain mb-2" />
          <div className="w-10 h-10 border-3 border-forest-700 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-body">Loading Live-Trace...</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            fontFamily: 'Inter, sans-serif',
            borderRadius: '10px',
            border: '1px solid #DCE8D8',
            boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          },
          success: {
            iconTheme: { primary: '#2E7D32', secondary: '#E8F5E9' },
          },
          error: {
            iconTheme: { primary: '#DC2626', secondary: '#FEE2E2' },
          },
        }}
      />
    </ErrorBoundary>
  )
}
