import { Component, lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { useSubscription } from '../contexts/SubscriptionContext'
// Above-the-fold — eager imports
import PriceWidget from '../components/PriceWidget'
import TickerTape from '../components/TickerTape'
import DataSourceFooter from '../components/DataSourceFooter'
// Below-the-fold — lazy imports (deferred until near viewport)
const PriceChart = lazy(() => import('../components/PriceChart'))
const PredictionCard = lazy(() => import('../components/PredictionCard'))
const QuantPredictionCard = lazy(() => import('../components/QuantPredictionCard'))
const SignalPanel = lazy(() => import('../components/SignalPanel'))
const NewsCarousel = lazy(() => import('../components/NewsCarousel'))
const InfluencerFeed = lazy(() => import('../components/InfluencerFeed'))
const MacroDashboard = lazy(() => import('../components/MacroDashboard'))
const OnChainWidget = lazy(() => import('../components/OnChainWidget'))
const DominanceWidget = lazy(() => import('../components/DominanceWidget'))
const FearGreedWidget = lazy(() => import('../components/FearGreedWidget'))
const SupplyWidget = lazy(() => import('../components/SupplyWidget'))
const DailyBriefingCard = lazy(() => import('../components/DailyBriefingCard'))

class SafeWrap extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error, info) {
    console.error(`[${this.props.name}] crashed:`, error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
          <p className="text-accent-red text-xs">{this.props.t('common:widget.failedToLoad', { name: this.props.name })}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="text-accent-blue text-[10px] mt-1 underline"
          >
            {this.props.t('common:app.retry')}
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function WidgetSkeleton() {
  return <div className="bg-bg-card rounded-2xl h-24 animate-pulse" />
}

function LazyWidget({ children }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px' }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  if (!visible) return <div ref={ref}><WidgetSkeleton /></div>

  return (
    <Suspense fallback={<WidgetSkeleton />}>
      {children}
    </Suspense>
  )
}

const quickIcons = {
  technical: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-6 4 4 5-8" />
    </svg>
  ),
  signals: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20v-6" />
      <path d="M12 10V4" />
      <circle cx="12" cy="12" r="2" />
      <path d="M16.24 7.76a6 6 0 010 8.49" />
      <path d="M7.76 16.24a6 6 0 010-8.49" />
      <path d="M19.07 4.93a10 10 0 010 14.14" />
      <path d="M4.93 19.07a10 10 0 010-14.14" />
    </svg>
  ),
  liquidations: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2c-4 4.5-8 8.5-8 13a8 8 0 0016 0c0-4.5-4-8.5-8-13z" />
      <path d="M12 18a4 4 0 01-4-4c0-2.5 2-4.5 4-7" />
    </svg>
  ),
  powerlaw: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 20Q8 18 12 12t9-9" />
      <path d="M3 20h18" />
      <path d="M3 20V3" />
    </svg>
  ),
  elliott: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 17 7 10 10 14 14 6 17 11 21 4" />
      <path d="M21 4v4h-4" />
    </svg>
  ),
  events: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  coins: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8" />
      <path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5 1-2.5 2s1 2 2.5 2 2.5 1 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5" />
      <path d="M12 6.5v1M12 16.5v1" />
    </svg>
  ),
  advisor: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15.5 14" />
    </svg>
  ),
  news: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M10 6h8M10 10h8M10 14h4" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
  about: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  premium: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  tools: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  resources: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
      <path d="M8 7h8M8 11h6" />
    </svg>
  ),
  learn: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c0 1.66 2.69 3 6 3s6-1.34 6-3v-5" />
    </svg>
  ),
  whales: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12c0-3.5 3-7 9-7s9 3.5 9 7-3 6-9 6-9-2.5-9-6z" />
      <circle cx="8" cy="11" r="1" fill="currentColor" />
      <path d="M21 12c1 1 2 2 2 3" />
    </svg>
  ),
  arbitrage: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 16V4m0 0L3 8m4-4l4 4" />
      <path d="M17 8v12m0 0l4-4m-4 4l-4-4" />
    </svg>
  ),
  listings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
      <circle cx="12" cy="12" r="10" />
    </svg>
  ),
  memecoins: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2" />
      <line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="2.5" />
      <line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="2.5" />
    </svg>
  ),
  alerts: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 01-3.46 0" />
    </svg>
  ),
  briefing: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  game: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12h8" />
      <path d="M12 8v8" />
      <path d="M8.5 8.5l7 7" />
    </svg>
  ),
  smartmoney: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </svg>
  ),
  market: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-4 4 4 5-5" />
    </svg>
  ),
}

