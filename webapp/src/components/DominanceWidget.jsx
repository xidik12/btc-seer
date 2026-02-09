import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import { formatPercent } from '../utils/format.js'
import { useChartZoom } from '../hooks/useChartZoom'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'

export default function DominanceWidget() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const res = await api.getDominanceData(30)
      setData(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 300_000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Extract dominance value safely
  const current = typeof data?.current?.btc_dominance === 'number'
    ? data.current.btc_dominance
    : typeof data?.dominance === 'number'
    ? data.dominance
    : null

  const change24h = typeof data?.current?.market_cap_change_24h === 'number'
    ? data.current.market_cap_change_24h
    : null

  const rawHistory = Array.isArray(data?.history) ? data.history : []
  const history = rawHistory
    .map(h => ({
      date: (typeof h?.timestamp === 'string' ? h.timestamp.slice(0, 10) : h?.date) || '',
      dominance: typeof h?.btc_dominance === 'number' ? h.btc_dominance
        : typeof h?.dominance === 'number' ? h.dominance
        : null,
    }))
    .filter(h => h.dominance != null)

  const isUp = change24h != null ? change24h >= 0 : true
  const { data: visibleHistory, bindGestures, isZoomed, resetZoom } = useChartZoom(history)

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-3">BTC Dominance</h3>
        <div className="animate-pulse">
          <div className="h-24 bg-bg-secondary rounded-xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-2">BTC Dominance</h3>
        <div className="flex flex-col items-center py-4 gap-2">
          <p className="text-accent-red text-sm">Failed to load</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  // No data yet — show waiting state (not an error)
  if (current == null) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-2">BTC Dominance</h3>
        <div className="flex flex-col items-center py-6 gap-2">
          <p className="text-text-muted text-sm">Collecting data...</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Refresh</button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary font-semibold text-sm">BTC Dominance</h3>
        <div className="flex items-center gap-2">
          {isZoomed && (
            <button onClick={resetZoom} className="text-[10px] text-accent-blue">Reset</button>
          )}
          <span className="text-text-muted text-[10px]">
            {isUp ? 'Risk-off (money to BTC)' : 'Risk-on (money to alts)'}
          </span>
        </div>
      </div>

      <div className="flex items-end gap-3 mb-3">
        <span className="text-2xl font-bold text-text-primary tabular-nums">
          {current.toFixed(1)}%
        </span>
        {change24h != null && (
          <span className={`text-sm font-medium ${isUp ? 'text-accent-green' : 'text-accent-red'}`}>
            {formatPercent(change24h)} 24h
          </span>
        )}
      </div>

      {history.length > 2 && (
        <div className="h-[80px]" {...bindGestures}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={visibleHistory} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="domGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ffb800" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#ffb800" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis domain={['dataMin - 0.5', 'dataMax + 0.5']} hide />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(v) => [typeof v === 'number' ? `${v.toFixed(2)}%` : '--', 'Dominance']}
                labelFormatter={(d) => d || ''}
              />
              <Area
                type="monotone"
                dataKey="dominance"
                stroke="#ffb800"
                strokeWidth={1.5}
                fill="url(#domGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      {history.length > 2 && (
        <p className="text-text-muted text-[9px] text-center mt-1.5">Pinch to zoom &middot; Drag to pan</p>
      )}

      <p className="text-text-muted text-[10px] mt-2">
        {current > 55
          ? 'High dominance signals capital flowing into BTC as a safe haven. Altcoins may underperform.'
          : current < 45
          ? 'Low dominance signals alt season. Capital is flowing into riskier assets.'
          : 'Moderate dominance. Market is balanced between BTC and altcoins.'}
      </p>
    </div>
  )
}
