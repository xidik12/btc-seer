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

const ACTION_DISPLAY = {
  strong_buy: { label: 'Strong Buy', emoji: '\uD83D\uDE80' },
  buy: { label: 'Buy', emoji: '\u2705' },
  hold: { label: 'Hold', emoji: '\u23F8\uFE0F' },
  sell: { label: 'Sell', emoji: '\u26A0\uFE0F' },
  strong_sell: { label: 'Strong Sell', emoji: '\uD83D\uDEA8' },
}

function getActionDisplay(action) {
  return ACTION_DISPLAY[action] ?? { label: action ?? 'Unknown', emoji: '\u2753' }
}

export default function SignalPanel() {
  const [signal, setSignal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getCurrentSignals()
      setSignal(data)
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
        <div className="h-5 w-32 bg-bg-hover rounded mb-4" />
        <div className="h-12 w-40 bg-bg-hover rounded mx-auto mb-4" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 w-full bg-bg-hover rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">Failed to load signals</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  // Extract signal data — API returns {signals: {"1h": {...}, ...}}
  const sigMap = signal?.signals ?? signal ?? {}
  const s = sigMap['1h'] ?? sigMap['4h'] ?? sigMap['24h'] ?? sigMap ?? {}

  const action = s?.action ?? 'hold'
  const display = getActionDisplay(action)
  const actionColorClass = getActionColor(action)
  const actionBgClass = getActionBg(action)
  const confidence = s?.confidence ?? 0
  const risk = s?.risk_rating ?? s?.risk ?? s?.risk_level ?? 5
  const entry = s?.entry_price ?? s?.entry
  const target = s?.target_price ?? s?.target
  const stopLoss = s?.stop_loss ?? s?.stop_loss_price

  const riskClamped = Math.max(1, Math.min(10, Math.round(risk)))
  const riskPercent = (riskClamped / 10) * 100
  const riskColor =
    riskClamped <= 3
      ? 'bg-accent-green'
      : riskClamped <= 6
      ? 'bg-accent-yellow'
      : 'bg-accent-red'

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <h3 className="text-text-primary text-sm font-semibold mb-3">
        Trading Signal
      </h3>

      {/* Action Badge */}
      <div className="flex justify-center mb-4">
        <div
          className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border text-lg font-bold ${actionBgClass} ${actionColorClass}`}
        >
          <span className="text-xl">{display.emoji}</span>
          <span>{display.label}</span>
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="text-text-secondary text-xs">Confidence</span>
        <span className={`text-sm font-semibold ${actionColorClass}`}>
          {confidence.toFixed(0)}%
        </span>
      </div>

      {/* Price Levels */}
      <div className="space-y-2 mb-4">
        {entry != null && (
          <PriceRow label="Entry" value={entry} colorClass="text-accent-blue" />
        )}
        {target != null && (
          <PriceRow label="Target" value={target} colorClass="text-accent-green" />
        )}
        {stopLoss != null && (
          <PriceRow label="Stop-Loss" value={stopLoss} colorClass="text-accent-red" />
        )}
      </div>

      {/* Risk Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-text-secondary text-xs">Risk Level</span>
          <span className="text-text-primary text-xs font-semibold">
            {riskClamped}/10
          </span>
        </div>
        <div className="w-full h-2 bg-bg-primary rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${riskColor}`}
            style={{ width: `${riskPercent}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-text-muted text-[10px]">Low</span>
          <span className="text-text-muted text-[10px]">High</span>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-text-muted text-[10px] leading-relaxed border-t border-white/5 pt-3">
        Not financial advice. AI-generated signals are for informational purposes
        only. Always do your own research before making trading decisions.
      </p>
    </div>
  )
}

function PriceRow({ label, value, colorClass }) {
  return (
    <div className="flex items-center justify-between bg-bg-secondary rounded-lg px-3 py-2">
      <span className="text-text-secondary text-xs">{label}</span>
      <span className={`text-sm font-semibold tabular-nums ${colorClass}`}>
        {formatPrice(value)}
      </span>
    </div>
  )
}
