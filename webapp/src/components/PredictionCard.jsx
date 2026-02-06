import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import {
  formatPricePrecise,
  formatTimeAgo,
} from '../utils/format.js'

const POLL_INTERVAL = 30_000

const TIMEFRAME_LABELS = {
  '1h': '1H',
  '4h': '4H',
  '24h': '24H',
}

// Shared row renderer for a single timeframe prediction
function PredRow({ tf, direction, predictedPrice, changePct, confidence }) {
  const isUp = changePct > 0 || direction === 'bullish'
  const isDown = changePct < 0 || direction === 'bearish'
  const hasData = direction != null

  const accent = isUp ? 'text-accent-green' : isDown ? 'text-accent-red' : 'text-accent-yellow'
  const bg = isUp ? 'bg-accent-green/8' : isDown ? 'bg-accent-red/8' : 'bg-accent-yellow/8'
  const border = isUp ? 'border-accent-green/20' : isDown ? 'border-accent-red/20' : 'border-accent-yellow/20'
  const barColor = isUp ? 'bg-accent-green' : isDown ? 'bg-accent-red' : 'bg-accent-yellow'

  if (!hasData) {
    return (
      <div className="rounded-lg px-2.5 py-1.5 border border-white/5 bg-bg-secondary">
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-[10px] font-semibold">{TIMEFRAME_LABELS[tf]}</span>
          <span className="text-text-muted text-[10px]">--</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-lg px-2.5 py-1.5 border ${border} ${bg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted text-[10px] font-semibold w-5">{TIMEFRAME_LABELS[tf]}</span>
          <span className={`text-sm font-bold ${accent}`}>
            {isUp ? '\u2191' : isDown ? '\u2193' : '\u2194'}
          </span>
          <div className="flex items-baseline gap-1">
            {predictedPrice ? (
              <span className={`text-xs font-bold ${accent}`}>
                {formatPricePrecise(predictedPrice)}
              </span>
            ) : (
              <span className={`text-xs font-semibold ${accent}`}>
                {isUp ? 'Up' : isDown ? 'Down' : 'Flat'}
              </span>
            )}
            <span className={`text-[10px] ${accent} opacity-70`}>
              ({changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%)
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-8 h-1 bg-bg-primary/50 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${Math.min(confidence, 100)}%` }}
            />
          </div>
          <span className="text-text-muted text-[9px] tabular-nums w-6 text-right">
            {confidence.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  )
}

// Action badge for quant prediction
function ActionBadge({ action, score }) {
  const colors = {
    STRONG_BUY: 'bg-accent-green/20 text-accent-green border-accent-green/30',
    BUY: 'bg-accent-green/15 text-accent-green border-accent-green/25',
    LEAN_BULLISH: 'bg-accent-green/10 text-accent-green/80 border-accent-green/20',
    NEUTRAL: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20',
    LEAN_BEARISH: 'bg-accent-red/10 text-accent-red/80 border-accent-red/20',
    SELL: 'bg-accent-red/15 text-accent-red border-accent-red/25',
    STRONG_SELL: 'bg-accent-red/20 text-accent-red border-accent-red/30',
  }
  const cls = colors[action] || colors.NEUTRAL
  const label = action?.replace(/_/g, ' ') || 'N/A'

  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${cls}`}>
        {label}
      </span>
      {score != null && (
        <span className="text-text-muted text-[9px]">
          ({score > 0 ? '+' : ''}{score.toFixed(0)})
        </span>
      )}
    </div>
  )
}

// Signal breakdown mini-view
function SignalMini({ bullish, bearish, total, agreement }) {
  if (!total) return null
  return (
    <div className="flex items-center gap-2 text-[9px] text-text-muted mt-1">
      <span className="text-accent-green">{bullish}B</span>
      <span>/</span>
      <span className="text-accent-red">{bearish}S</span>
      <span className="text-text-muted/50">of {total}</span>
      {agreement != null && (
        <span className="ml-auto">{(agreement * 100).toFixed(0)}% agree</span>
      )}
    </div>
  )
}

export default function PredictionCard() {
  const [aiPredictions, setAiPredictions] = useState(null)
  const [quantData, setQuantData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [aiData, qData] = await Promise.all([
        api.getCurrentPredictions().catch(() => null),
        api.getQuantPrediction().catch(() => null),
      ])
      setAiPredictions(aiData)
      setQuantData(qData)
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
        <div className="grid grid-cols-2 gap-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-32 bg-bg-hover rounded-xl" />
          ))}
        </div>
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

  // Parse AI predictions
  const timeframes = ['1h', '4h', '24h']
  const predMap = aiPredictions?.predictions ?? aiPredictions ?? {}
  const aiRows = timeframes.map((tf) => {
    if (Array.isArray(predMap)) {
      return { timeframe: tf, ...(predMap.find((p) => p.timeframe === tf) || {}) }
    }
    return { timeframe: tf, ...(predMap[tf] || {}) }
  })
  const aiTimestamp = aiRows.find((r) => r.timestamp)?.timestamp

  // Parse Quant prediction
  const qp = quantData?.prediction
  const quantRows = timeframes.map((tf) => {
    const p = qp?.predictions?.[tf]
    return {
      timeframe: tf,
      direction: p?.direction ?? qp?.direction,
      predicted_price: p?.predicted_price,
      predicted_change_pct: p?.predicted_change_pct ?? 0,
      confidence: p?.confidence ?? qp?.confidence ?? 0,
    }
  })

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary text-sm font-semibold">
          Dual Predictions
        </h3>
        <span className="text-text-muted text-[9px]">Updated every 30m</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* ── AI Model Column ── */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-accent-blue">AI MODEL</span>
            {aiTimestamp && (
              <span className="text-text-muted text-[8px]">{formatTimeAgo(aiTimestamp)}</span>
            )}
          </div>
          {aiRows.map((row) => (
            <PredRow
              key={row.timeframe}
              tf={row.timeframe}
              direction={row.direction}
              predictedPrice={row.predicted_price}
              changePct={row.predicted_change_pct ?? 0}
              confidence={row.confidence ?? 0}
            />
          ))}
          <p className="text-text-muted text-[8px] mt-1 opacity-60">
            LSTM + XGBoost + Sentiment
          </p>
        </div>

        {/* ── Quant Theory Column ── */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-accent-yellow">QUANT THEORY</span>
            {qp?.timestamp && (
              <span className="text-text-muted text-[8px]">{formatTimeAgo(qp.timestamp)}</span>
            )}
          </div>
          {qp ? (
            <>
              {quantRows.map((row) => (
                <PredRow
                  key={row.timeframe}
                  tf={row.timeframe}
                  direction={row.direction}
                  predictedPrice={row.predicted_price}
                  changePct={row.predicted_change_pct}
                  confidence={row.confidence}
                />
              ))}
              <ActionBadge action={qp.action} score={qp.composite_score} />
              <SignalMini
                bullish={qp.bullish_signals}
                bearish={qp.bearish_signals}
                total={qp.active_signals}
                agreement={qp.agreement_ratio}
              />
            </>
          ) : (
            <>
              {timeframes.map((tf) => (
                <PredRow key={tf} tf={tf} direction={null} changePct={0} confidence={0} />
              ))}
              <p className="text-text-muted text-[9px]">{quantData?.message || 'Generating...'}</p>
            </>
          )}
          <p className="text-text-muted text-[8px] mt-1 opacity-60">
            15 theories combined
          </p>
        </div>
      </div>
    </div>
  )
}
