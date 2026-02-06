import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import {
  formatPrice,
  formatPercent,
  formatNumber,
  formatTime,
  formatTimeAgo,
  getDirectionColor,
  getActionColor,
  getActionBg,
} from '../utils/format.js'

const POLL_INTERVAL = 60_000

const TIMEFRAME_LABELS = {
  '1h': '1 Hour',
  '4h': '4 Hours',
  '24h': '24 Hours',
}

const DIRECTION_CONFIG = {
  bullish: { label: 'Bullish', arrow: '\u2191', colorClass: 'text-accent-green', bgClass: 'bg-accent-green/10' },
  bearish: { label: 'Bearish', arrow: '\u2193', colorClass: 'text-accent-red', bgClass: 'bg-accent-red/10' },
  neutral: { label: 'Neutral', arrow: '\u2194', colorClass: 'text-accent-yellow', bgClass: 'bg-accent-yellow/10' },
}

function getConfig(direction) {
  return DIRECTION_CONFIG[direction] ?? DIRECTION_CONFIG.neutral
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
          <div key={i} className="h-12 w-full bg-bg-hover rounded mb-2" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">Failed to load predictions</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  const timeframes = ['1h', '4h', '24h']
  const predMap = predictions?.predictions ?? predictions ?? {}

  const rows = timeframes.map((tf) => {
    // Handle both object-keyed and array formats
    if (Array.isArray(predMap)) {
      const match = predMap.find((p) => p.timeframe === tf)
      return { timeframe: tf, ...match }
    }
    const match = predMap[tf]
    return { timeframe: tf, ...match }
  })

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h3 className="text-text-primary text-sm font-semibold mb-3">
        Price Predictions
      </h3>

      <div className="space-y-2">
        {rows.map((row) => {
          const direction = row.direction ?? 'neutral'
          const config = getConfig(direction)
          const confidence = row.confidence ?? 0

          return (
            <div
              key={row.timeframe}
              className="flex items-center justify-between bg-bg-secondary rounded-xl px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <span className="text-text-secondary text-xs font-medium w-10">
                  {TIMEFRAME_LABELS[row.timeframe] ?? row.timeframe}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${config.colorClass} ${config.bgClass}`}
                >
                  <span className="text-sm">{config.arrow}</span>
                  {config.label}
                </span>

                <div className="flex items-center gap-1.5 min-w-[60px] justify-end">
                  <div className="w-12 h-1.5 bg-bg-primary rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        direction === 'bullish'
                          ? 'bg-accent-green'
                          : direction === 'bearish'
                          ? 'bg-accent-red'
                          : 'bg-accent-yellow'
                      }`}
                      style={{ width: `${Math.min(confidence, 100)}%` }}
                    />
                  </div>
                  <span className="text-text-secondary text-xs tabular-nums">
                    {confidence.toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {predictions?.updated_at && (
        <p className="text-text-muted text-[10px] mt-3 text-right">
          Updated {formatTimeAgo(predictions.updated_at)}
        </p>
      )}
    </div>
  )
}
