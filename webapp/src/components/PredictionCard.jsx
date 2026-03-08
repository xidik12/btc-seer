import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import CardShareButton from './CardShareButton'
import { api } from '../utils/api.js'
import { formatPricePrecise, formatTimeAgo, safeFixed } from '../utils/format.js'

const POLL_INTERVAL = 30_000

function CountdownTimer() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  const next = new Date(now)
  next.setUTCMinutes(0, 0, 0)
  next.setUTCHours(next.getUTCHours() + 1)
  const diff = Math.max(0, Math.floor((next - now) / 1000))
  const mm = String(Math.floor(diff / 60)).padStart(2, '0')
  const ss = String(diff % 60).padStart(2, '0')
  return <span className="text-accent-blue text-[10px] font-mono tabular-nums">{mm}:{ss}</span>
}

export default function PredictionCard() {
  const { t } = useTranslation('dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const cardRef = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getCurrentPredictions()
      setData(res)
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
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-bg-hover rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('prediction.aiTitle') })}</p>
        <button onClick={fetchData} className="text-accent-blue text-xs mt-1 underline">{t('common:app.retry')}</button>
      </div>
    )
  }

  const timeframes = ['1h', '4h', '24h', '1w', '1mo']
  const tfLabels = { '1h': '1H', '4h': '4H', '24h': '24H', '1w': '1W', '1mo': '1MO' }
  const predMap = data?.predictions ?? data ?? {}

  const rows = timeframes.map((tf) => {
    if (Array.isArray(predMap)) {
      return { timeframe: tf, ...(predMap.find((p) => p.timeframe === tf) || {}) }
    }
    return { timeframe: tf, ...(predMap[tf] || {}) }
  })

  const timestamp = rows.find((r) => r.timestamp)?.timestamp

  return (
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 gradient-border slide-up">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-accent-blue">{t('prediction.aiModel')}</span>
          <span className="text-text-muted text-[8px]">{t('prediction.modelDescription')}</span>
        </div>
        <div className="flex items-center gap-2">
          <CardShareButton cardRef={cardRef} label="AI Prediction" filename="ai-prediction.png" />
          <CountdownTimer />
          {timestamp && (
            <span className="text-text-muted text-[10px]">{formatTimeAgo(timestamp)}</span>
          )}
        </div>
      </div>

      <div className="space-y-1.5">
        {rows.map((row) => {
          const dir = row.direction
          const changePct = Number(row.predicted_change_pct) || 0
          const confidence = Number(row.confidence) || 0
          const price = row.predicted_price

          const isUp = changePct > 0 || dir === 'bullish'
          const isDown = changePct < 0 || dir === 'bearish'
          const hasData = dir != null

          if (!hasData) {
            return (
              <div key={row.timeframe} className="rounded-lg px-3 py-2 border border-white/5 bg-bg-secondary">
                <div className="flex items-center justify-between">
                  <span className="text-text-muted text-xs font-semibold">{tfLabels[row.timeframe]}</span>
                  <span className="text-text-muted text-[10px]">{t('prediction.pending', { defaultValue: 'Pending' })}</span>
                </div>
              </div>
            )
          }

          const accent = isUp ? 'text-accent-green' : isDown ? 'text-accent-red' : 'text-accent-yellow'
          const bg = isUp ? 'bg-accent-green/8' : isDown ? 'bg-accent-red/8' : 'bg-accent-yellow/8'
          const border = isUp ? 'border-accent-green/20' : isDown ? 'border-accent-red/20' : 'border-accent-yellow/20'
          const barColor = isUp ? 'bg-accent-green' : isDown ? 'bg-accent-red' : 'bg-accent-yellow'
          const arrow = isUp ? '\u2191' : isDown ? '\u2193' : '\u2194'

          return (
            <div key={row.timeframe} className={`rounded-lg px-3 py-2 border ${border} ${bg}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-text-muted text-xs font-semibold w-6">{tfLabels[row.timeframe]}</span>
                  <span className={`text-sm font-bold ${accent}`}>{arrow}</span>
                  <div className="flex items-baseline gap-1">
                    {price ? (
                      <span className={`text-xs font-bold ${accent}`}>{formatPricePrecise(price)}</span>
                    ) : (
                      <span className={`text-xs font-semibold ${accent}`}>
                        {isUp ? t('common:direction.bullish') : isDown ? t('common:direction.bearish') : t('common:direction.neutral')}
                      </span>
                    )}
                    <span className={`text-[10px] ${accent} opacity-70`}>
                      ({changePct > 0 ? '+' : ''}{safeFixed(changePct, 2)}%)
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-10 h-1.5 bg-bg-primary/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${barColor}`}
                      style={{ width: `${Math.min(confidence, 100)}%` }}
                    />
                  </div>
                  <span className="text-text-muted text-[10px] tabular-nums w-7 text-right">
                    {safeFixed(confidence, 0)}%
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
