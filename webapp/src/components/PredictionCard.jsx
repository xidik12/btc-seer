import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import {
  formatPricePrecise,
  formatPercent,
  formatTimeAgo,
} from '../utils/format.js'

const POLL_INTERVAL = 30_000

const TIMEFRAME_LABELS = {
  '1h': '1H',
  '4h': '4H',
  '24h': '24H',
}

export default function PredictionCard() {
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getCurrentPredictions()
      setPredictions(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-5 w-36 bg-bg-hover rounded mb-4" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 w-full bg-bg-hover rounded mb-2" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">Failed to load predictions</p>
        <button onClick={fetchData} className="text-accent-blue text-xs mt-1 underline">Retry</button>
      </div>
    )
  }

  const timeframes = ['1h', '4h', '24h']
  const predMap = predictions?.predictions ?? predictions ?? {}

  const rows = timeframes.map((tf) => {
    if (Array.isArray(predMap)) {
      const match = predMap.find((p) => p.timeframe === tf)
      return { timeframe: tf, ...match }
    }
    const match = predMap[tf]
    return { timeframe: tf, ...match }
  })

  // Find timestamp from any prediction
  const timestamp = rows.find((r) => r.timestamp)?.timestamp

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary text-sm font-semibold">
          Price Predictions
        </h3>
        {timestamp && (
          <span className="text-text-muted text-[10px]">
            {formatTimeAgo(timestamp)}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {rows.map((row) => {
          const direction = row.direction ?? 'neutral'
          const changePct = row.predicted_change_pct ?? 0
          const predictedPrice = row.predicted_price
          const currentPrice = row.current_price
          const confidence = row.confidence ?? 0
          const isUp = changePct > 0 || direction === 'bullish'
          const isDown = changePct < 0 || direction === 'bearish'
          const hasData = row.direction != null

          const accentColor = isUp ? 'text-accent-green' : isDown ? 'text-accent-red' : 'text-accent-yellow'
          const bgColor = isUp ? 'bg-accent-green/8' : isDown ? 'bg-accent-red/8' : 'bg-accent-yellow/8'
          const borderColor = isUp ? 'border-accent-green/20' : isDown ? 'border-accent-red/20' : 'border-accent-yellow/20'

          return (
            <div
              key={row.timeframe}
              className={`rounded-xl px-3 py-2.5 border ${hasData ? borderColor + ' ' + bgColor : 'border-white/5 bg-bg-secondary'}`}
            >
              {hasData ? (
                <div className="flex items-center justify-between">
                  {/* Left: timeframe + arrow + price */}
                  <div className="flex items-center gap-2">
                    <span className="text-text-muted text-xs font-semibold w-6">
                      {TIMEFRAME_LABELS[row.timeframe]}
                    </span>
                    <span className={`text-lg font-bold ${accentColor}`}>
                      {isUp ? '\u2191' : isDown ? '\u2193' : '\u2194'}
                    </span>
                    <div>
                      {predictedPrice ? (
                        <span className={`text-sm font-bold ${accentColor}`}>
                          {formatPricePrecise(predictedPrice)}
                        </span>
                      ) : (
                        <span className={`text-sm font-semibold ${accentColor}`}>
                          {isUp ? 'Up' : isDown ? 'Down' : 'Flat'}
                        </span>
                      )}
                      <span className={`text-xs ml-1.5 ${accentColor} opacity-80`}>
                        ({changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%)
                      </span>
                    </div>
                  </div>

                  {/* Right: confidence bar */}
                  <div className="flex items-center gap-1.5">
                    <div className="w-10 h-1.5 bg-bg-primary/50 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isUp ? 'bg-accent-green' : isDown ? 'bg-accent-red' : 'bg-accent-yellow'
                        }`}
                        style={{ width: `${Math.min(confidence, 100)}%` }}
                      />
                    </div>
                    <span className="text-text-muted text-[10px] tabular-nums w-7 text-right">
                      {confidence.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted text-xs font-semibold">
                    {TIMEFRAME_LABELS[row.timeframe]}
                  </span>
                  <span className="text-text-muted text-xs">Awaiting data...</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
