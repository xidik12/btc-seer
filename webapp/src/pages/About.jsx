const I = (children, sm) => (
  <svg className={sm ? 'w-4 h-4 text-accent-blue' : 'w-5 h-5 text-accent-blue'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

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
            { icon: I(<><path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" /></>), title: 'Prediction Cards', desc: 'Confidence scores to gauge market direction across multiple timeframes' },
            { icon: I(<><polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" /></>), title: 'Trading Signals', desc: 'Entry, target, and stop-loss levels with AI-calculated confidence' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M3 17C7 15 11 9 21 5" /></>), title: 'Power Law Analysis', desc: 'Long-term fair value model to understand where BTC stands historically' },
            { icon: I(<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />), title: 'Elliott Wave Analysis', desc: 'Wave-based market structure to identify trend phases and potential reversals' },
            { icon: I(<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />), title: 'Liquidation Map', desc: 'See where leveraged positions cluster and where liquidation cascades may trigger' },
            { icon: I(<><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>), title: 'News Sentiment', desc: 'Real-time tracking of what the market is feeling through news analysis' },
            { icon: I(<><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></>), title: 'AI Advisor', desc: 'Get personalized market commentary and trading suggestions powered by AI' },
            { icon: I(<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></>), title: 'Paper Trading', desc: 'Practice trading with virtual money — test strategies without risking real capital' },
            { icon: I(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>), title: 'Accuracy Tracking', desc: 'Every prediction is evaluated and scored — full transparency on model performance' },
          ].map((item) => (
            <div key={item.title} className="flex items-start gap-3 p-2 rounded-xl bg-white/[0.02]">
              <span className="mt-0.5 shrink-0">{item.icon}</span>
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
            { icon: I(<><path d="M9 18h6" /><path d="M10 22h4" /><path d="M12 2a7 7 0 00-4 12.9V17h8v-2.1A7 7 0 0012 2z" /></>, true), label: 'AI Predictions' },
            { icon: I(<><polyline points="22 17 13.5 8.5 8.5 13.5 2 7" /><polyline points="16 17 22 17 22 11" /></>, true), label: 'Quant Theory' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M3 17C7 15 11 9 21 5" /></>, true), label: 'Power Law' },
            { icon: I(<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />, true), label: 'Elliott Wave' },
            { icon: I(<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />, true), label: 'Liquidation Map' },
            { icon: I(<><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>, true), label: 'News Sentiment' },
            { icon: I(<><polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" /></>, true), label: 'Trading Signals' },
            { icon: I(<><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></>, true), label: 'AI Advisor' },
            { icon: I(<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></>, true), label: 'Paper Trading' },
            { icon: I(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>, true), label: 'Accuracy Tracking' },
            { icon: I(<><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z" /><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z" /></>, true), label: 'Learn & Educate' },
            { icon: I(<><circle cx="15.5" cy="8.5" r="3.5" /><path d="M12 12L4 20" /><path d="M8 16l3 3" /></>, true), label: 'API Access' },
          ].map((f) => (
            <div key={f.label} className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02]">
              <span className="shrink-0">{f.icon}</span>
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
