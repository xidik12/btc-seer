import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'
import { api } from '../utils/api.js'
import {
  formatPricePrecise,
  formatPrice,
  formatNumber,
  formatPercent,
  formatTime,
  formatDate,
} from '../utils/format.js'

const TIMEFRAMES = [
  { label: '24H', value: '1d' },
  { label: '1W', value: '1w' },
  { label: '1M', value: '1mo' },
  { label: '1Y', value: '1y' },
  { label: 'ALL', value: 'all' },
]

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null

  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a45] rounded-lg px-3 py-2 shadow-2xl text-xs backdrop-blur-sm">
      <p className="text-[#8888aa] mb-1.5 text-[10px]">
        {formatDate(d.time)} {formatTime(d.time)}
      </p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        <p><span className="text-[#6a6a80]">O </span><span className="text-[#e0e0ee]">{formatPricePrecise(d.open)}</span></p>
        <p><span className="text-[#6a6a80]">H </span><span className="text-[#00d68f]">{formatPricePrecise(d.high)}</span></p>
        <p><span className="text-[#6a6a80]">C </span><span className="text-[#e0e0ee] font-medium">{formatPricePrecise(d.close)}</span></p>
        <p><span className="text-[#6a6a80]">L </span><span className="text-[#ff4d6a]">{formatPricePrecise(d.low)}</span></p>
      </div>
      <div className="mt-1 pt-1 border-t border-[#2a2a45]">
        <p className="text-[#6a6a80]">Vol <span className="text-[#4a9eff]">{formatNumber(d.volume)}</span></p>
      </div>
    </div>
  )
}

function VolumeTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a45] rounded-lg px-2 py-1 shadow-2xl text-xs">
      <span className="text-[#6a6a80]">Vol </span>
      <span className="text-[#4a9eff]">{formatNumber(payload[0]?.value)}</span>
    </div>
  )
}

