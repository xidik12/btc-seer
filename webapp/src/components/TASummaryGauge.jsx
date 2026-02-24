import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

const RATING_COLORS = {
  STRONG_BUY: '#22c55e',
  BUY: '#4ade80',
  NEUTRAL: '#eab308',
  SELL: '#f87171',
  STRONG_SELL: '#ef4444',
}

const RATING_LABELS = {
  STRONG_BUY: 'Strong Buy',
  BUY: 'Buy',
  NEUTRAL: 'Neutral',
  SELL: 'Sell',
  STRONG_SELL: 'Strong Sell',
}

function GaugeArc({ score }) {
  // score: -1 to +1 → needle from -90° to +90°
  const angle = score * 90
  const radius = 70
  const cx = 80
  const cy = 80

  // 5 zones: Strong Sell, Sell, Neutral, Buy, Strong Buy
  const zones = [
    { start: -90, end: -54, color: '#ef4444' },
    { start: -54, end: -18, color: '#f87171' },
    { start: -18, end: 18, color: '#eab308' },
    { start: 18, end: 54, color: '#4ade80' },
    { start: 54, end: 90, color: '#22c55e' },
  ]

  const describeArc = (startAngle, endAngle) => {
    const startRad = ((startAngle - 90) * Math.PI) / 180
    const endRad = ((endAngle - 90) * Math.PI) / 180
    const x1 = cx + radius * Math.cos(startRad)
    const y1 = cy + radius * Math.sin(startRad)
    const x2 = cx + radius * Math.cos(endRad)
    const y2 = cy + radius * Math.sin(endRad)
    const large = endAngle - startAngle > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
  }

  const needleRad = ((angle - 90) * Math.PI) / 180
  const needleLen = 55
  const nx = cx + needleLen * Math.cos(needleRad)
  const ny = cy + needleLen * Math.sin(needleRad)

  return (
    <svg viewBox="0 0 160 95" className="w-full max-w-[200px] mx-auto">
      {zones.map((z, i) => (
        <path
          key={i}
          d={describeArc(z.start, z.end)}
          stroke={z.color}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          opacity="0.6"
        />
      ))}
      <line
        x1={cx}
        y1={cy}
        x2={nx}
        y2={ny}
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r="4" fill="white" />
    </svg>
  )
}

function VoteBar({ label, buy, neutral, sell }) {
  const total = buy + neutral + sell || 1
  const bPct = (buy / total) * 100
  const nPct = (neutral / total) * 100
  const sPct = (sell / total) * 100

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-text-secondary text-xs">{label}</span>
        <div className="flex gap-2 text-[10px] tabular-nums">
          <span className="text-accent-green">{buy}</span>
          <span className="text-accent-yellow">{neutral}</span>
          <span className="text-accent-red">{sell}</span>
        </div>
      </div>
      <div className="flex h-1.5 rounded-full overflow-hidden bg-bg-secondary">
        <div className="bg-accent-green" style={{ width: `${bPct}%` }} />
        <div className="bg-accent-yellow" style={{ width: `${nPct}%` }} />
        <div className="bg-accent-red" style={{ width: `${sPct}%` }} />
      </div>
    </div>
  )
}

export default function TASummaryGauge() {
  const [data, setData] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchTA = useCallback(async () => {
    try {
      const result = await api.getTASummary()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTA()
    const iv = setInterval(fetchTA, 60_000)
    return () => clearInterval(iv)
  }, [fetchTA])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-4 w-32 bg-bg-secondary rounded mb-4" />
        <div className="h-24 w-24 mx-auto bg-bg-secondary rounded-full" />
      </div>
    )
  }

  if (!data || data.error) return null

  const rating = data.overall || 'NEUTRAL'
  const score = data.overall_score || 0
  const summary = data.summary || {}
  const ma = data.moving_averages || {}
  const osc = data.oscillators || {}

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary font-semibold text-sm">TA Summary</h3>
        <span
          className="text-xs font-bold px-2 py-0.5 rounded-full"
          style={{
            color: RATING_COLORS[rating],
            backgroundColor: `${RATING_COLORS[rating]}20`,
          }}
        >
          {RATING_LABELS[rating]}
        </span>
      </div>

      <GaugeArc score={score} />

      <div className="text-center mb-4">
        <p className="text-text-muted text-[10px] mt-1">
          {summary.buy || 0} Buy · {summary.neutral || 0} Neutral · {summary.sell || 0} Sell
        </p>
      </div>

      <VoteBar label="Moving Averages" buy={ma.buy || 0} neutral={ma.neutral || 0} sell={ma.sell || 0} />
      <VoteBar label="Oscillators" buy={osc.buy || 0} neutral={osc.neutral || 0} sell={osc.sell || 0} />

      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-center text-accent-blue text-[10px] mt-2 hover:underline"
      >
        {expanded ? 'Hide Signals' : 'Show All Signals'}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {ma.signals?.length > 0 && (
            <div>
              <p className="text-text-secondary text-[10px] font-semibold mb-1">Moving Averages</p>
              {ma.signals.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-white/5">
                  <span className="text-text-secondary text-[10px]">{s.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary text-[10px] tabular-nums">
                      {typeof s.value === 'number' ? s.value.toFixed(2) : s.value}
                    </span>
                    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                      s.action === 'BUY' ? 'bg-accent-green/15 text-accent-green'
                      : s.action === 'SELL' ? 'bg-accent-red/15 text-accent-red'
                      : 'bg-accent-yellow/15 text-accent-yellow'
                    }`}>
                      {s.action}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          {osc.signals?.length > 0 && (
            <div>
              <p className="text-text-secondary text-[10px] font-semibold mb-1">Oscillators</p>
              {osc.signals.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-white/5">
                  <span className="text-text-secondary text-[10px]">{s.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary text-[10px] tabular-nums">
                      {typeof s.value === 'number' ? s.value.toFixed(2) : s.value}
                    </span>
                    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                      s.action === 'BUY' ? 'bg-accent-green/15 text-accent-green'
                      : s.action === 'SELL' ? 'bg-accent-red/15 text-accent-red'
                      : 'bg-accent-yellow/15 text-accent-yellow'
                    }`}>
                      {s.action}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
