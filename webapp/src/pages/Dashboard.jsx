import PriceWidget from '../components/PriceWidget'
import PriceChart from '../components/PriceChart'
import PredictionCard from '../components/PredictionCard'
import QuantPredictionCard from '../components/QuantPredictionCard'
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

      {/* Dual Prediction System */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <div className="h-px flex-1 bg-white/5" />
          <span className="text-text-muted text-[10px] font-semibold tracking-widest">PREDICTIONS</span>
          <div className="h-px flex-1 bg-white/5" />
        </div>

        {/* Prediction A: ML Ensemble (data-driven) */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5 px-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-blue" />
            <span className="text-text-muted text-[10px] font-semibold tracking-wider">ML ENSEMBLE</span>
            <span className="text-text-muted text-[9px] opacity-60">LSTM + XGBoost + Sentiment</span>
          </div>
          <PredictionCard />
        </div>

        {/* Prediction B: Quant Theory (formula-driven) */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5 px-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-purple" />
            <span className="text-text-muted text-[10px] font-semibold tracking-wider">QUANT THEORY</span>
            <span className="text-text-muted text-[9px] opacity-60">15 proven algorithms combined</span>
          </div>
          <QuantPredictionCard />
        </div>
      </div>

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
