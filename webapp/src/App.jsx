import { Component } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import Dashboard from './pages/Dashboard'
import Technical from './pages/Technical'
import Signals from './pages/Signals'
import News from './pages/News'
import History from './pages/History'
import NavBar from './components/NavBar'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, color: 'white', fontFamily: 'monospace' }}>
          <h2 style={{ color: '#ff4d6a' }}>Something went wrong</h2>
          <pre style={{ fontSize: 12, color: '#aaa', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {this.state.error?.message}
            {'\n\n'}
            {this.state.error?.stack}
            {'\n\n'}
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 16px', background: '#4a9eff', border: 'none', borderRadius: 6, color: 'white', cursor: 'pointer' }}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  useTelegram()

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/technical" element={<Technical />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/news" element={<News />} />
          <Route path="/history" element={<History />} />
        </Routes>
        <NavBar />
      </div>
    </ErrorBoundary>
  )
}
