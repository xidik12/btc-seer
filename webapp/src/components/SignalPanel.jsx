import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
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
  safeFixed,
} from '../utils/format.js'
import CardShareButton from './CardShareButton'

const POLL_INTERVAL = 60_000

const ACTION_ICONS = {
  strong_buy: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M12 19V5M5 12l7-7 7 7" />
      <path d="M5 5h14" />
    </svg>
  ),
  buy: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  ),
  hold: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M5 12h14" />
    </svg>
  ),
  sell: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M12 5v14M5 12l7 7 7-7" />
    </svg>
  ),
  strong_sell: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M12 5v14M5 12l7 7 7-7" />
      <path d="M5 19h14" />
    </svg>
  ),
}

function getActionDisplay(action, t) {
  const ACTION_DISPLAY = {
    strong_buy: { label: t('common:signal.strongBuy') },
    buy: { label: t('common:signal.buy') },
    hold: { label: t('common:signal.hold') },
    sell: { label: t('common:signal.sell') },
    strong_sell: { label: t('common:signal.strongSell') },
  }
  return ACTION_DISPLAY[action] ?? { label: action ?? t('common:signal.hold') }
}

export default function SignalPanel() {
  const { t } = useTranslation('dashboard')
  const [signal, setSignal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const cardRef = useRef(null)

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
        <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('signalPanel.title') })}</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          {t('common:app.retry')}
        </button>
      </div>
    )
  }

  // Extract signal data — API returns {signals: {"1h": {...}, ...}}
  const sigMap = signal?.signals ?? signal ?? {}
  const s = sigMap['1h'] ?? sigMap['4h'] ?? sigMap['24h'] ?? sigMap ?? {}

  const action = s?.action ?? 'hold'
  const display = getActionDisplay(action, t)
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
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 gradient-border slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary text-sm font-semibold">{t('signalPanel.title')}</h3>
        <CardShareButton cardRef={cardRef} label="Signal Panel" filename="signal-panel.png" />
      </div>

      {/* Action Badge */}
      <div className="flex justify-center mb-4">
        <div
          className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border text-lg font-bold ${actionBgClass} ${actionColorClass}`}
        >
          <span>{ACTION_ICONS[action] || ACTION_ICONS.hold}</span>
          <span>{display.label}</span>
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="text-text-secondary text-xs">{t('signalPanel.confidence')}</span>
        <span className={`text-sm font-semibold ${actionColorClass}`}>
          {safeFixed(confidence, 0)}%
        </span>
      </div>

      {/* Price Levels */}
      <div className="space-y-2 mb-4">
        {entry != null && (
          <PriceRow label={t('signalPanel.entry')} value={entry} colorClass="text-accent-blue" />
        )}
        {target != null && (
          <PriceRow label={t('signalPanel.target')} value={target} colorClass="text-accent-green" />
        )}
        {stopLoss != null && (
          <PriceRow label={t('signalPanel.stopLoss')} value={stopLoss} colorClass="text-accent-red" />
        )}
      </div>

      {/* Risk Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-text-secondary text-xs">{t('signalPanel.riskLevel')}</span>
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
          <span className="text-text-muted text-[10px]">{t('signalPanel.low')}</span>
          <span className="text-text-muted text-[10px]">{t('signalPanel.high')}</span>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-text-muted text-[10px] leading-relaxed border-t border-white/5 pt-3">
        {t('signalPanel.disclaimer')}
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
