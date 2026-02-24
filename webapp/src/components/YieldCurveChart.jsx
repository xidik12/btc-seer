import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

const YIELD_LABELS = {
  treasury_2y: '2Y',
  treasury_5y: '5Y',
  treasury_10y: '10Y',
  treasury_30y: '30Y',
}

export default function YieldCurveChart() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchYields = useCallback(async () => {
    try {
      const result = await api.getYieldCurve()
      setData(result)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchYields()
    const iv = setInterval(fetchYields, 120_000)
    return () => clearInterval(iv)
  }, [fetchYields])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-4 w-28 bg-bg-secondary rounded mb-4" />
        <div className="h-32 bg-bg-secondary rounded" />
      </div>
    )
  }

  if (!data?.current) return null

  const current = data.current
  const inverted = data.inverted

  // Build curve data points
  const curveData = ['treasury_2y', 'treasury_5y', 'treasury_10y', 'treasury_30y']
    .map((key) => ({
      maturity: YIELD_LABELS[key],
      yield: current[key] ?? null,
    }))
    .filter((d) => d.yield !== null)

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary font-semibold text-sm">Yield Curve</h3>
        {inverted && (
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-accent-red/15 text-accent-red">
            INVERTED
          </span>
        )}
      </div>

      {/* Current yields */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        {curveData.map((d) => (
          <div key={d.maturity} className="text-center">
            <p className="text-text-muted text-[10px]">{d.maturity}</p>
            <p className="text-text-primary text-sm font-semibold tabular-nums">{d.yield?.toFixed(2)}%</p>
          </div>
        ))}
      </div>

      {curveData.length >= 2 && (
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={curveData} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="maturity" tick={{ fontSize: 10, fill: '#888' }} />
            <YAxis tick={{ fontSize: 10, fill: '#888' }} domain={['dataMin - 0.5', 'dataMax + 0.5']} />
            <Tooltip
              contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              labelStyle={{ color: '#aaa' }}
            />
            <Area
              type="monotone"
              dataKey="yield"
              stroke={inverted ? '#ef4444' : '#4a9eff'}
              fill={inverted ? 'rgba(239,68,68,0.1)' : 'rgba(74,158,255,0.1)'}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {inverted && (
        <p className="text-accent-red text-[10px] mt-2 text-center">
          2Y yield ({current.treasury_2y?.toFixed(2)}%) exceeds 10Y ({current.treasury_10y?.toFixed(2)}%) — historically signals recession risk
        </p>
      )}
    </div>
  )
}
