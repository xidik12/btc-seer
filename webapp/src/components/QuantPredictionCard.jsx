import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import CardShareButton from './CardShareButton'
import { api } from '../utils/api.js'
import {
  formatPricePrecise,
  formatTimeAgo,
} from '../utils/format.js'

const POLL_INTERVAL = 30_000

const TIMEFRAME_LABELS = { '1h': '1H', '4h': '4H', '24h': '24H', '1w': '1W', '1mo': '1MO' }

function getActionStyles(t) {
  return {
    STRONG_BUY: { label: t('common:signal.strongBuy'), color: 'text-accent-green', bg: 'bg-accent-green/15', border: 'border-accent-green/30' },
    BUY: { label: t('common:signal.buy'), color: 'text-accent-green', bg: 'bg-accent-green/10', border: 'border-accent-green/20' },
    LEAN_BULLISH: { label: t('common:direction.bullish'), color: 'text-accent-green', bg: 'bg-accent-green/8', border: 'border-accent-green/15' },
    NEUTRAL: { label: t('common:direction.neutral'), color: 'text-accent-yellow', bg: 'bg-accent-yellow/8', border: 'border-accent-yellow/15' },
    LEAN_BEARISH: { label: t('common:direction.bearish'), color: 'text-accent-red', bg: 'bg-accent-red/8', border: 'border-accent-red/15' },
    SELL: { label: t('common:signal.sell'), color: 'text-accent-red', bg: 'bg-accent-red/10', border: 'border-accent-red/20' },
    STRONG_SELL: { label: t('common:signal.strongSell'), color: 'text-accent-red', bg: 'bg-accent-red/15', border: 'border-accent-red/30' },
  }
}

function ScoreBar({ score }) {
  // score from -100 to +100, map to 0-100 for bar position
  const pct = (score + 100) / 2
  const isPositive = score > 0

  return (
    <div className="relative w-full h-2 bg-bg-primary/50 rounded-full overflow-hidden">
      {/* Center marker */}
      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-text-muted/30 z-10" />
      {/* Score fill */}
      {isPositive ? (
        <div
          className="absolute top-0 bottom-0 bg-accent-green rounded-full transition-all duration-700"
          style={{ left: '50%', width: `${Math.min(score / 2, 50)}%` }}
        />
      ) : (
        <div
          className="absolute top-0 bottom-0 bg-accent-red rounded-full transition-all duration-700"
          style={{ right: '50%', width: `${Math.min(Math.abs(score) / 2, 50)}%` }}
        />
      )}
    </div>
  )
}