const CATEGORIES = [
  {
    titleKey: 'category.trading',
    links: [
      { path: '/signals', labelKey: 'link.signals', icon: 'signals' },
      { path: '/advisor', labelKey: 'link.advisor', icon: 'advisor' },
      { path: '/mock-trading', labelKey: 'link.paperTrade', icon: 'advisor' },
      { path: '/alerts', labelKey: 'link.alerts', icon: 'alerts' },
    ],
  },
  {
    titleKey: 'category.analysis',
    links: [
      { path: '/technical', labelKey: 'link.technical', icon: 'technical' },
      { path: '/powerlaw', labelKey: 'link.powerLaw', icon: 'powerlaw' },
      { path: '/elliott-wave', labelKey: 'link.elliottWave', icon: 'elliott' },
      { path: '/liquidations', labelKey: 'link.liquidations', icon: 'liquidations' },
    ],
  },
  {
    titleKey: 'category.market',
    links: [
      { path: '/markets', labelKey: 'link.markets', icon: 'market' },
      { path: '/coins', labelKey: 'link.coins', icon: 'coins' },
      { path: '/arbitrage', labelKey: 'link.arbitrage', icon: 'arbitrage' },
      { path: '/new-listings', labelKey: 'link.listings', icon: 'listings' },
      { path: '/memecoins', labelKey: 'link.memecoins', icon: 'memecoins' },
      { path: '/whales', labelKey: 'link.whales', icon: 'whales' },
      { path: '/smart-money', labelKey: 'link.smartMoney', icon: 'smartmoney' },
      { path: '/news', labelKey: 'link.news', icon: 'news' },
      { path: '/events', labelKey: 'link.events', icon: 'events' },
      { path: '/history', labelKey: 'link.history', icon: 'history' },
    ],
  },
  {
    titleKey: 'category.more',
    links: [
      { path: '/game', labelKey: 'link.game', icon: 'game' },
      { path: '/briefing', labelKey: 'link.briefing', icon: 'briefing' },
      { path: '/learn', labelKey: 'link.learn', icon: 'learn' },
      { path: '/resources', labelKey: 'link.resources', icon: 'resources' },
      { path: '/tools', labelKey: 'link.tools', icon: 'tools' },
      { path: '/subscription', labelKey: 'link.premium', icon: 'premium', highlight: true },
      { path: '/settings', labelKey: 'link.settings', icon: 'settings' },
      { path: '/about', labelKey: 'link.about', icon: 'about' },
    ],
  },
]

