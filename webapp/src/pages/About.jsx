export default function About() {
  return (
    <div className="px-4 pt-4 space-y-3 pb-4">
      {/* Hero */}
      <div className="bg-bg-card rounded-2xl p-5 border border-white/5 text-center slide-up">
        <img src="/btc-seer.jpeg" alt="BTC Seer" className="w-full rounded-xl mb-4" />
        <h1 className="text-xl font-bold mb-1">BTC Seer</h1>
        <p className="text-text-secondary text-sm">AI-Powered Bitcoin Intelligence</p>
        <div className="flex items-center justify-center gap-2 mt-2">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-accent-blue/15 text-accent-blue border border-accent-blue/30">v1.0 BETA</span>
          <span className="flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-full bg-accent-green/15 text-accent-green border border-accent-green/30">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
            LIVE
          </span>
        </div>
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

      {/* How to Use BTC Seer — Quick Start */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">HOW TO USE BTC SEER</h3>
        <p className="text-text-muted text-[10px] mb-3">New here? Follow these 5 steps to get started:</p>
        <div className="space-y-2 text-[11px] text-text-muted">
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">1</span>
            <p><span className="text-text-secondary font-semibold">Start on Dashboard</span> — check the current price, prediction cards, and overall market direction at a glance.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">2</span>
            <p><span className="text-text-secondary font-semibold">Read Signals</span> — view AI-generated entry, exit, and stop-loss levels with confidence scores.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">3</span>
            <p><span className="text-text-secondary font-semibold">Check Sentiment</span> — browse news sentiment, Fear & Greed index, and influencer mood to gauge market emotion.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">4</span>
            <p><span className="text-text-secondary font-semibold">Dive Deeper</span> — explore technical analysis, Power Law, Elliott Wave, and the liquidation map for advanced context.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">5</span>
            <p><span className="text-text-secondary font-semibold">Practice First</span> — use Paper Trading to test strategies with virtual money before risking real capital.</p>
          </div>
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
            { icon: '🌊', title: 'Elliott Wave Analysis', desc: 'Wave-based market structure to identify trend phases and potential reversals' },
            { icon: '💥', title: 'Liquidation Map', desc: 'See where leveraged positions cluster and where liquidation cascades may trigger' },
            { icon: '📰', title: 'News Sentiment', desc: 'Real-time tracking of what the market is feeling through news analysis' },
            { icon: '🤖', title: 'AI Advisor', desc: 'Get personalized market commentary and trading suggestions powered by AI' },
            { icon: '💰', title: 'Paper Trading', desc: 'Practice trading with virtual money — test strategies without risking real capital' },
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

      {/* What's Inside — All Pages */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">WHAT'S INSIDE</h3>
        <div className="space-y-1.5">
          {[
            ['Dashboard', 'Live BTC price, prediction cards, and market overview'],
            ['Predictions', 'Detailed AI predictions across all 5 timeframes'],
            ['Signals', 'Actionable entry/exit/SL levels with confidence scores'],
            ['Advisor', 'AI-powered market commentary and trade suggestions'],
            ['Sentiment', 'News analysis, Fear & Greed, and influencer mood tracking'],
            ['Technical', 'Charts with indicators — RSI, MACD, Bollinger Bands, and more'],
            ['Power Law', 'Long-term fair value model based on BTC adoption growth'],
            ['Elliott Wave', 'Wave-based analysis of market structure and trend phases'],
            ['Liquidation Map', 'Leveraged position clusters and liquidation risk zones'],
            ['Paper Trading', 'Practice with virtual money — track your P&L without risk'],
            ['Accuracy', 'How well our predictions performed — transparent scoring'],
            ['Learn', 'Trading education — basics, strategies, psychology, and patterns'],
            ['Events', 'Upcoming macro events, halvings, and market-moving dates'],
          ].map(([page, desc]) => (
            <div key={page} className="flex gap-2 py-1 border-b border-white/[0.03] last:border-0">
              <span className="text-accent-blue text-[11px] font-bold w-24 flex-shrink-0">{page}</span>
              <span className="text-text-muted text-[10px]">{desc}</span>
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
            { icon: '🌊', label: 'Elliott Wave' },
            { icon: '💥', label: 'Liquidation Map' },
            { icon: '📰', label: 'News Sentiment' },
            { icon: '📈', label: 'Trading Signals' },
            { icon: '🤖', label: 'AI Advisor' },
            { icon: '💰', label: 'Paper Trading' },
            { icon: '🎯', label: 'Accuracy Tracking' },
            { icon: '📚', label: 'Learn & Educate' },
            { icon: '🔑', label: 'API Access' },
          ].map((f) => (
            <div key={f.label} className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02]">
              <span className="text-base">{f.icon}</span>
              <span className="text-text-primary text-xs font-medium">{f.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Creator / Community */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">BUILT BY</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            Created by <span className="text-text-secondary font-semibold">Salakhitdinov Khidayotullo</span> — full-stack developer, AI researcher, and crypto enthusiast.
          </p>
          <p>
            BTC Seer is a solo project built with a passion for making AI-powered market intelligence accessible to everyone.
          </p>
          <a
            href="https://t.me/btc_seer_bot"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-1 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-[11px] font-semibold border border-accent-blue/20"
          >
            Join on Telegram
          </a>
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
