import { Component, lazy, Suspense, useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import { useLanguageInit } from './i18n/useLanguage'
import { api } from './utils/api'
import NavBar from './components/NavBar'

// Lazy-load all pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Technical = lazy(() => import('./pages/Technical'))
const Signals = lazy(() => import('./pages/Signals'))
const News = lazy(() => import('./pages/News'))
const History = lazy(() => import('./pages/History'))
const PowerLaw = lazy(() => import('./pages/PowerLaw'))
const Liquidations = lazy(() => import('./pages/Liquidations'))
const About = lazy(() => import('./pages/About'))
const EventMemory = lazy(() => import('./pages/EventMemory'))
const ElliottWave = lazy(() => import('./pages/ElliottWave'))
const Advisor = lazy(() => import('./pages/Advisor'))
const MockTrading = lazy(() => import('./pages/MockTrading'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const More = lazy(() => import('./pages/More'))
const Settings = lazy(() => import('./pages/Settings'))
const Subscription = lazy(() => import('./pages/Subscription'))
const Coins = lazy(() => import('./pages/Coins'))
const CoinDetail = lazy(() => import('./pages/CoinDetail'))
const CoinSearch = lazy(() => import('./pages/CoinSearch'))
const CoinReport = lazy(() => import('./pages/CoinReport'))
const Tools = lazy(() => import('./pages/Tools'))
const Resources = lazy(() => import('./pages/Resources'))
const Learn = lazy(() => import('./pages/Learn'))
const Whales = lazy(() => import('./pages/Whales'))
const Arbitrage = lazy(() => import('./pages/Arbitrage'))
const NewListings = lazy(() => import('./pages/NewListings'))
const Memecoins = lazy(() => import('./pages/Memecoins'))
const PartnerDashboard = lazy(() => import('./pages/PartnerDashboard'))
const PriceAlerts = lazy(() => import('./pages/PriceAlerts'))
const Briefing = lazy(() => import('./pages/Briefing'))
const PredictionGame = lazy(() => import('./pages/PredictionGame'))
const SmartMoney = lazy(() => import('./pages/SmartMoney'))

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

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  const { tg } = useTelegram()
  const location = useLocation()
  useLanguageInit()

  // Auto-register user when Mini App opens
  useEffect(() => {
    if (tg?.initData) {
      api.registerUser(tg.initData).catch(() => {})
    }
  }, [tg])

  return (
    <ErrorBoundary>
      <ScrollToTop />
      <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
        <div key={location.pathname} className="page-enter">
        <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          {/* Analysis group */}
          <Route path="/technical" element={<Technical />} />
          <Route path="/signals" element={<Signals />} />
          {/* Markets group */}
          <Route path="/liquidations" element={<Liquidations />} />
          <Route path="/powerlaw" element={<PowerLaw />} />
          <Route path="/events" element={<EventMemory />} />
          <Route path="/whales" element={<Whales />} />
          <Route path="/arbitrage" element={<Arbitrage />} />
          <Route path="/new-listings" element={<NewListings />} />
          <Route path="/memecoins" element={<Memecoins />} />
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
          <Route path="/subscription" element={<Subscription />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/partner/:code" element={<PartnerDashboard />} />
          {/* New features */}
          <Route path="/alerts" element={<PriceAlerts />} />
          <Route path="/briefing" element={<Briefing />} />
          <Route path="/game" element={<PredictionGame />} />
          <Route path="/smart-money" element={<SmartMoney />} />
        </Routes>
        </Suspense>
        </div>
        <NavBar />
      </div>
    </ErrorBoundary>
  )
}
