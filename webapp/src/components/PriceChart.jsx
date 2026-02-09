import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  LineChart,
  Brush,
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
  { label: '24H', value: '1d' },
  { label: '1W', value: '1w' },
  { label: '1M', value: '1mo' },
  { label: '1Y', value: '1y' },
  { label: 'ALL', value: 'all' },
]

// ── Frontend indicator calculations from candle data ──

function computeEMA(data, key, period) {
  const k = 2 / (period + 1)
  const result = []
  let ema = null
  for (let i = 0; i < data.length; i++) {
    const val = data[i][key]
    if (val == null) { result.push(null); continue }
    if (ema === null) { ema = val } else { ema = val * k + ema * (1 - k) }
    result.push(i >= period - 1 ? ema : null)
  }
  return result
}

function computeSMA(data, key, period) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j][key] || 0
    result.push(sum / period)
  }
  return result
}

function computeRSI(data, key, period = 14) {
  const result = []
  let avgGain = 0, avgLoss = 0
  for (let i = 0; i < data.length; i++) {
    if (i === 0) { result.push(null); continue }
    const change = (data[i][key] || 0) - (data[i - 1][key] || 0)
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? -change : 0

    if (i <= period) {
      avgGain += gain / period
      avgLoss += loss / period
      result.push(i === period ? (avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)) : null)
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
      result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss))
    }
  }
  return result
}

function computeBB(data, key, period = 20, mult = 2) {
  const sma = computeSMA(data, key, period)
  const upper = [], lower = []
  for (let i = 0; i < data.length; i++) {
    if (sma[i] == null) { upper.push(null); lower.push(null); continue }
    let sumSq = 0
    for (let j = i - period + 1; j <= i; j++) {
      const diff = (data[j][key] || 0) - sma[i]
      sumSq += diff * diff
    }
    const std = Math.sqrt(sumSq / period)
    upper.push(sma[i] + mult * std)
    lower.push(sma[i] - mult * std)
  }
  return { sma, upper, lower }
}

// ── Tooltips ──

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
      {d.ema9 && (
        <div className="mt-1 pt-1 border-t border-[#2a2a45] grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px]">
          <p><span className="text-[#ffbb33]">EMA9 </span><span className="text-[#aaa]">{formatPrice(d.ema9)}</span></p>
          <p><span className="text-[#33bbff]">EMA21 </span><span className="text-[#aaa]">{formatPrice(d.ema21)}</span></p>
          {d.ema50 && <p><span className="text-[#ff66aa]">EMA50 </span><span className="text-[#aaa]">{formatPrice(d.ema50)}</span></p>}
          {d.rsi && <p><span className="text-[#aa88ff]">RSI </span><span className="text-[#aaa]">{d.rsi.toFixed(1)}</span></p>}
        </div>
      )}
    </div>
  )
}

function RsiTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const rsi = payload[0]?.value
  if (rsi == null) return null
  const color = rsi > 70 ? '#ff4d6a' : rsi < 30 ? '#00d68f' : '#aaa'
  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a45] rounded-lg px-2 py-1 shadow-2xl text-xs">
      <span style={{ color }}>RSI {rsi.toFixed(1)}</span>
    </div>
  )
}

// ── Indicator toggles ──

const OVERLAYS = [
  { key: 'ema', label: 'EMA', default: true },
  { key: 'bb', label: 'BB', default: false },
  { key: 'vol', label: 'Vol', default: true },
  { key: 'rsi', label: 'RSI', default: false },
]

