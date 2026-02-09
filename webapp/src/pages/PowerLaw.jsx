import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPrice } from '../utils/format'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Brush,
} from 'recharts'

const POLL_INTERVAL = 60_000

const VALUATION_COLORS = {
  'Extremely Undervalued': { text: 'text-accent-green', bg: 'bg-accent-green/15', border: 'border-accent-green/30' },
  'Undervalued': { text: 'text-accent-green', bg: 'bg-accent-green/10', border: 'border-accent-green/20' },
  'Below Fair Value': { text: 'text-accent-green', bg: 'bg-accent-green/8', border: 'border-accent-green/15' },
  'Above Fair Value': { text: 'text-accent-yellow', bg: 'bg-accent-yellow/8', border: 'border-accent-yellow/15' },
  'Overvalued': { text: 'text-accent-red', bg: 'bg-accent-red/10', border: 'border-accent-red/20' },
}

function CorridorGauge({ position, bands, currentPrice }) {
  const pct = Math.max(0, Math.min(100, position * 100))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">CORRIDOR POSITION</h3>
      <div className="relative h-4 bg-gradient-to-r from-accent-green/30 via-accent-yellow/30 to-accent-red/30 rounded-full">
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg border-2 border-accent-blue transition-all duration-700"
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-text-muted">
        <span>Support {bands?.support ? `$${bands.support.toLocaleString()}` : ''}</span>
        <span>Fair {bands?.fair ? `$${bands.fair.toLocaleString()}` : ''}</span>
        <span>Resist {bands?.top_resistance ? `$${bands.top_resistance.toLocaleString()}` : ''}</span>
      </div>
    </div>
  )
}

function StatsGrid({ data }) {
  const stats = [
    { label: 'Days Since Genesis', value: data?.days_since_genesis?.toLocaleString() },
    { label: 'Fair Value', value: data?.fair_value ? `$${data.fair_value.toLocaleString()}` : '--' },
    { label: 'Deviation', value: data?.deviation_pct ? `${data.deviation_pct > 0 ? '+' : ''}${data.deviation_pct.toFixed(1)}%` : '--' },
    { label: 'To Support', value: data?.distance_to_support_pct ? `${data.distance_to_support_pct.toFixed(1)}%` : '--' },
    { label: 'To Resistance', value: data?.distance_to_resistance_pct ? `${data.distance_to_resistance_pct.toFixed(1)}%` : '--' },
    { label: 'Corridor Pos', value: data?.corridor_position ? `${(data.corridor_position * 100).toFixed(0)}%` : '--' },
  ]

  return (
    <div className="grid grid-cols-3 gap-2">
      {stats.map((s) => (
        <div key={s.label} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{s.label}</div>
          <div className="text-text-primary text-sm font-bold tabular-nums">{s.value || '--'}</div>
        </div>
      ))}
    </div>
  )
}

function PowerLawChart({ historicalData }) {
  if (!historicalData?.points?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-64 flex items-center justify-center">
        <span className="text-text-muted text-sm">Loading chart...</span>
      </div>
    )
  }

  // Filter to points that have data
  const chartData = historicalData.points
    .filter((_, i) => i % 7 === 0) // Weekly samples for performance
    .map((p) => ({
      date: p.date,
      fairValue: p.fair_value,
      support: p.support,
      topResistance: p.top_resistance,
      actualPrice: p.actual_price,
    }))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">POWER LAW CORRIDOR</h3>
      <ResponsiveContainer width="100%" height={310}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => v?.slice(5, 10)}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            domain={['auto', 'auto']}
            scale="log"
          />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v, name) => [v ? `$${v.toLocaleString()}` : '--', name]}
          />
          <Area
            dataKey="topResistance"
            stroke="none"
            fill="rgba(255,77,106,0.08)"
            name="Top Resistance"
          />
          <Area
            dataKey="support"
            stroke="none"
            fill="rgba(0,200,83,0.08)"
            name="Support"
          />
          <Line
            dataKey="fairValue"
            stroke="#4a9eff"
            strokeWidth={2}
            dot={false}
            name="Fair Value"
          />
          <Line
            dataKey="support"
            stroke="#00c853"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="Support"
          />
          <Line
            dataKey="topResistance"
            stroke="#ff4d6a"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="Resistance"
          />
          <Line
            dataKey="actualPrice"
            stroke="#ffc107"
            strokeWidth={1.5}
            dot={false}
            name="BTC Price"
            connectNulls
          />
          <Brush
            dataKey="date"
            height={20}
            stroke="#4a9eff"
            fill="#0f0f14"
            tickFormatter={(v) => v?.slice(5, 10)}
            startIndex={Math.max(0, chartData.length - Math.floor(chartData.length * 0.5))}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function PowerLaw() {
  const [current, setCurrent] = useState(null)
  const [historical, setHistorical] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [curr, hist] = await Promise.all([
        api.getPowerLawCurrent(),
        api.getPowerLawHistorical(365),
      ])
      setCurrent(curr)
      setHistorical(hist)
    } catch (err) {
      console.error('Power Law fetch error:', err)
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
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Power Law</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-bg-card rounded-2xl" />
          <div className="h-64 bg-bg-card rounded-2xl" />
          <div className="h-16 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  const valStyle = VALUATION_COLORS[current?.valuation] || VALUATION_COLORS['Above Fair Value']

  return (
    <div className="px-4 pt-4 space-y-3 pb-4">
      <h1 className="text-lg font-bold">Power Law Analysis</h1>

      {/* Valuation Card */}
      {current && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-text-muted text-[10px] font-medium">CURRENT PRICE</div>
              <div className="text-text-primary text-xl font-bold tabular-nums">
                {current.current_price ? formatPrice(current.current_price) : '--'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-text-muted text-[10px] font-medium">FAIR VALUE</div>
              <div className="text-accent-blue text-xl font-bold tabular-nums">
                {current.fair_value ? `$${current.fair_value.toLocaleString()}` : '--'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className={`text-xs font-bold px-2 py-1 rounded border ${valStyle.bg} ${valStyle.border} ${valStyle.text}`}>
              {current.valuation}
            </span>
            <span className={`text-sm font-bold tabular-nums ${current.deviation_pct > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
              {current.deviation_pct > 0 ? '+' : ''}{current.deviation_pct?.toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Chart */}
      <PowerLawChart historicalData={historical} />

      {/* Corridor Gauge */}
      {current && (
        <CorridorGauge
          position={current.corridor_position}
          bands={current.corridor}
          currentPrice={current.current_price}
        />
      )}

      {/* Stats Grid */}
      {current && <StatsGrid data={current} />}

      {/* Educational Section */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">ABOUT THE POWER LAW</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            The Bitcoin Power Law model describes BTC's long-term price trajectory using
            a power law relationship: <span className="text-text-secondary font-mono">Price = 10^(-17.016 + 5.845 * log10(days))</span>
          </p>
          <p>
            <span className="text-text-secondary font-semibold">How it works:</span> BTC's price
            follows a straight line on a log-log chart, with R² &gt; 0.95 over its entire history.
            The model provides a "fair value" corridor — price tends to oscillate between support (0.42x)
            and resistance (1.5x) of the fair value line.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Limitations:</span> Past performance
            doesn't guarantee future results. The model assumes continued adoption growth and doesn't
            account for black swan events or regulatory changes.
          </p>
        </div>
      </div>
    </div>
  )
}
