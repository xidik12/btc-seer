import { Component } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import Dashboard from './pages/Dashboard'
import Technical from './pages/Technical'
import Signals from './pages/Signals'
import News from './pages/News'
import History from './pages/History'
import PowerLaw from './pages/PowerLaw'
import Liquidations from './pages/Liquidations'
import About from './pages/About'
import EventMemory from './pages/EventMemory'
import ElliottWave from './pages/ElliottWave'
import Advisor from './pages/Advisor'
import MockTrading from './pages/MockTrading'
import AdminDashboard from './pages/AdminDashboard'
import More from './pages/More'
import Settings from './pages/Settings'
import Coins from './pages/Coins'
import CoinDetail from './pages/CoinDetail'
import CoinSearch from './pages/CoinSearch'
import CoinReport from './pages/CoinReport'
import Tools from './pages/Tools'
import Resources from './pages/Resources'
import Learn from './pages/Learn'
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
  const location = useLocation()

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
        <div key={location.pathname} className="page-enter">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          {/* Analysis group */}
          <Route path="/technical" element={<Technical />} />
          <Route path="/signals" element={<Signals />} />
          {/* Markets group */}
          <Route path="/liquidations" element={<Liquidations />} />
          <Route path="/powerlaw" element={<PowerLaw />} />
          <Route path="/events" element={<EventMemory />} />
          <Route path="/elliott-wave" element={<ElliottWave />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/resources" element={<Resources />} />
          <Route path="/learn" element={<Learn />} />
          {/* Coins */}
          <Route path="/coins" element={<Coins />} />
          <Route path="/coins/search" element={<CoinSearch />} />
          <Route path="/coins/report/:address" element={<CoinReport />} />
          <Route path="/coins/:coinId" element={<CoinDetail />} />
          {/* History */}
          <Route path="/history" element={<History />} />
          {/* More group */}
          <Route path="/more" element={<More />} />
          <Route path="/news" element={<News />} />
          <Route path="/advisor" element={<Advisor />} />
          <Route path="/mock-trading" element={<MockTrading />} />
          <Route path="/about" element={<About />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
        </div>
        <NavBar />
      </div>
    </ErrorBoundary>
  )
}
