import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'

const COINS = [
  { id: 'bitcoin', label: 'BTC' },
  { id: 'ethereum', label: 'ETH' },
  { id: 'solana', label: 'SOL' },
  { id: 'ripple', label: 'XRP' },
]

export default function PriceAlerts() {
  const { t } = useTranslation('common')
  const { tg } = useTelegram()
  const [alerts, setAlerts] = useState([])
  const [activeCount, setActiveCount] = useState(0)
  const [loading, setLoading] = useState(true)

  // Form state
  const [coinId, setCoinId] = useState('bitcoin')
  const [targetPrice, setTargetPrice] = useState('')
  const [direction, setDirection] = useState('above')
  const [isRepeating, setIsRepeating] = useState(false)
  const [note, setNote] = useState('')
  const [creating, setCreating] = useState(false)
  const [currentPrice, setCurrentPrice] = useState(null)

  const initData = tg?.initData

  const fetchAlerts = useCallback(() => {
    if (!initData) return
    api.getUserAlerts(initData)
      .then((res) => {
        setAlerts(res.alerts || [])
        setActiveCount(res.active_count || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [initData])

  useEffect(() => {
    fetchAlerts()
    api.getCurrentPrice()
      .then((res) => setCurrentPrice(res?.price || res?.close))
      .catch(() => {})
  }, [fetchAlerts])

  const handleCreate = async () => {
    if (!initData || !targetPrice) return
    setCreating(true)
    try {
      await api.createAlert(initData, {
        coin_id: coinId,
        target_price: parseFloat(targetPrice),
        direction,
        is_repeating: isRepeating,
        note: note || undefined,
      })
      setTargetPrice('')
      setNote('')
      setIsRepeating(false)
      fetchAlerts()
    } catch (err) {
      alert(err.message || 'Failed to create alert')
    }
    setCreating(false)
  }

  const handleDelete = async (alertId) => {
    if (!initData) return
    try {
      await api.deleteAlert(initData, alertId)
      fetchAlerts()
    } catch {}
  }

  const activeAlerts = alerts.filter((a) => a.is_active)
  const triggeredAlerts = alerts.filter((a) => !a.is_active && a.triggered_at)

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Price Alerts</h1>

      {/* Create Form */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 space-y-3">
        <h3 className="text-sm font-semibold text-text-primary">New Alert</h3>

        {/* Coin selector */}
        <div className="flex gap-2">
          {COINS.map((c) => (
            <button
              key={c.id}
              onClick={() => setCoinId(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                coinId === c.id
                  ? 'bg-accent-blue text-white'
                  : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Price input */}
        <div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              placeholder={`Target price${currentPrice ? ` (now $${Number(currentPrice).toLocaleString()})` : ''}`}
              className="flex-1 bg-bg-secondary rounded-xl px-3 py-2.5 text-sm text-text-primary placeholder-text-muted border border-white/5 outline-none focus:border-accent-blue/30"
            />
          </div>
        </div>

        {/* Direction toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => setDirection('above')}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-colors ${
              direction === 'above'
                ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                : 'bg-bg-secondary text-text-muted border border-white/5'
            }`}
          >
            Above ↑
          </button>
          <button
            onClick={() => setDirection('below')}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-colors ${
              direction === 'below'
                ? 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                : 'bg-bg-secondary text-text-muted border border-white/5'
            }`}
          >
            Below ↓
          </button>
        </div>

        {/* Options row */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={isRepeating}
              onChange={(e) => setIsRepeating(e.target.checked)}
              className="rounded"
            />
            Repeating
          </label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note (optional)"
            className="flex-1 bg-bg-secondary rounded-lg px-2 py-1.5 text-xs text-text-primary placeholder-text-muted border border-white/5 outline-none"
          />
        </div>

        <button
          onClick={handleCreate}
          disabled={creating || !targetPrice}
          className="w-full py-2.5 rounded-xl bg-accent-blue text-white font-semibold text-sm disabled:opacity-50 active:scale-[0.98] transition-all"
        >
          {creating ? 'Creating...' : 'Create Alert'}
        </button>

        <p className="text-text-muted text-[10px] text-center">
          {activeCount}/10 alerts used
        </p>
      </div>

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-text-primary">Active Alerts</h3>
          {activeAlerts.map((a) => (
            <div key={a.id} className="bg-bg-card rounded-xl p-3 border border-white/5 flex items-center justify-between slide-up">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold ${a.direction === 'above' ? 'text-accent-green' : 'text-accent-red'}`}>
                    {a.coin_id?.toUpperCase()?.slice(0, 6)} {a.direction === 'above' ? '↑' : '↓'} ${Number(a.target_price).toLocaleString()}
                  </span>
                  {a.is_repeating && <span className="text-[10px] text-accent-blue">🔄</span>}
                </div>
                {a.note && <p className="text-text-muted text-[10px] mt-0.5">{a.note}</p>}
              </div>
              <button
                onClick={() => handleDelete(a.id)}
                className="text-accent-red/60 hover:text-accent-red text-xs p-1"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Triggered History */}
      {triggeredAlerts.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-text-muted">Triggered</h3>
          {triggeredAlerts.slice(0, 10).map((a) => (
            <div key={a.id} className="bg-bg-card/50 rounded-xl p-3 border border-white/5 opacity-60">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted">
                  {a.coin_id?.toUpperCase()?.slice(0, 6)} {a.direction} ${Number(a.target_price).toLocaleString()}
                </span>
                <span className="text-[10px] text-text-muted">
                  @ ${a.triggered_price ? Number(a.triggered_price).toLocaleString() : '—'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-8">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  )
}