function SignalBreakdown({ breakdown, expanded, t }) {
  if (!expanded || !breakdown) return null

  const signals = Object.entries(breakdown).sort((a, b) => {
    // Sort by weight descending
    return (b[1]?.weight || 0) - (a[1]?.weight || 0)
  })

  return (
    <div className="mt-3 pt-3 border-t border-white/5 space-y-1.5">
      <p className="text-text-muted text-xs font-semibold tracking-wider mb-2">
        {t('dashboard:prediction.signalBreakdown').toUpperCase()} ({signals.length} {t('dashboard:prediction.activeSignals')})
      </p>
      {signals.map(([name, sig]) => {
        const dir = sig.direction || 0
        const isBull = dir > 0.1
        const isBear = dir < -0.1
        const color = isBull ? 'text-accent-green' : isBear ? 'text-accent-red' : 'text-text-muted'
        const arrow = isBull ? '\u2191' : isBear ? '\u2193' : '\u2022'
        const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

        return (
          <div key={name} className="flex items-start gap-2 text-xs">
            <span className={`${color} font-bold w-3 text-center shrink-0`}>{arrow}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary font-medium">{label}</span>
                <span className="text-text-muted text-xs tabular-nums">
                  {(sig.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-text-muted text-xs truncate">{sig.reasoning}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function QuantPredictionCard() {
  const { t } = useTranslation('dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const cardRef = useRef(null)

  const ACTION_STYLES = getActionStyles(t)

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getQuantPrediction()
      setData(res?.prediction || null)
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
        <div className="h-5 w-44 bg-bg-hover rounded mb-4" />
        <div className="h-16 w-full bg-bg-hover rounded mb-2" />
        <div className="h-14 w-full bg-bg-hover rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('prediction.quantTitle') })}</p>
        <button onClick={fetchData} className="text-accent-blue text-xs mt-1 underline">{t('common:app.retry')}</button>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-primary text-sm font-semibold mb-2">{t('prediction.quantTitle')}</h3>
        <p className="text-text-muted text-xs">{t('common:app.loading')}</p>
      </div>
    )
  }

  const actionStyle = ACTION_STYLES[data.action] || ACTION_STYLES.NEUTRAL
  const isUp = data.direction === 'bullish'
  const score = data.composite_score || 0
  const preds = data.predictions || {}

  return (
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 gradient-border slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-text-primary text-sm font-semibold">{t('prediction.quantTitle')}</h3>
          <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${actionStyle.bg} ${actionStyle.border} ${actionStyle.color}`}>
            {actionStyle.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <CardShareButton cardRef={cardRef} label="Quant Prediction" filename="quant-prediction.png" />
          {data.timestamp && (
            <span className="text-text-muted text-xs">
              {formatTimeAgo(data.timestamp)}
            </span>
          )}
        </div>
      </div>

      {/* Composite Score Bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-text-muted text-xs">{t('common:direction.bearish')}</span>
          <span className={`text-xs font-bold tabular-nums ${isUp ? 'text-accent-green' : 'text-accent-red'}`}>
            {score > 0 ? '+' : ''}{score.toFixed(0)}
          </span>
          <span className="text-text-muted text-xs">{t('common:direction.bullish')}</span>
        </div>
        <ScoreBar score={score} />
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-text-muted text-xs">
            {data.bullish_signals || 0}{t('prediction.bullishShort')} / {data.bearish_signals || 0}{t('prediction.bearishShort')}
            {data.agreement_ratio ? ` (${(data.agreement_ratio * 100).toFixed(0)}% ${t('prediction.agreement')})` : ''}
          </span>
          <span className="text-text-muted text-xs tabular-nums">
            {data.active_signals || 0}/{Object.keys(data.signal_breakdown || {}).length} {t('prediction.activeSignals')}
          </span>
        </div>
      </div>

      {/* Timeframe Predictions */}
      <div className="space-y-1.5">
        {['1h', '4h', '24h', '1w', '1mo'].map((tf) => {
          const p = preds[tf]
          if (!p) return null
          const changePct = p.predicted_change_pct || 0
          const predPrice = p.predicted_price
          const tfUp = changePct > 0
          const tfDown = changePct < 0
          const color = tfUp ? 'text-accent-green' : tfDown ? 'text-accent-red' : 'text-text-muted'
          const bgColor = tfUp ? 'bg-accent-green/8 border-accent-green/20' : tfDown ? 'bg-accent-red/8 border-accent-red/20' : 'bg-bg-secondary border-white/5'

          return (
            <div key={tf} className={`rounded-xl px-3 py-2 border ${bgColor}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-text-muted text-xs font-semibold w-6">
                    {TIMEFRAME_LABELS[tf]}
                  </span>
                  <span className={`text-lg font-bold ${color}`}>
                    {tfUp ? '\u2191' : tfDown ? '\u2193' : '\u2022'}
                  </span>
                  <div>
                    {predPrice ? (
                      <span className={`text-sm font-bold ${color}`}>
                        {formatPricePrecise(predPrice)}
                      </span>
                    ) : null}
                    <span className={`text-xs ml-1.5 ${color} opacity-80`}>
                      ({changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%)
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-10 h-1.5 bg-bg-primary/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        tfUp ? 'bg-accent-green' : tfDown ? 'bg-accent-red' : 'bg-accent-yellow'
                      }`}
                      style={{ width: `${Math.min(data.confidence || 0, 100)}%` }}
                    />
                  </div>
                  <span className="text-text-muted text-xs tabular-nums w-7 text-right">
                    {(data.confidence || 0).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Expand/collapse signal breakdown */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full mt-2 text-center text-accent-blue text-xs hover:underline"
      >
        {expanded ? t('prediction.hideBreakdown') : t('prediction.showBreakdown')}
      </button>

      <SignalBreakdown breakdown={data.signal_breakdown} expanded={expanded} t={t} />
    </div>
  )
}
