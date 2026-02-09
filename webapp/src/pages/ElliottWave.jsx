import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPrice } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', label: 'Liquidations' },
  { path: '/powerlaw', label: 'Power Law' },
  { path: '/elliott-wave', label: 'Elliott Wave' },
  { path: '/events', label: 'Events' },
]

import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Scatter,
} from 'recharts'

const POLL_INTERVAL = 60_000

const TIMEFRAMES = [
  { key: '1h', label: '1H', days: 30 },
  { key: '4h', label: '4H', days: 90 },
  { key: '1d', label: '1D', days: 365 },
]

function TimeframeSelector({ selected, onChange }) {
  return (
    <div className="flex gap-1 bg-bg-card rounded-xl p-1 border border-white/5">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf.key}
          onClick={() => onChange(tf.key)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            selected === tf.key
              ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
              : 'text-text-muted hover:text-text-secondary'
          }`}
        >
          {tf.label}
        </button>
      ))}
    </div>
  )
}

function DirectionBadge({ direction, pattern, confidence }) {
  const isBullish = direction === 'bullish'
  const color = isBullish ? 'accent-green' : direction === 'bearish' ? 'accent-red' : 'accent-yellow'

  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs font-bold px-2 py-1 rounded border bg-${color}/10 border-${color}/30 text-${color} uppercase`}>
        {direction}
      </span>
      <span className="text-text-muted text-[10px] capitalize">{pattern}</span>
      <div className="flex items-center gap-1 ml-auto">
        <span className="text-text-muted text-[9px]">Confidence</span>
        <div className="w-16 h-1.5 bg-bg-hover rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full bg-${color}`}
            style={{ width: `${(confidence * 100)}%` }}
          />
        </div>
        <span className="text-text-secondary text-[10px] font-bold tabular-nums">{(confidence * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

function WaveStatusCard({ data }) {
  if (!data) return null

  const { wave_count, confidence, current_price } = data

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">CURRENT PRICE</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {current_price ? formatPrice(current_price) : '--'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">CURRENT WAVE</div>
          <div className="text-accent-blue text-2xl font-bold">{wave_count?.current_wave || '?'}</div>
        </div>
      </div>
      <DirectionBadge
        direction={wave_count?.direction || 'neutral'}
        pattern={wave_count?.pattern || 'unknown'}
        confidence={confidence || 0}
      />
    </div>
  )
}

function WaveChart({ historicalData }) {
  if (!historicalData?.points?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-64 flex items-center justify-center">
        <span className="text-text-muted text-sm">Loading chart...</span>
      </div>
    )
  }

  const chartData = historicalData.points
    .filter((_, i) => i % 2 === 0)
    .map((p) => ({
      date: p.date?.slice(0, 10),
      price: p.price,
      high: p.high,
      low: p.low,
      swingPrice: p.is_swing ? p.price : null,
      waveLabel: p.wave_label,
    }))

  const fibLevels = historicalData.fib_levels || []

  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-xs font-semibold">WAVE CHART</h3>
        {isZoomed && (
          <button onClick={resetZoom} className="text-[10px] text-accent-blue">Reset</button>
        )}
      </div>
      <div {...bindGestures}>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={visibleData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#888' }}
              tickFormatter={(v) => v?.slice(5, 10)}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 9, fill: '#888' }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                background: '#1a1a2e',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                fontSize: 11,
              }}
              formatter={(v, name) => {
                if (name === 'swingPrice') return [v ? `$${v.toLocaleString()}` : '--', 'Swing']
                return [v ? `$${v.toLocaleString()}` : '--', name]
              }}
            />
            {fibLevels.slice(0, 6).map((fib, i) => (
              <ReferenceLine
                key={i}
                y={fib.price}
                stroke={fib.type === 'support' ? '#00c853' : '#ff4d6a'}
                strokeDasharray="4 4"
                strokeWidth={0.5}
                label={{
                  value: `${fib.ratio} $${(fib.price / 1000).toFixed(1)}k`,
                  fill: fib.type === 'support' ? '#00c853' : '#ff4d6a',
                  fontSize: 8,
                  position: 'right',
                }}
              />
            ))}
            <Line
              dataKey="price"
              stroke="#ffc107"
              strokeWidth={1.5}
              dot={false}
              name="Price"
              connectNulls
            />
            <Scatter
              dataKey="swingPrice"
              fill="#4a9eff"
              r={4}
              name="swingPrice"
              shape={(props) => {
                if (!props.payload?.swingPrice) return null
                const label = props.payload.waveLabel
                return (
                  <g>
                    <circle cx={props.cx} cy={props.cy} r={4} fill="#4a9eff" stroke="#fff" strokeWidth={1} />
                    {label && (
                      <text x={props.cx} y={props.cy - 8} textAnchor="middle" fill="#4a9eff" fontSize={10} fontWeight="bold">
                        {label}
                      </text>
                    )}
                  </g>
                )
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-2">Pinch to zoom &middot; Drag to pan</p>
    </div>
  )
}

