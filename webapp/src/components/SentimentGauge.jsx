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

const POLL_INTERVAL = 300_000

function getSentimentLabel(value) {
  if (value <= 20) return 'Extreme Fear'
  if (value <= 40) return 'Fear'
  if (value <= 60) return 'Neutral'
  if (value <= 80) return 'Greed'
  return 'Extreme Greed'
}

function getSentimentColor(value) {
  if (value <= 20) return '#ff4d6a'
  if (value <= 40) return '#ff8c42'
  if (value <= 60) return '#ffb800'
  if (value <= 80) return '#7dd87d'
  return '#00d68f'
}

function getSentimentTextClass(value) {
  if (value <= 20) return 'text-accent-red'
  if (value <= 40) return 'text-accent-orange'
  if (value <= 60) return 'text-accent-yellow'
  if (value <= 80) return 'text-accent-green'
  return 'text-accent-green'
}

/**
 * Renders a semi-circular SVG gauge arc.
 * The arc sweeps from 180deg (left) to 0deg (right) in a standard semi-circle.
 * `ratio` is 0..1 representing the fill amount.
 */
function GaugeArc({ value, size = 180 }) {
  const ratio = Math.max(0, Math.min(1, value / 100))
  const strokeWidth = 12
  const radius = (size - strokeWidth) / 2
  const cx = size / 2
  const cy = size / 2

  // Arc from PI (left) to 0 (right), sweeping clockwise
  const startAngle = Math.PI
  const endAngle = 0

  // Background arc path (full semi-circle)
  const bgStartX = cx + radius * Math.cos(startAngle)
  const bgStartY = cy - radius * Math.sin(startAngle)
  const bgEndX = cx + radius * Math.cos(endAngle)
  const bgEndY = cy - radius * Math.sin(endAngle)
  const bgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 0 1 ${bgEndX} ${bgEndY}`

  // Foreground arc path (partial, based on ratio)
  const fillAngle = Math.PI - ratio * Math.PI // from PI toward 0
  const fillEndX = cx + radius * Math.cos(fillAngle)
  const fillEndY = cy - radius * Math.sin(fillAngle)
  const largeArc = ratio > 0.5 ? 1 : 0
  const fgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 ${largeArc} 1 ${fillEndX} ${fillEndY}`

  // Needle position
  const needleLength = radius - 8
  const needleX = cx + needleLength * Math.cos(fillAngle)
  const needleY = cy - needleLength * Math.sin(fillAngle)

  // Gradient stops for the arc
  const color = getSentimentColor(value)

  return (
    <svg
      width={size}
      height={size / 2 + 20}
      viewBox={`0 0 ${size} ${size / 2 + 20}`}
      className="mx-auto"
    >
      <defs>
        <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ff4d6a" />
          <stop offset="25%" stopColor="#ff8c42" />
          <stop offset="50%" stopColor="#ffb800" />
          <stop offset="75%" stopColor="#7dd87d" />
          <stop offset="100%" stopColor="#00d68f" />
        </linearGradient>
      </defs>

      {/* Background arc */}
      <path
        d={bgPath}
        fill="none"
        stroke="#1a1a24"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />

      {/* Gradient arc (full, clipped visually by the fill arc) */}
      <path
        d={bgPath}
        fill="none"
        stroke="url(#gauge-gradient)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        opacity={0.15}
      />

      {/* Filled arc */}
      {ratio > 0.005 && (
        <path
          d={fgPath}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      )}

      {/* Needle */}
      <line
        x1={cx}
        y1={cy}
        x2={needleX}
        y2={needleY}
        stroke="#ffffff"
        strokeWidth={2}
        strokeLinecap="round"
        className="transition-all duration-700"
      />

      {/* Center dot */}
      <circle cx={cx} cy={cy} r={4} fill="#ffffff" />

      {/* Min / Max labels */}
      <text
        x={strokeWidth / 2 + 2}
        y={cy + 16}
        fill="#5a5a70"
        fontSize="10"
        textAnchor="start"
      >
        0
      </text>
      <text
        x={size - strokeWidth / 2 - 2}
        y={cy + 16}
        fill="#5a5a70"
        fontSize="10"
        textAnchor="end"
      >
        100
      </text>
    </svg>
  )
}

export default function SentimentGauge() {
  const [macro, setMacro] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getMacroData()
      setMacro(data)
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
        <div className="h-24 w-36 bg-bg-hover rounded mx-auto mb-3" />
        <div className="h-6 w-24 bg-bg-hover rounded mx-auto" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">Failed to load sentiment data</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  const fgi =
    macro?.fear_greed_index ??
    macro?.fear_and_greed ??
    macro?.fgi ??
    50
  const value = Math.max(0, Math.min(100, Math.round(fgi)))
  const label = getSentimentLabel(value)
  const textClass = getSentimentTextClass(value)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h3 className="text-text-primary text-sm font-semibold mb-2">
        Fear &amp; Greed Index
      </h3>

      <GaugeArc value={value} />

      <div className="text-center -mt-1">
        <p className={`text-3xl font-bold tabular-nums ${textClass}`}>
          {value}
        </p>
        <p className={`text-sm font-medium mt-0.5 ${textClass}`}>
          {label}
        </p>
      </div>

      {macro?.updated_at && (
        <p className="text-text-muted text-[10px] mt-3 text-right">
          Updated {formatTimeAgo(macro.updated_at)}
        </p>
      )}
    </div>
  )
}
