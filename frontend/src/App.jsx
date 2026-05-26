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
      <div className="min-h-screen bg-beige-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-saffron-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500 font-body">Restoring session...</p>
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
          },
        }}
      />
    </ErrorBoundary>
  )
}
