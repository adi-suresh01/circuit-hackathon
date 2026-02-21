import React from 'react'

class ErrorBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('App error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h1 className="text-lg font-semibold text-slate-800 mb-2">Something went wrong</h1>
            <p className="text-sm text-slate-600 mb-4">
              The app hit an error. If the Copilot sidebar is enabled, make sure the backend is running at{' '}
              <code className="text-xs bg-slate-100 px-1 rounded">VITE_COPILOT_RUNTIME_URL</code> (default: localhost:8000).
            </p>
            <pre className="text-xs bg-slate-100 rounded-lg p-3 overflow-auto max-h-32 text-slate-700 mb-4">
              {this.state.error?.message ?? String(this.state.error)}
            </pre>
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
