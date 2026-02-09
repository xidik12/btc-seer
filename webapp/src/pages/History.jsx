import AccuracyTracker from '../components/AccuracyTracker'
import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { formatPrice, formatDate, formatTime, getDirectionColor } from '../utils/format'

export default function History() {
  const [predictions, setPredictions] = useState([])
  const [timeframe, setTimeframe] = useState('1h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const data = await api.getPredictionHistory(timeframe, 14)
        setPredictions(data.history || [])
      } catch {
        setPredictions([])
      }
      setLoading(false)
    }
    load()
  }, [timeframe])

  return (
    <div className="px-4 pt-4">
      <h1 className="text-lg font-bold mb-4">🎯 Prediction History</h1>

      <AccuracyTracker />

      <div className="flex gap-2 my-4">
        {['1h', '4h', '24h', '1w', '1mo'].map((tf) => (
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
      ) : predictions.length === 0 ? (
        <div className="text-center text-text-secondary py-10">No predictions yet</div>
      ) : (
        <div className="space-y-2">
          {predictions.map((p) => (
            <div
              key={p.id}
              className="bg-bg-card rounded-xl p-3 border border-white/5 flex items-center gap-3 slide-up"
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                p.was_correct === true
                  ? 'bg-accent-green/20 text-accent-green'
                  : p.was_correct === false
                  ? 'bg-accent-red/20 text-accent-red'
                  : 'bg-white/5 text-text-muted'
              }`}>
                {p.was_correct === true ? '✓' : p.was_correct === false ? '✗' : '?'}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${getDirectionColor(p.direction)}`}>
                    {p.direction === 'bullish' ? '▲' : p.direction === 'bearish' ? '▼' : '◄►'}{' '}
                    {p.direction}
                  </span>
                  <span className="text-text-muted text-xs">
                    {p.confidence?.toFixed(0)}%
                  </span>
                </div>
                <div className="text-[10px] text-text-muted mt-0.5">
                  {formatDate(p.timestamp)} {formatTime(p.timestamp)} — {formatPrice(p.current_price)}
                  {p.actual_price ? ` → ${formatPrice(p.actual_price)}` : ''}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
