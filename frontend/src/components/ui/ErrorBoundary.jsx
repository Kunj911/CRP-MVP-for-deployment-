import { Component } from 'react'

/**
 * React Error Boundary — catches runtime errors in the component tree
 * and renders a user-friendly fallback instead of a blank white screen.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <AppRouter />
 *   </ErrorBoundary>
 *
 * Note: Error Boundaries MUST be class components (React limitation).
 * They do NOT catch:
 *   - Event handler errors (use try/catch)
 *   - Async errors (use .catch() or try/catch in async functions)
 *   - Server-side rendering errors
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    // Log to console for debugging
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
    
    // In production, you'd send this to Sentry/DataDog:
    // Sentry.captureException(error, { extra: errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-agri-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
            {/* Error icon */}
            <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-50 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h2 className="font-heading font-bold text-xl text-slate-900 mb-2">
              Something went wrong
            </h2>
            <p className="text-sm text-slate-500 font-body mb-6 leading-relaxed">
              An unexpected error occurred. The Live-Trace team has been
              notified. You can try reloading the page.
            </p>

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleGoHome}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-body"
              >
                Go Home
              </button>
              <button
                onClick={this.handleReload}
                className="px-4 py-2 text-sm font-medium text-white bg-forest-700 rounded-lg hover:bg-forest-800 transition-colors font-body"
              >
                Reload Page
              </button>
            </div>

            {/* Show error details in development only */}
            {import.meta.env.DEV && this.state.error && (
              <details className="mt-6 text-left">
                <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 font-body">
                  Error details (dev only)
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-red-600 overflow-auto max-h-48 font-mono">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