function FibTargets({ targets }) {
  if (!targets) return null

  const { support_levels = [], resistance_levels = [] } = targets

  if (!support_levels.length && !resistance_levels.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">FIBONACCI TARGETS</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-accent-green text-[10px] font-semibold mb-2">SUPPORT</div>
          <div className="space-y-1">
            {support_levels.slice(0, 5).map((lvl, i) => (
              <div key={i} className="flex items-center justify-between text-[11px]">
                <span className="text-text-muted">{lvl.ratio}</span>
                <span className="text-accent-green font-mono font-medium tabular-nums">
                  ${lvl.price?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-accent-red text-[10px] font-semibold mb-2">RESISTANCE</div>
          <div className="space-y-1">
            {resistance_levels.slice(0, 5).map((lvl, i) => (
              <div key={i} className="flex items-center justify-between text-[11px]">
                <span className="text-text-muted">{lvl.ratio}</span>
                <span className="text-accent-red font-mono font-medium tabular-nums">
                  ${lvl.price?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function DivergenceAlerts({ divergences }) {
  if (!divergences?.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">DIVERGENCE ALERTS</h3>
      <div className="space-y-2">
        {divergences.map((d, i) => {
          const isBullish = d.type === 'bullish'
          return (
            <div
              key={i}
              className={`flex items-center justify-between p-2.5 rounded-xl border ${
                isBullish ? 'bg-accent-green/5 border-accent-green/15' : 'bg-accent-red/5 border-accent-red/15'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold ${isBullish ? 'text-accent-green' : 'text-accent-red'}`}>
                  {d.type.toUpperCase()}
                </span>
                <span className="text-text-secondary text-[11px]">{d.indicator}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-12 h-1.5 bg-bg-hover rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${isBullish ? 'bg-accent-green' : 'bg-accent-red'}`}
                    style={{ width: `${d.strength * 100}%` }}
                  />
                </div>
                <span className="text-text-muted text-[10px] tabular-nums">${d.price?.toLocaleString()}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function StatsGrid({ data }) {
  if (!data) return null

  const wc = data.wave_count || {}
  const stats = [
    { label: 'Pattern', value: wc.pattern || '--' },
    { label: 'Current Wave', value: wc.current_wave || '--' },
    { label: 'Direction', value: wc.direction || '--' },
    { label: 'Confidence', value: data.confidence != null ? `${(data.confidence * 100).toFixed(0)}%` : '--' },
    { label: 'Divergences', value: data.divergences?.length || '0' },
    { label: 'Wave Count', value: wc.waves?.length || '0' },
  ]

  return (
    <div className="grid grid-cols-3 gap-2">
      {stats.map((s) => (
        <div key={s.label} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{s.label}</div>
          <div className="text-text-primary text-sm font-bold capitalize">{s.value}</div>
        </div>
      ))}
    </div>
  )
}

export default function ElliottWave() {
  const [current, setCurrent] = useState(null)
  const [historical, setHistorical] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeframe, setTimeframe] = useState('4h')

  const tfConfig = TIMEFRAMES.find((t) => t.key === timeframe) || TIMEFRAMES[1]

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const [curr, hist] = await Promise.all([
        api.getElliottWaveCurrent(timeframe),
        api.getElliottWaveHistorical(tfConfig.days, timeframe),
      ])
      setCurrent(curr)
      setHistorical(hist)
    } catch (err) {
      console.error('Elliott Wave fetch error:', err)
      setError(err.message || 'Failed to load Elliott Wave data')
    } finally {
      setLoading(false)
    }
  }, [timeframe, tfConfig.days])

  useEffect(() => {
    setLoading(true)
    fetchData()
    const interval = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Elliott Wave</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-bg-card rounded-2xl" />
          <div className="h-64 bg-bg-card rounded-2xl" />
          <div className="h-16 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  if (error && !current) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Elliott Wave</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">Failed to load data</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Elliott Wave Analysis</h1>
        <TimeframeSelector selected={timeframe} onChange={setTimeframe} />
      </div>

      <WaveStatusCard data={current} />
      <WaveChart historicalData={historical} />
      <FibTargets targets={current?.fibonacci_targets} />
      <DivergenceAlerts divergences={current?.divergences} />
      <StatsGrid data={current} />

      {current?.summary && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h3 className="text-text-secondary text-xs font-semibold mb-2">ANALYSIS SUMMARY</h3>
          <p className="text-text-muted text-[11px] leading-relaxed">{current.summary}</p>
        </div>
      )}

      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">ABOUT ELLIOTT WAVES</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            <span className="text-text-secondary font-semibold">Elliott Wave Theory</span> identifies
            recurring fractal wave patterns in market prices. Markets move in 5-wave impulses
            (with the trend) and 3-wave corrections (against the trend).
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Three inviolable rules:</span>{' '}
            (1) Wave 2 never retraces more than 100% of Wave 1.{' '}
            (2) Wave 3 is never the shortest impulse wave.{' '}
            (3) Wave 4 never enters Wave 1 price territory.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Fibonacci ratios</span> guide
            wave projections: Wave 3 often extends to 1.618x of Wave 1, Wave 4 retraces
            to 0.382x of Wave 3, and Wave 5 often equals Wave 1 in length.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Divergences</span> (price vs RSI/MACD)
            at swing points help confirm wave completions, especially at Wave 5 endings.
          </p>
        </div>
      </div>
    </div>
  )
}
