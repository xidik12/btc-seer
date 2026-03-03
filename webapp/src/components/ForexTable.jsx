import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPercent } from '../utils/format'

const FOREX_PAIRS = [
  { key: 'eurusd', name: 'EUR/USD', base: 'EUR', quote: 'USD' },
  { key: 'gbpusd', name: 'GBP/USD', base: 'GBP', quote: 'USD' },
  { key: 'usdjpy', name: 'USD/JPY', base: 'USD', quote: 'JPY' },
  { key: 'usdchf', name: 'USD/CHF', base: 'USD', quote: 'CHF' },
  { key: 'audusd', name: 'AUD/USD', base: 'AUD', quote: 'USD' },
  { key: 'usdcad', name: 'USD/CAD', base: 'USD', quote: 'CAD' },
  { key: 'nzdusd', name: 'NZD/USD', base: 'NZD', quote: 'USD' },
]

export default function ForexTable({ data: externalData, setData: setExternalData }) {
  const [internalData, setInternalData] = useState(null)
  const data = externalData !== undefined ? externalData : internalData
  const setData = externalData !== undefined ? setExternalData : setInternalData
  const [loading, setLoading] = useState(data === null)

  const fetchForex = useCallback(async () => {
    try {
      const result = await api.getForexData()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [setData])

  useEffect(() => {
    if (data !== null) return
    fetchForex()
  }, [data, fetchForex])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/[0.04] space-y-3 animate-pulse">
        {Array.from({ length: 7 }, (_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-bg-secondary" />
            <div className="flex-1 h-3 w-20 bg-bg-secondary rounded" />
            <div className="h-3 w-16 bg-bg-secondary rounded" />
            <div className="h-5 w-14 bg-bg-secondary rounded-md" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/[0.04]">
      <h3 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">Forex Pairs</h3>

      {/* Column headers */}
      <div className="flex items-center justify-between px-0 pb-2 mb-1 border-b border-white/[0.06]">
        <span className="text-[9px] text-text-muted uppercase font-semibold tracking-wider">Pair</span>
        <div className="flex items-center gap-4">
          <span className="text-[9px] text-text-muted uppercase font-semibold tracking-wider w-20 text-right">Rate</span>
          <span className="text-[9px] text-text-muted uppercase font-semibold tracking-wider w-16 text-right">Change</span>
        </div>
      </div>

      {FOREX_PAIRS.map(({ key, name, base }) => {
        const val = data?.[key]
        const price = val?.price ?? (typeof val === 'number' ? val : null)
        const change = val?.change_1h ?? val?.change_24h ?? null
        const isUp = change >= 0

        return (
          <div key={key} className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center border border-white/[0.06]">
                <span className="text-[10px] font-bold text-text-secondary">{base}</span>
              </div>
              <span className="text-text-primary text-sm font-medium">{name}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-text-primary text-sm font-semibold tabular-nums w-20 text-right">
                {price != null ? price.toFixed(4) : '--'}
              </span>
              {change != null ? (
                <div className={`px-2 py-0.5 rounded-md text-[11px] font-semibold tabular-nums w-16 text-center ${
                  isUp
                    ? 'bg-accent-green/10 text-accent-green'
                    : 'bg-accent-red/10 text-accent-red'
                }`}>
                  {formatPercent(change)}
                </div>
              ) : (
                <span className="text-text-muted text-[11px] w-16 text-center">--</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