function QuickAccessGrid() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { isAdmin } = useSubscription()

  return (
    <div className="space-y-3">
      {CATEGORIES.map((cat) => {
        const links = cat.titleKey === 'category.more' && isAdmin
          ? [...cat.links, { path: '/admin', labelKey: 'link.admin', icon: 'settings' }]
          : cat.links
        return (
          <div key={cat.titleKey}>
            <h3 className="text-accent-yellow text-[10px] font-semibold uppercase tracking-wider mb-1.5 px-1">{t(cat.titleKey)}</h3>
            <div className="grid grid-cols-4 gap-2">
              {links.map((link) => (
                <button
                  key={link.path}
                  onClick={() => navigate(link.path)}
                  className="bg-bg-card rounded-xl border border-accent-yellow/10 p-3 flex flex-col items-center gap-1.5 hover:border-accent-yellow/25 active:scale-95 transition-all"
                >
                  <span className="w-5 h-5 text-accent-yellow">{quickIcons[link.icon]}</span>
                  <span className="text-[10px] text-accent-yellow/80 font-medium leading-tight text-center">{t(link.labelKey)}</span>
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function CouncilCTA() {
  const { t } = useTranslation('common')
  const tg = window.Telegram?.WebApp
  const openCommunity = () => {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink('https://t.me/+-72wnR04tPUyZmIy')
    } else {
      window.open('https://t.me/+-72wnR04tPUyZmIy', '_blank')
    }
  }

  return (
    <button
      onClick={openCommunity}
      className="w-full flex items-center gap-3 bg-bg-card rounded-xl border border-accent-blue/15 p-4 hover:border-accent-blue/30 transition-colors text-left"
    >
      <div className="w-9 h-9 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2L11 13" />
          <path d="M22 2L15 22L11 13L2 9L22 2Z" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
        <p className="text-text-muted text-[10px]">{t('paywall.councilDesc')}</p>
      </div>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </button>
  )
}

function DashboardPaywallCTA() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { tier } = useSubscription()
  const hadTrial = tier === 'expired' || tier === 'trial_expired'

  const tg = window.Telegram?.WebApp
  const openCommunity = () => {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink('https://t.me/+-72wnR04tPUyZmIy')
    } else {
      window.open('https://t.me/+-72wnR04tPUyZmIy', '_blank')
    }
  }

  return (
    <div className="space-y-4">
      {hadTrial && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-xl px-4 py-2">
          <p className="text-accent-red text-xs font-medium">{t('paywall.trialExpired')}</p>
        </div>
      )}
      <div className="bg-bg-card rounded-2xl border border-accent-blue/20 p-5 text-center">
        <div className="w-12 h-12 rounded-full bg-accent-yellow/10 flex items-center justify-center mx-auto mb-3">
          <svg className="w-6 h-6 text-accent-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        </div>
        <h3 className="text-text-primary text-sm font-bold mb-1">{t('paywall.unlockPrompt')}</h3>
        <ul className="text-text-muted text-xs space-y-1 mb-4 text-left max-w-xs mx-auto">
          {['paywall.features.predictions', 'paywall.features.signals', 'paywall.features.advisor', 'paywall.features.alerts'].map((key) => (
            <li key={key} className="flex items-center gap-2">
              <svg className="w-3 h-3 text-accent-green shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              {t(key)}
            </li>
          ))}
        </ul>
        <button
          onClick={() => navigate('/settings')}
          className="w-full py-2.5 rounded-xl text-sm font-bold text-white bg-accent-blue active:scale-95 transition-all mb-2"
        >
          {hadTrial ? t('paywall.subscribe') : t('paywall.startTrial')}
        </button>
        <button
          onClick={() => navigate('/subscription')}
          className="text-accent-blue text-xs font-medium"
        >
          {t('paywall.viewPlans')}
        </button>
      </div>

      {/* Community CTA */}
      <button
        onClick={openCommunity}
        className="w-full flex items-center gap-3 bg-bg-card rounded-xl border border-accent-blue/15 p-4 hover:border-accent-blue/30 transition-colors text-left"
      >
        <div className="w-9 h-9 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
          <p className="text-text-muted text-[10px]">{t('paywall.councilDesc')}</p>
        </div>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  )
}

export default function Dashboard() {
  const { t } = useTranslation(['common', 'dashboard'])
  const { isPremium, loading } = useSubscription()

  return (
    <div className="px-4 pt-4 space-y-4 dashboard-stagger">
      <header className="flex items-center justify-between mb-2">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <span className="text-xl">{'\u20BF'}</span> <span className="text-shimmer-gold">{t('common:app.title')}</span>
        </h1>
        <span className="text-text-muted text-xs pulse-glow">{t('common:app.live')}</span>
      </header>

      {(loading || isPremium) && <TickerTape />}

      <QuickAccessGrid />

      <SafeWrap name="PriceWidget" t={t}>
        <PriceWidget />
      </SafeWrap>

      <SafeWrap name="PriceChart" t={t}>
        <Suspense fallback={<WidgetSkeleton />}>
          <PriceChart />
        </Suspense>
      </SafeWrap>

      {/* Paywall CTA for free users — shown below price */}
      {!loading && !isPremium && <DashboardPaywallCTA />}

      {/* Premium content — only shown for premium users */}
      {(loading || isPremium) && (
        <>
          {/* Dual Predictions */}
          <div className="space-y-3">
            <LazyWidget>
              <SafeWrap name="AI Prediction" t={t}>
                <PredictionCard />
              </SafeWrap>
            </LazyWidget>
            <LazyWidget>
              <SafeWrap name="Quant Prediction" t={t}>
                <QuantPredictionCard />
              </SafeWrap>
            </LazyWidget>
          </div>

          <LazyWidget>
            <SafeWrap name="DailyBriefing" t={t}>
              <DailyBriefingCard />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="SignalPanel" t={t}>
              <SignalPanel />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="FearGreedWidget" t={t}>
              <FearGreedWidget />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="NewsCarousel" t={t}>
              <NewsCarousel />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="InfluencerFeed" t={t}>
              <InfluencerFeed />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="OnChainWidget" t={t}>
              <OnChainWidget />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="SupplyWidget" t={t}>
              <SupplyWidget />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="DominanceWidget" t={t}>
              <DominanceWidget />
            </SafeWrap>
          </LazyWidget>

          <LazyWidget>
            <SafeWrap name="MacroDashboard" t={t}>
              <MacroDashboard />
            </SafeWrap>
          </LazyWidget>

          <DataSourceFooter sources={['binance', 'coingecko', 'cryptopanic', 'rss', 'reddit', 'blockchain', 'mempool', 'feargreed', 'alphavantage', 'coinglass', 'defillama', 'deribit', 'ai']} />

          {/* Community CTA for premium users */}
          <CouncilCTA />
        </>
      )}

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        {t('common:app.disclaimer')}
      </p>
    </div>
  )
}
