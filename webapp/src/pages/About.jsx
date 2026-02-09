export default function About() {
  return (
    <div className="px-4 pt-4 space-y-3 pb-4">
      {/* Hero */}
      <div className="bg-bg-card rounded-2xl p-5 border border-white/5 text-center slide-up">
        <img src="/btc-seer.jpeg" alt="BTC Seer" className="w-full rounded-xl mb-4" />
        <h1 className="text-xl font-bold mb-1">BTC Seer</h1>
        <p className="text-text-secondary text-sm">AI-Powered Bitcoin Intelligence</p>
        <p className="text-text-muted text-[11px] mt-2">
          Real-time predictions, trading signals, and market analysis — all driven by machine learning.
        </p>
      </div>

      {/* What is BTC Seer */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">WHAT IS BTC SEER?</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            BTC Seer is an ML-powered Bitcoin prediction platform that analyzes <span className="text-text-secondary font-semibold">69+ features</span> from
            news sentiment, market data, on-chain metrics, social signals, and macroeconomic indicators.
          </p>
          <p>
            It generates predictions across <span className="text-text-secondary font-semibold">5 timeframes</span> — 1H, 4H, 24H, 1W, and 1MO — using
            multiple AI models working together: LSTM, Temporal Fusion Transformer, XGBoost, Sentiment Analysis, and Quant Theory.
          </p>
        </div>
      </div>

      {/* How It Helps */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">HOW IT HELPS YOU</h3>
        <div className="space-y-2">
          {[
            { icon: '📊', title: 'Prediction Cards', desc: 'Confidence scores to gauge market direction across multiple timeframes' },
            { icon: '📈', title: 'Trading Signals', desc: 'Entry, target, and stop-loss levels with AI-calculated confidence' },
            { icon: '📐', title: 'Power Law Analysis', desc: 'Long-term fair value model to understand where BTC stands historically' },
            { icon: '💥', title: 'Liquidation Map', desc: 'See where leveraged positions cluster and where liquidation cascades may trigger' },
            { icon: '📰', title: 'News Sentiment', desc: 'Real-time tracking of what the market is feeling through news analysis' },
            { icon: '🎯', title: 'Accuracy Tracking', desc: 'Every prediction is evaluated and scored — full transparency on model performance' },
          ].map((item) => (
            <div key={item.title} className="flex items-start gap-3 p-2 rounded-xl bg-white/[0.02]">
              <span className="text-lg mt-0.5">{item.icon}</span>
              <div>
                <div className="text-text-primary text-xs font-semibold">{item.title}</div>
                <div className="text-text-muted text-[10px]">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* How the AI Works */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">HOW THE AI WORKS</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          <div className="flex items-start gap-2">
            <span className="text-accent-blue font-bold text-xs mt-0.5">1</span>
            <p><span className="text-text-secondary font-semibold">Continuous Learning:</span> Models retrain every 6 hours with the latest market data, adapting to changing conditions.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-accent-blue font-bold text-xs mt-0.5">2</span>
            <p><span className="text-text-secondary font-semibold">Phrase Analyzer:</span> Learns which news words and phrases historically move the market, improving sentiment accuracy over time.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-accent-blue font-bold text-xs mt-0.5">3</span>
            <p><span className="text-text-secondary font-semibold">A/B Testing:</span> New model candidates compete against production models before promotion — only the best get deployed.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-accent-blue font-bold text-xs mt-0.5">4</span>
            <p><span className="text-text-secondary font-semibold">Ensemble Voting:</span> Multiple models vote on each prediction, reducing individual model bias and improving reliability.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-accent-blue font-bold text-xs mt-0.5">5</span>
            <p><span className="text-text-secondary font-semibold">Accuracy Tracking:</span> Every prediction is evaluated against actual price movements and scored for continuous improvement.</p>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">FEATURES</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { icon: '🧠', label: 'AI Predictions' },
            { icon: '📉', label: 'Quant Theory' },
            { icon: '📐', label: 'Power Law' },
            { icon: '💥', label: 'Liquidation Map' },
            { icon: '📰', label: 'News Sentiment' },
            { icon: '📈', label: 'Trading Signals' },
            { icon: '🎯', label: 'Accuracy Tracking' },
            { icon: '🔑', label: 'API Access' },
          ].map((f) => (
            <div key={f.label} className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02]">
              <span className="text-base">{f.icon}</span>
              <span className="text-text-primary text-xs font-medium">{f.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* API Access */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">API ACCESS</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            BTC Seer offers a free API for developers and traders. Get your API key through the
            Telegram bot using the <span className="text-accent-blue font-mono">/apikey</span> command.
          </p>
          <p>
            All tiers are <span className="text-text-secondary font-semibold">free during beta</span>. Access predictions,
            signals, market data, and more programmatically.
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-yellow/15">
        <h3 className="text-accent-yellow text-xs font-semibold mb-2">DISCLAIMER</h3>
        <p className="text-text-muted text-[10px]">
          BTC Seer is not financial advice. All predictions, signals, and analysis are for
          educational and informational purposes only. Cryptocurrency trading carries significant
          risk. Always do your own research (DYOR) and never invest more than you can afford to lose.
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  )
}