export default function PriceChart() {
  const [tfIndex, setTfIndex] = useState(0)
  const [candles, setCandles] = useState([])
  const [stats, setStats] = useState(null)
  const [indicators, setIndicators] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [overlays, setOverlays] = useState(() => {
    const m = {}
    OVERLAYS.forEach((o) => { m[o.key] = o.default })
    return m
  })

  const timeframe = TIMEFRAMES[tfIndex]

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const [priceData, indData] = await Promise.all([
        api.getPriceStats(timeframe.value),
        api.getIndicators().catch(() => null),
      ])

      if (priceData?.error) {
        setError(priceData.error)
        setCandles([])
        setStats(null)
        return
      }

      const formatted = (priceData?.candles || []).map((c) => ({
        time: c.timestamp || c.time || c.t,
        open: Number(c.open ?? c.o) || 0,
        high: Number(c.high ?? c.h) || 0,
        low: Number(c.low ?? c.l) || 0,
        close: Number(c.close ?? c.c) || 0,
        volume: Number(c.volume ?? c.v) || 0,
      }))
      setCandles(formatted)
      setStats({
        price: priceData.current_price,
        change: priceData.change,
        changePct: priceData.change_pct,
        high: priceData.high,
        low: priceData.low,
        volume: priceData.volume,
      })
      setIndicators(indData)
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

  // Compute chart data with indicators
  const chartData = useMemo(() => {
    if (!candles.length) return []

    const ema9 = computeEMA(candles, 'close', 9)
    const ema21 = computeEMA(candles, 'close', 21)
    const ema50 = computeEMA(candles, 'close', 50)
    const bb = computeBB(candles, 'close', 20, 2)
    const rsi = computeRSI(candles, 'close', 14)

    return candles.map((c, i) => ({
      ...c,
      ema9: ema9[i],
      ema21: ema21[i],
      ema50: ema50[i],
      bbUpper: bb.upper[i],
      bbMiddle: bb.sma[i],
      bbLower: bb.lower[i],
      rsi: rsi[i],
    }))
  }, [candles])

  const isPositive = (stats?.change ?? 0) >= 0
  const accentColor = isPositive ? '#00d68f' : '#ff4d6a'

  const formatXTick = (tick) => {
    if (!tick) return ''
    const tf = timeframe.value
    if (tf === '1d') return formatTime(tick)
    if (tf === '1w') return new Date(tick).toLocaleDateString('en-US', { weekday: 'short' })
    if (tf === '1mo') return formatDate(tick)
    return new Date(tick).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
  }

  // Y domain with padding
  const closePrices = chartData.map((c) => c.close).filter((v) => v > 0)
  const allPrices = overlays.bb
    ? [
        ...closePrices,
        ...chartData.map((c) => c.bbUpper).filter(Boolean),
        ...chartData.map((c) => c.bbLower).filter(Boolean),
      ]
    : closePrices

  const minP = allPrices.length ? Math.min(...allPrices) : 0
  const maxP = allPrices.length ? Math.max(...allPrices) : 100000
  const pad = (maxP - minP) * 0.05 || 100
  const yDomain = allPrices.length ? [minP - pad, maxP + pad] : ['auto', 'auto']

  // Support / Resistance from indicators
  const support = indicators?.levels?.support_1
  const resistance = indicators?.levels?.resistance_1

  const toggleOverlay = (key) => setOverlays((o) => ({ ...o, [key]: !o[key] }))

  return (
    <div className="bg-bg-card rounded-2xl overflow-hidden slide-up">
      {/* Header */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h3 className="text-text-primary font-semibold text-sm">BTC Chart</h3>
            {stats && (
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${isPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                {isPositive ? '+' : ''}{Number(stats.changePct || 0).toFixed(2)}%
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
        <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5 mb-2">
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

        {/* Indicator toggle pills */}
        <div className="flex gap-1.5">
          {OVERLAYS.map((o) => (
            <button
              key={o.key}
              onClick={() => toggleOverlay(o.key)}
              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors border ${
                overlays[o.key]
                  ? 'bg-accent-blue/15 text-accent-blue border-accent-blue/30'
                  : 'bg-transparent text-text-muted border-white/10'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[240px] flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
            <span className="text-text-muted text-xs">Loading chart...</span>
          </div>
        </div>
      ) : error ? (
        <div className="h-[240px] flex flex-col items-center justify-center gap-2">
          <p className="text-accent-red text-sm">Failed to load chart</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center">
          <p className="text-text-secondary text-sm">No data available</p>
        </div>
      ) : (
        <>
          {/* Main price chart with overlays */}
          <div className="h-[250px] px-1 relative">
            <div className="absolute top-2 left-14 z-10 text-[10px] text-[#3a3a55] font-semibold tracking-wider">
              BTC/USDT {timeframe.label}
            </div>

            {/* MA Legend */}
            {overlays.ema && (
              <div className="absolute top-2 right-14 z-10 flex gap-2 text-[8px] font-semibold">
                <span style={{ color: '#ffbb33' }}>EMA9</span>
                <span style={{ color: '#33bbff' }}>EMA21</span>
                <span style={{ color: '#ff66aa' }}>EMA50</span>
              </div>
            )}

            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.15} />
                    <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="bbGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4a9eff" stopOpacity={0.08} />
                    <stop offset="100%" stopColor="#4a9eff" stopOpacity={0.02} />
                  </linearGradient>
                </defs>

                <CartesianGrid strokeDasharray="3 6" stroke="#1e1e30" vertical={false} />

                <XAxis
                  dataKey="time"
                  tickFormatter={formatXTick}
                  tick={{ fill: '#4a4a66', fontSize: 9 }}
                  axisLine={{ stroke: '#1e1e30' }}
                  tickLine={false}
                  minTickGap={40}
                />
                <YAxis
                  yAxisId="price"
                  domain={yDomain}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                  tick={{ fill: '#4a4a66', fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />

                <Tooltip content={<ChartTooltip />} />

                {/* Bollinger Bands */}
                {overlays.bb && (
                  <>
                    <Area
                      yAxisId="price"
                      type="monotone"
                      dataKey="bbUpper"
                      stroke="#4a9eff"
                      strokeWidth={0.5}
                      strokeDasharray="3 3"
                      fill="none"
                      dot={false}
                      isAnimationActive={false}
                    />
                    <Area
                      yAxisId="price"
                      type="monotone"
                      dataKey="bbLower"
                      stroke="#4a9eff"
                      strokeWidth={0.5}
                      strokeDasharray="3 3"
                      fill="url(#bbGrad)"
                      dot={false}
                      isAnimationActive={false}
                    />
                    <Line
                      yAxisId="price"
                      type="monotone"
                      dataKey="bbMiddle"
                      stroke="#4a9eff"
                      strokeWidth={0.5}
                      strokeDasharray="2 4"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </>
                )}

                {/* Support / Resistance */}
                {support && (
                  <ReferenceLine
                    yAxisId="price"
                    y={support}
                    stroke="#00d68f"
                    strokeDasharray="4 4"
                    strokeWidth={0.7}
                    label={{ value: `S ${formatPrice(support)}`, position: 'insideBottomLeft', fill: '#00d68f', fontSize: 8 }}
                  />
                )}
                {resistance && (
                  <ReferenceLine
                    yAxisId="price"
                    y={resistance}
                    stroke="#ff4d6a"
                    strokeDasharray="4 4"
                    strokeWidth={0.7}
                    label={{ value: `R ${formatPrice(resistance)}`, position: 'insideTopLeft', fill: '#ff4d6a', fontSize: 8 }}
                  />
                )}

                {/* Price area */}
                <Area
                  yAxisId="price"
                  type="monotone"
                  dataKey="close"
                  stroke={accentColor}
                  strokeWidth={1.5}
                  fill="url(#priceGrad)"
                  dot={false}
                  activeDot={{ r: 3, fill: accentColor, stroke: '#0f0f14', strokeWidth: 2 }}
                />

                {/* EMA overlays */}
                {overlays.ema && (
                  <>
                    <Line yAxisId="price" type="monotone" dataKey="ema9" stroke="#ffbb33" strokeWidth={1} dot={false} isAnimationActive={false} />
                    <Line yAxisId="price" type="monotone" dataKey="ema21" stroke="#33bbff" strokeWidth={1} dot={false} isAnimationActive={false} />
                    <Line yAxisId="price" type="monotone" dataKey="ema50" stroke="#ff66aa" strokeWidth={0.8} dot={false} isAnimationActive={false} strokeDasharray="3 3" />
                  </>
                )}

                <Brush
                  dataKey="time"
                  height={20}
                  stroke="#4a9eff"
                  fill="#0f0f14"
                  tickFormatter={formatXTick}
                  startIndex={Math.max(0, chartData.length - Math.floor(chartData.length * 0.75))}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Volume bars */}
          {overlays.vol && (
            <div className="h-[36px] px-1">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 0, right: 8, left: 4, bottom: 0 }}>
                  <XAxis dataKey="time" hide />
                  <YAxis
                    yAxisId="vol"
                    width={48}
                    tickFormatter={(v) => v > 1000 ? `${(v / 1000).toFixed(0)}k` : String(Math.round(v))}
                    tick={{ fill: '#3a3a55', fontSize: 8 }}
                    axisLine={false}
                    tickLine={false}
                    domain={[0, 'auto']}
                    tickCount={2}
                  />
                  <Bar yAxisId="vol" dataKey="volume" fill="#4a9eff" opacity={0.25} radius={[1, 1, 0, 0]} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* RSI mini-chart */}
          {overlays.rsi && (
            <div className="h-[60px] px-1 border-t border-[#1e1e30]">
              <div className="absolute right-14 mt-0.5 text-[8px] text-[#aa88ff] font-semibold z-10">RSI(14)</div>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
                  <XAxis dataKey="time" hide />
                  <YAxis
                    width={48}
                    domain={[0, 100]}
                    ticks={[30, 50, 70]}
                    tick={{ fill: '#3a3a55', fontSize: 8 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <ReferenceLine y={70} stroke="#ff4d6a" strokeDasharray="2 4" strokeWidth={0.5} />
                  <ReferenceLine y={30} stroke="#00d68f" strokeDasharray="2 4" strokeWidth={0.5} />
                  <Tooltip content={<RsiTooltip />} />
                  <Line type="monotone" dataKey="rsi" stroke="#aa88ff" strokeWidth={1.2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Current indicator summary strip */}
          {indicators && (
            <div className="flex items-center justify-between px-4 py-2 border-t border-[#1e1e30] text-[9px]">
              <div className="flex items-center gap-3">
                {indicators.momentum?.rsi != null && (
                  <span className={indicators.momentum.rsi > 70 ? 'text-accent-red' : indicators.momentum.rsi < 30 ? 'text-accent-green' : 'text-text-muted'}>
                    RSI {indicators.momentum.rsi.toFixed(0)}
                  </span>
                )}
                {indicators.momentum?.macd_histogram != null && (
                  <span className={indicators.momentum.macd_histogram > 0 ? 'text-accent-green' : 'text-accent-red'}>
                    MACD {indicators.momentum.macd_histogram > 0 ? '+' : ''}{indicators.momentum.macd_histogram.toFixed(0)}
                  </span>
                )}
                {indicators.volatility?.bb_position != null && (
                  <span className="text-text-muted">
                    BB {(indicators.volatility.bb_position * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {indicators.momentum?.adx != null && (
                  <span className="text-text-muted">
                    ADX {indicators.momentum.adx.toFixed(0)}
                  </span>
                )}
                {indicators.volume?.volume_ratio != null && (
                  <span className={indicators.volume.volume_ratio > 1.5 ? 'text-accent-blue' : 'text-text-muted'}>
                    Vol {indicators.volume.volume_ratio.toFixed(1)}x
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
