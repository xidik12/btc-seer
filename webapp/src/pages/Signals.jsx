import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { formatPrice, formatTime, formatDate, getActionColor, getActionBg } from '../utils/format'

export default function Signals() {
  const [signals, setSignals] = useState([])
  const [timeframe, setTimeframe] = useState('1h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const data = await api.getSignalHistory(timeframe, 7)
        setSignals(data.signals || [])
      } catch {
        setSignals([])
      }
      setLoading(false)
    }
    load()
  }, [timeframe])

  return (
    <div className="px-4 pt-4">
      <h1 className="text-lg font-bold mb-4">📈 Signal History</h1>

      <div className="flex gap-2 mb-4">
        {['1h', '4h', '24h'].map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              timeframe === tf
                ? 'bg-accent-blue text-white'
                : 'bg-bg-card text-text-secondary'
            }`}
          >
            {tf.toUpperCase()}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center text-text-secondary py-10">Loading...</div>
      ) : signals.length === 0 ? (
        <div className="text-center text-text-secondary py-10">No signals yet</div>
      ) : (
        <div className="space-y-3">
          {signals.map((s) => (
            <div
              key={s.id}
              className={`p-4 rounded-xl border slide-up ${getActionBg(s.action)}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-bold uppercase ${getActionColor(s.action)}`}>
                  {s.action?.replace('_', ' ')}
                </span>
                <span className="text-text-muted text-xs">
                  {formatDate(s.timestamp)} {formatTime(s.timestamp)}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <div className="text-text-muted">Entry</div>
                  <div className="font-mono">{formatPrice(s.entry_price)}</div>
                </div>
                <div>
                  <div className="text-text-muted">Target</div>
                  <div className="font-mono text-accent-green">{formatPrice(s.target_price)}</div>
                </div>
                <div>
                  <div className="text-text-muted">Stop</div>
                  <div className="font-mono text-accent-red">{formatPrice(s.stop_loss)}</div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
                <span className="text-text-muted text-xs">
                  Confidence: {s.confidence?.toFixed(0)}%
                </span>
                <span className="text-text-muted text-xs">
                  Risk: {s.risk_rating}/10
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
