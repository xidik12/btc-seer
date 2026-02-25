import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent } from '../utils/format'

const FOREX_PAIRS = [
  { key: 'eurusd', name: 'EUR/USD', flag: 'EU' },
  { key: 'gbpusd', name: 'GBP/USD', flag: 'GB' },
  { key: 'usdjpy', name: 'USD/JPY', flag: 'JP' },
  { key: 'usdchf', name: 'USD/CHF', flag: 'CH' },
  { key: 'audusd', name: 'AUD/USD', flag: 'AU' },
  { key: 'usdcad', name: 'USD/CAD', flag: 'CA' },
  { key: 'nzdusd', name: 'NZD/USD', flag: 'NZ' },
]

export default function ForexTable() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchForex = useCallback(async () => {
    try {
      const result = await api.getForexData()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchForex()
    const iv = setInterval(fetchForex, 120_000)
    return () => clearInterval(iv)
  }, [fetchForex])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-xl p-4 animate-pulse">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div key={i} className="h-10 bg-bg-secondary rounded mb-2" />
        ))}
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-xl p-4">
      <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 text-[10px] text-text-muted uppercase font-semibold pb-2 border-b border-white/5">
        <span>Pair</span>
        <span className="text-right">Bid</span>
        <span className="text-right w-16">Change</span>
      </div>

      {FOREX_PAIRS.map(({ key, name, flag }) => {
        const val = data?.[key]
        const price = val?.price ?? (typeof val === 'number' ? val : null)
        const change = val?.change_1h ?? val?.change_24h ?? null
        const isUp = change >= 0

        return (
          <div key={key} className="grid grid-cols-[1fr_auto_auto] gap-x-3 items-center py-2.5 border-b border-white/5 last:border-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono bg-bg-secondary rounded px-1.5 py-0.5 text-text-muted">{flag}</span>
              <span className="text-text-primary text-sm font-medium">{name}</span>
            </div>
            <span className="text-text-primary text-sm font-semibold tabular-nums text-right">
              {price != null ? price.toFixed(4) : '--'}
            </span>
            <span className={`text-[10px] font-semibold text-right w-16 ${
              change != null ? (isUp ? 'text-accent-green' : 'text-accent-red') : 'text-text-muted'
            }`}>
              {change != null ? formatPercent(change) : '--'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