export default function PriceChart() {
  const [tfIndex, setTfIndex] = useState(0)
  const [candles, setCandles] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const timeframe = TIMEFRAMES[tfIndex]

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getPriceStats(timeframe.value)

      if (data?.error) {
        setError(data.error)
        setCandles([])
        setStats(null)
        return
      }

      const formatted = (data?.candles || []).map((c) => ({
        time: c.timestamp || c.time || c.t,
        open: c.open ?? c.o,
        high: c.high ?? c.h,
        low: c.low ?? c.l,
        close: c.close ?? c.c,
        volume: c.volume ?? c.v ?? 0,
      }))
      setCandles(formatted)
      setStats({
        price: data.current_price,
        change: data.change,
        changePct: data.change_pct,
        high: data.high,
        low: data.low,
        volume: data.volume,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [timeframe.value])

  useEffect(() => {
    setLoading(true)
    fetchData()
    const interval = setInterval(fetchData, 60_000)
    return () => clearInterval(interval)
  }, [fetchData])

  const isPositive = (stats?.change ?? 0) >= 0
  const accentColor = isPositive ? '#00d68f' : '#ff4d6a'
  const dimColor = isPositive ? 'rgba(0,214,143,0.08)' : 'rgba(255,77,106,0.08)'

  const formatXTick = (tick) => {
    if (!tick) return ''
    const tf = timeframe.value
    if (tf === '1d') return formatTime(tick)
    if (tf === '1w') return new Date(tick).toLocaleDateString('en-US', { weekday: 'short' })
    if (tf === '1mo') return formatDate(tick)
    // 1y, all — show month + year
    return new Date(tick).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
  }

  // Calculate Y domain with padding
  const prices = candles.map((c) => c.close).filter(Boolean)
  const minP = Math.min(...prices)
  const maxP = Math.max(...prices)
  const pad = (maxP - minP) * 0.05 || 100
  const yDomain = prices.length ? [minP - pad, maxP + pad] : ['auto', 'auto']

  // Average line
  const avgPrice = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null

  return (
    <div className="bg-bg-card rounded-2xl overflow-hidden slide-up">
      {/* Header with stats */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h3 className="text-text-primary font-semibold text-sm">BTC Price</h3>
            {stats && (
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${isPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                {isPositive ? '+' : ''}{stats.changePct?.toFixed(2)}%
              </span>
            )}
          </div>
          {stats && (
            <div className="flex items-center gap-3 text-[10px] text-text-muted">
              <span>H <span className="text-accent-green">{formatPrice(stats.high)}</span></span>
              <span>L <span className="text-accent-red">{formatPrice(stats.low)}</span></span>
            </div>
          )}
        </div>

        {/* Timeframe buttons */}
        <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
          {TIMEFRAMES.map((tf, i) => (
            <button
              key={tf.label}
              onClick={() => setTfIndex(i)}
              className={`flex-1 px-2 py-1 rounded-md text-[11px] font-semibold transition-all duration-200 ${
                tfIndex === i
                  ? 'bg-accent-blue text-white shadow-sm shadow-accent-blue/25'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[220px] flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
            <span className="text-text-muted text-xs">Loading chart...</span>
          </div>
        </div>
      ) : error ? (
        <div className="h-[220px] flex flex-col items-center justify-center gap-2">
          <p className="text-accent-red text-sm">Failed to load chart</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      ) : candles.length === 0 ? (
        <div className="h-[220px] flex items-center justify-center">
          <p className="text-text-secondary text-sm">No data available</p>
        </div>
      ) : (
        <>
          {/* Price area chart */}
          <div className="h-[210px] px-1 relative">
            {/* Timeframe label overlay */}
            <div className="absolute top-2 left-14 z-10 text-[10px] text-[#3a3a55] font-semibold tracking-wider">
              BTC/USDT {timeframe.label}
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={candles} margin={{ top: 8, right: 56, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.20} />
                    <stop offset="50%" stopColor={accentColor} stopOpacity={0.06} />
                    <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 6"
                  stroke="#1e1e30"
                  vertical={false}
                />
                {avgPrice && (
                  <ReferenceLine
                    y={avgPrice}
                    stroke="#3a3a55"
                    strokeDasharray="4 4"
                    strokeWidth={0.5}
                    label={{ value: 'AVG', position: 'insideTopLeft', fill: '#3a3a55', fontSize: 8 }}
                  />
                )}
                {stats?.price && (
                  <ReferenceLine
                    y={stats.price}
                    stroke={accentColor}
                    strokeDasharray="2 3"
                    strokeWidth={0.8}
                    label={{ value: formatPrice(stats.price), position: 'right', fill: accentColor, fontSize: 9 }}
                  />
                )}
                <XAxis
                  dataKey="time"
                  tickFormatter={formatXTick}
                  tick={{ fill: '#4a4a66', fontSize: 9 }}
                  axisLine={{ stroke: '#1e1e30' }}
                  tickLine={false}
                  minTickGap={40}
                />
                <YAxis
                  yAxisId="left"
                  domain={yDomain}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                  tick={{ fill: '#4a4a66', fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                  orientation="left"
                />
                <YAxis
                  yAxisId="right"
                  domain={yDomain}
                  tickFormatter={(v) => formatPrice(v)}
                  tick={{ fill: '#5a5a77', fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  width={54}
                  orientation="right"
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="close"
                  stroke={accentColor}
                  strokeWidth={1.5}
                  fill="url(#priceGradient)"
                  dot={false}
                  activeDot={{
                    r: 3,
                    fill: accentColor,
                    stroke: '#0f0f14',
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Volume bar chart */}
          <div className="h-[40px] px-1 mb-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={candles} margin={{ top: 0, right: 56, left: 4, bottom: 0 }}>
                <XAxis dataKey="time" hide />
                <YAxis
                  yAxisId="vol-left"
                  orientation="left"
                  width={48}
                  tickFormatter={(v) => v > 1000 ? `${(v/1000).toFixed(0)}k` : v.toFixed(0)}
                  tick={{ fill: '#3a3a55', fontSize: 8 }}
                  axisLine={false}
                  tickLine={false}
                  domain={[0, 'auto']}
                  tickCount={2}
                />
                <YAxis yAxisId="vol-right" orientation="right" width={54} hide domain={[0, 'auto']} />
                <Tooltip content={<VolumeTooltip />} />
                <Bar
                  yAxisId="vol-left"
                  dataKey="volume"
                  fill="#4a9eff"
                  opacity={0.25}
                  radius={[1, 1, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
