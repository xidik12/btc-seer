import { Component } from 'react'
import { useNavigate } from 'react-router-dom'
import PriceWidget from '../components/PriceWidget'
import PriceChart from '../components/PriceChart'
import PredictionCard from '../components/PredictionCard'
import QuantPredictionCard from '../components/QuantPredictionCard'
import SignalPanel from '../components/SignalPanel'
import SentimentGauge from '../components/SentimentGauge'
import NewsCarousel from '../components/NewsCarousel'
import InfluencerFeed from '../components/InfluencerFeed'
import MacroDashboard from '../components/MacroDashboard'
import OnChainWidget from '../components/OnChainWidget'
import DominanceWidget from '../components/DominanceWidget'

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
          <p className="text-accent-red text-xs">{this.props.name} failed to load</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="text-accent-blue text-[10px] mt-1 underline"
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
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
      <path d="M12 2a7 7 0 017 7c0 3-2 5.5-4 7.5L12 20l-3-3.5C7 14.5 5 12 5 9a7 7 0 017-7z" />
      <circle cx="12" cy="9" r="2.5" />
    </svg>
  ),
}

const QUICK_LINKS = [
  { path: '/technical', label: 'Technical', icon: 'technical' },
  { path: '/signals', label: 'Signals', icon: 'signals' },
  { path: '/liquidations', label: 'Liquidations', icon: 'liquidations' },
  { path: '/powerlaw', label: 'Power Law', icon: 'powerlaw' },
  { path: '/elliott-wave', label: 'Elliott Wave', icon: 'elliott' },
  { path: '/events', label: 'Events', icon: 'events' },
  { path: '/coins', label: 'Coins', icon: 'coins' },
  { path: '/advisor', label: 'Advisor', icon: 'advisor' },
]

function QuickAccessGrid() {
  const navigate = useNavigate()
  return (
    <div className="grid grid-cols-4 gap-2">
      {QUICK_LINKS.map((link) => (
        <button
          key={link.path}
          onClick={() => navigate(link.path)}
          className="bg-bg-card rounded-xl border border-white/5 p-3 flex flex-col items-center gap-1.5 hover:border-white/15 active:scale-95 transition-all"
        >
          <span className="w-5 h-5 text-text-secondary">{quickIcons[link.icon]}</span>
          <span className="text-[10px] text-text-secondary font-medium leading-tight text-center">{link.label}</span>
        </button>
      ))}
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="px-4 pt-4 space-y-4">
      <header className="flex items-center justify-between mb-2">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <span className="text-xl">₿</span> BTC Oracle
        </h1>
        <span className="text-text-muted text-xs pulse-glow">LIVE</span>
      </header>

      <QuickAccessGrid />

      <SafeWrap name="PriceWidget">
        <PriceWidget />
      </SafeWrap>

      <SafeWrap name="PriceChart">
        <PriceChart />
      </SafeWrap>

      {/* Dual Predictions */}
      <div className="space-y-3">
        <SafeWrap name="AI Prediction">
          <PredictionCard />
        </SafeWrap>
        <SafeWrap name="Quant Prediction">
          <QuantPredictionCard />
        </SafeWrap>
      </div>

      <SafeWrap name="SignalPanel">
        <SignalPanel />
      </SafeWrap>

      <SafeWrap name="SentimentGauge">
        <SentimentGauge />
      </SafeWrap>

      <SafeWrap name="NewsCarousel">
        <NewsCarousel />
      </SafeWrap>

      <SafeWrap name="InfluencerFeed">
        <InfluencerFeed />
      </SafeWrap>

      <SafeWrap name="OnChainWidget">
        <OnChainWidget />
      </SafeWrap>

      <SafeWrap name="DominanceWidget">
        <DominanceWidget />
      </SafeWrap>

      <SafeWrap name="MacroDashboard">
        <MacroDashboard />
      </SafeWrap>

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        This is not financial advice. Predictions are ML-generated and may be incorrect.
        Always do your own research. Past accuracy does not guarantee future results.
      </p>
    </div>
  )
}
