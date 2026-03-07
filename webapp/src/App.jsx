import { Component, lazy, Suspense, useEffect } from 'react'
import { Routes, Route, useLocation, useNavigationType } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import { useLanguageInit } from './i18n/useLanguage'
import { SubscriptionProvider, useSubscription } from './contexts/SubscriptionContext'
import NavBar from './components/NavBar'
import PaywallOverlay from './components/PaywallOverlay'
import WarmupBanner from './components/WarmupBanner'

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
const MarketOverview = lazy(() => import('./pages/MarketOverview'))
const AddressDistribution = lazy(() => import('./pages/AddressDistribution'))

// Prefetch top page chunks during idle time
const PAGE_PREFETCHES = [
  () => import('./pages/Dashboard'),
  () => import('./pages/Technical'),
  () => import('./pages/Signals'),
  () => import('./pages/News'),
  () => import('./pages/History'),
  () => import('./pages/PowerLaw'),
  () => import('./pages/Liquidations'),
]

function usePrefetchPages() {
  useEffect(() => {
    const ric = typeof requestIdleCallback === 'function' ? requestIdleCallback : (cb) => setTimeout(cb, 200)
    const id = ric(() => {
      PAGE_PREFETCHES.forEach(load => load())
    })
    return () => {
      if (typeof cancelIdleCallback === 'function') cancelIdleCallback(id)
    }
  }, [])
}

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
  const navType = useNavigationType()
  useEffect(() => {
    if (navType === 'PUSH') window.scrollTo(0, 0)
  }, [pathname, navType])
  return null
}

function PremiumRoute({ children }) {
  const { isPremium, isAdmin, loading } = useSubscription()
  if (loading) return <PageLoader />
  if (!isPremium && !isAdmin) return <PaywallOverlay />
  return children
}

export default function App() {
  useLanguageInit()
  usePrefetchPages()

  return (
    <ErrorBoundary>
      <WarmupBanner />
      <SubscriptionProvider>
        <ScrollToTop />
        <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
          <div className="page-enter">
          <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Free routes */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/more" element={<More />} />
            <Route path="/subscription" element={<Subscription />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/about" element={<About />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/partner/:code" element={<PartnerDashboard />} />

            {/* Premium routes — gated */}
            <Route path="/technical" element={<PremiumRoute><Technical /></PremiumRoute>} />
            <Route path="/signals" element={<PremiumRoute><Signals /></PremiumRoute>} />
            <Route path="/liquidations" element={<PremiumRoute><Liquidations /></PremiumRoute>} />
            <Route path="/powerlaw" element={<PremiumRoute><PowerLaw /></PremiumRoute>} />
            <Route path="/events" element={<PremiumRoute><EventMemory /></PremiumRoute>} />
            <Route path="/whales" element={<PremiumRoute><Whales /></PremiumRoute>} />
            <Route path="/arbitrage" element={<PremiumRoute><Arbitrage /></PremiumRoute>} />
            <Route path="/new-listings" element={<PremiumRoute><NewListings /></PremiumRoute>} />
            <Route path="/memecoins" element={<PremiumRoute><Memecoins /></PremiumRoute>} />
            <Route path="/elliott-wave" element={<PremiumRoute><ElliottWave /></PremiumRoute>} />
            <Route path="/tools" element={<PremiumRoute><Tools /></PremiumRoute>} />
            <Route path="/resources" element={<PremiumRoute><Resources /></PremiumRoute>} />
            <Route path="/learn" element={<PremiumRoute><Learn /></PremiumRoute>} />
            <Route path="/coins" element={<PremiumRoute><Coins /></PremiumRoute>} />
            <Route path="/coins/search" element={<PremiumRoute><CoinSearch /></PremiumRoute>} />
            <Route path="/coins/report/:address" element={<PremiumRoute><CoinReport /></PremiumRoute>} />
            <Route path="/coins/:coinId" element={<PremiumRoute><CoinDetail /></PremiumRoute>} />
            <Route path="/history" element={<PremiumRoute><History /></PremiumRoute>} />
            <Route path="/news" element={<PremiumRoute><News /></PremiumRoute>} />
            <Route path="/advisor" element={<PremiumRoute><Advisor /></PremiumRoute>} />
            <Route path="/mock-trading" element={<PremiumRoute><MockTrading /></PremiumRoute>} />
            <Route path="/alerts" element={<PremiumRoute><PriceAlerts /></PremiumRoute>} />
            <Route path="/briefing" element={<PremiumRoute><Briefing /></PremiumRoute>} />
            <Route path="/game" element={<PremiumRoute><PredictionGame /></PremiumRoute>} />
            <Route path="/smart-money" element={<PremiumRoute><SmartMoney /></PremiumRoute>} />
            <Route path="/markets" element={<PremiumRoute><MarketOverview /></PremiumRoute>} />
            <Route path="/address-distribution" element={<PremiumRoute><AddressDistribution /></PremiumRoute>} />
          </Routes>
          </Suspense>
          </div>
          <NavBar />
        </div>
      </SubscriptionProvider>
    </ErrorBoundary>
  )
}
