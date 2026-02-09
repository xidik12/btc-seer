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

const QUICK_LINKS = [
  { path: '/technical', label: 'Technical', icon: '\u{1F4CA}' },
  { path: '/signals', label: 'Signals', icon: '\u{1F4E1}' },
  { path: '/liquidations', label: 'Liquidations', icon: '\u{1F525}' },
  { path: '/powerlaw', label: 'Power Law', icon: '\u{1F4CF}' },
  { path: '/elliott-wave', label: 'Elliott Wave', icon: '\u{1F30A}' },
  { path: '/events', label: 'Events', icon: '\u{26A1}' },
  { path: '/coins', label: 'Coins', icon: '\u{1FA99}' },
  { path: '/advisor', label: 'Advisor', icon: '\u{1F9E0}' },
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
          <span className="text-lg">{link.icon}</span>
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
