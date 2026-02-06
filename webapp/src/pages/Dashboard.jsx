import PriceWidget from '../components/PriceWidget'
import PriceChart from '../components/PriceChart'
import PredictionCard from '../components/PredictionCard'
import SignalPanel from '../components/SignalPanel'
import SentimentGauge from '../components/SentimentGauge'
import NewsCarousel from '../components/NewsCarousel'
import InfluencerFeed from '../components/InfluencerFeed'
import MacroDashboard from '../components/MacroDashboard'

export default function Dashboard() {
  return (
    <div className="px-4 pt-4 space-y-4">
      <header className="flex items-center justify-between mb-2">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <span className="text-xl">₿</span> BTC Oracle
        </h1>
        <span className="text-text-muted text-xs pulse-glow">LIVE</span>
      </header>

      <PriceWidget />
      <PriceChart />
      <PredictionCard />
      <SignalPanel />
      <SentimentGauge />
      <NewsCarousel />
      <InfluencerFeed />
      <MacroDashboard />

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        This is not financial advice. Predictions are ML-generated and may be incorrect.
        Always do your own research. Past accuracy does not guarantee future results.
      </p>
    </div>
  )
}
