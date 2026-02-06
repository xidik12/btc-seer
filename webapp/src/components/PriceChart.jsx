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
} from 'recharts'
import { api } from '../utils/api.js'
import {
  formatPricePrecise,
  formatPrice,
  formatNumber,
  formatTime,
  formatDate,
} from '../utils/format.js'

const TIMEFRAMES = [
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 },
  { label: '30d', hours: 720 },
]

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null

  const d = payload[0]?.payload
  if (!d) return null

  return (
    <div className="bg-bg-card border border-text-muted/20 rounded-lg px-3 py-2 shadow-xl text-xs">
      <p className="text-text-secondary mb-1">
        {formatDate(d.time)} {formatTime(d.time)}
      </p>
      <div className="space-y-0.5">
        <p className="text-text-primary">
          <span className="text-text-secondary mr-1">O:</span>
          {formatPricePrecise(d.open)}
        </p>
        <p className="text-text-primary">
          <span className="text-text-secondary mr-1">H:</span>
          {formatPricePrecise(d.high)}
        </p>
        <p className="text-text-primary">
          <span className="text-text-secondary mr-1">L:</span>
          {formatPricePrecise(d.low)}
        </p>
        <p className="text-text-primary font-medium">
          <span className="text-text-secondary mr-1">C:</span>
          {formatPricePrecise(d.close)}
        </p>
        <p className="text-text-secondary">
          <span className="mr-1">Vol:</span>
          {formatNumber(d.volume)}
        </p>
      </div>
    </div>
  )
}

function VolumeTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-card border border-text-muted/20 rounded-lg px-2 py-1 shadow-xl text-xs">
      <span className="text-text-secondary">Vol: </span>
      <span className="text-text-primary">{formatNumber(payload[0]?.value)}</span>
    </div>
  )
}

export default function PriceChart() {
  const [timeframe, setTimeframe] = useState(TIMEFRAMES[0])
  const [candles, setCandles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCandles = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getCandles(timeframe.hours)
      const formatted = (data || []).map((c) => ({
        time: c.time || c.timestamp || c.t,
        open: c.open ?? c.o,
        high: c.high ?? c.h,
        low: c.low ?? c.l,
        close: c.close ?? c.c,
        volume: c.volume ?? c.v ?? 0,
      }))
      setCandles(formatted)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [timeframe.hours])

  useEffect(() => {
    setLoading(true)
    fetchCandles()
    const interval = setInterval(fetchCandles, 60_000)
    return () => clearInterval(interval)
  }, [fetchCandles])

  const priceChange =
    candles.length >= 2
      ? candles[candles.length - 1].close - candles[0].close
      : 0
  const isPositive = priceChange >= 0
  const gradientColor = isPositive ? '#00d68f' : '#ff4d6a'
  const strokeColor = isPositive ? '#00d68f' : '#ff4d6a'

  const formatXTick = (tick) => {
    if (!tick) return ''
    if (timeframe.hours <= 24) return formatTime(tick)
    return formatDate(tick)
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-text-primary font-semibold text-sm">
          BTC Price
        </h3>
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.label}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                timeframe.label === tf.label
                  ? 'bg-accent-blue text-white'
                  : 'bg-bg-secondary text-text-secondary hover:text-text-primary'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[200px] flex items-center justify-center">
          <div className="text-text-secondary text-sm pulse-glow">
            Loading chart...
          </div>
        </div>
      ) : error ? (
        <div className="h-[200px] flex flex-col items-center justify-center gap-2">
          <p className="text-accent-red text-sm">Failed to load chart</p>
          <button
            onClick={fetchCandles}
            className="text-accent-blue text-xs hover:underline"
          >
            Retry
          </button>
        </div>
      ) : candles.length === 0 ? (
        <div className="h-[200px] flex items-center justify-center">
          <p className="text-text-secondary text-sm">No data available</p>
        </div>
      ) : (
        <>
          {/* Price area chart */}
          <div className="h-[180px] -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={candles}
                margin={{ top: 4, right: 4, left: 4, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={gradientColor} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={gradientColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#2a2a38"
                  vertical={false}
                />
                <XAxis
                  dataKey="time"
                  tickFormatter={formatXTick}
                  tick={{ fill: '#5a5a70', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={40}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tickFormatter={(v) => formatPrice(v)}
                  tick={{ fill: '#5a5a70', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={60}
                  orientation="right"
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke={strokeColor}
                  strokeWidth={2}
                  fill="url(#priceGradient)"
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: strokeColor,
                    stroke: '#0f0f14',
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Volume bar chart */}
          <div className="h-[48px] -mx-2 mt-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={candles}
                margin={{ top: 0, right: 4, left: 4, bottom: 0 }}
              >
                <XAxis dataKey="time" hide />
                <YAxis hide domain={[0, 'auto']} />
                <Tooltip content={<VolumeTooltip />} />
                <Bar
                  dataKey="volume"
                  fill="#4a9eff"
                  opacity={0.35}
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
