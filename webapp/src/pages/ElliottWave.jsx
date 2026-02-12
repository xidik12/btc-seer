import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPrice } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'
import SubTabBar from '../components/SubTabBar'
import DataSourceFooter from '../components/DataSourceFooter'

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
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
  { key: '1h', labelKey: '1h', days: 7 },
  { key: '4h', labelKey: '4h', days: 30 },
  { key: '1d', labelKey: '1d', days: 90 },
  { key: '1w', labelKey: '1w', days: 365 },
  { key: '1mo', labelKey: '1mo', days: 730 },
]

function TimeframeSelector({ selected, onChange, t }) {
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
          {t(`market:elliott.timeframes.${tf.labelKey}`)}
        </button>
      ))}
    </div>
  )
}

function DirectionBadge({ direction, pattern, confidence, t }) {
  const isBullish = direction === 'bullish'
  const color = isBullish ? 'accent-green' : direction === 'bearish' ? 'accent-red' : 'accent-yellow'

  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs font-bold px-2 py-1 rounded border bg-${color}/10 border-${color}/30 text-${color} uppercase`}>
        {direction === 'bullish' ? t('market:elliott.directionBullish') : direction === 'bearish' ? t('market:elliott.directionBearish') : t('market:elliott.directionNeutral')}
      </span>
      <span className="text-text-muted text-[10px] capitalize">{pattern === 'impulse' ? t('market:elliott.impulse') : pattern === 'corrective' ? t('market:elliott.corrective') : pattern}</span>
      <div className="flex items-center gap-1 ml-auto">
        <span className="text-text-muted text-[9px]">{t('common:confidence')}</span>
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

function WaveStatusCard({ data, t }) {
  if (!data) return null

  const { wave_count, confidence, current_price } = data

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">{t('common:price.btcPrice').toUpperCase()}</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {current_price ? formatPrice(current_price) : '--'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">{t('market:elliott.currentWave').toUpperCase()}</div>
          <div className="text-accent-blue text-2xl font-bold">{wave_count?.current_wave || '?'}</div>
        </div>
      </div>
      <DirectionBadge
        direction={wave_count?.direction || 'neutral'}
        pattern={wave_count?.pattern || 'unknown'}
        confidence={confidence || 0}
        t={t}
      />
    </div>
  )
}

function CandlestickShape(props) {
  const { x, y, width, height, payload } = props
  if (!payload || payload.open == null || payload.price == null || !height) return null

  const isGreen = payload.price >= payload.open
  const color = isGreen ? '#00c853' : '#ff4d6a'
  const range = payload.high - payload.low
  if (range <= 0) return null

  // y = top of bar (high), y + height = bottom of bar (low)
  const openY = y + ((payload.high - payload.open) / range) * height
  const closeY = y + ((payload.high - payload.price) / range) * height
  const bodyTop = Math.min(openY, closeY)
  const bodyHeight = Math.max(Math.abs(openY - closeY), 1)
  const wickX = x + width / 2

  return (
    <g>
      <line x1={wickX} y1={y} x2={wickX} y2={y + height} stroke={color} strokeWidth={0.8} />
      <rect x={x + 0.5} y={bodyTop} width={Math.max(width - 1, 1.5)} height={bodyHeight} fill={color} />
    </g>
  )
}

function WaveChart({ historicalData, timeframe, t }) {
  if (!historicalData?.points?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-64 flex items-center justify-center">
        <span className="text-text-muted text-sm">{t('common:chart.loadingChart')}</span>
      </div>
    )
  }

  const chartData = historicalData.points.map((p) => ({
    date: p.date?.slice(0, 10),
    price: p.price,
    open: p.open,
    high: p.high,
    low: p.low,
    candleRange: p.high && p.low ? [p.low, p.high] : [0, 0],
    swingPrice: p.is_swing ? p.price : null,
    swingType: p.swing_type,
    waveLabel: p.wave_label,
  }))

  const fibLevels = historicalData.fib_levels || []

  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:elliott.title').toUpperCase()}</h3>
        {isZoomed && (
          <button onClick={resetZoom} className="text-[10px] text-accent-blue">{t('common:btn.resetZoom')}</button>
        )}
      </div>
      <div {...bindGestures}>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={visibleData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#888' }}
              tickFormatter={(v) => {
                if (!v) return ''
                if (timeframe === '1mo') return v?.slice(0, 7)
                if (timeframe === '1w') return v?.slice(2, 10)
                return v?.slice(5, 10)
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="price"
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
                if (name === 'swingPrice') return [v ? `$${v.toLocaleString()}` : '--', t('market:elliott.swing')]
                if (name === 'candleRange') return null
                if (Array.isArray(v)) return null
                return [v ? `$${v.toLocaleString()}` : '--', name]
              }}
              labelFormatter={(label) => label}
            />
            {fibLevels.slice(0, 6).map((fib, i) => (
              <ReferenceLine
                key={i}
                yAxisId="price"
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
            <Bar
              dataKey="candleRange"
              yAxisId="price"
              shape={(props) => <CandlestickShape {...props} yAxis={props.yAxis || props.background?.props?.yAxis} />}
              isAnimationActive={false}
            />
            <Line
              dataKey="price"
              yAxisId="price"
              stroke="rgba(255,193,7,0.4)"
              strokeWidth={1}
              dot={false}
              name={t('market:elliott.price')}
              connectNulls
              isAnimationActive={false}
            />
            <Scatter
              dataKey="swingPrice"
              yAxisId="price"
              fill="#4a9eff"
              name="swingPrice"
              shape={(props) => {
                if (!props.payload?.swingPrice) return null
                const label = props.payload.waveLabel
                const isHigh = props.payload.swingType === 'high'
                if (!label) {
                  return <circle cx={props.cx} cy={props.cy} r={2} fill="#4a9eff" opacity={0.6} />
                }
                const labelY = isHigh ? props.cy - 12 : props.cy + 12
                return (
                  <g>
                    <circle cx={props.cx} cy={props.cy} r={2.5} fill="#4a9eff" stroke="#fff" strokeWidth={0.8} />
                    <rect
                      x={props.cx - 8}
                      y={labelY - 6}
                      width={16}
                      height={12}
                      rx={6}
                      fill="#4a9eff"
                    />
                    <text
                      x={props.cx}
                      y={labelY + 3}
                      textAnchor="middle"
                      fill="#fff"
                      fontSize={7}
                      fontWeight="bold"
                    >
                      {label}
                    </text>
                  </g>
                )
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-2">{t('common:chart.pinchZoom')}</p>
    </div>
  )
}

function FibTargets({ targets, t }) {
  if (!targets) return null

  const { support_levels = [], resistance_levels = [] } = targets

  if (!support_levels.length && !resistance_levels.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('market:elliott.fibTargets').toUpperCase()}</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-accent-green text-[10px] font-semibold mb-2">{t('market:powerLaw.support').toUpperCase()}</div>
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
          <div className="text-accent-red text-[10px] font-semibold mb-2">{t('market:powerLaw.resistance').toUpperCase()}</div>
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

function DivergenceAlerts({ divergences, t }) {
  if (!divergences?.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('market:elliott.divergence').toUpperCase()}</h3>
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
                  {isBullish ? t('common:direction.bullish').toUpperCase() : t('common:direction.bearish').toUpperCase()}
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

function StatsGrid({ data, t }) {
  if (!data) return null

  const wc = data.wave_count || {}
  const patternMap = { impulse: t('market:elliott.impulse'), corrective: t('market:elliott.corrective') }
  const dirMap = { bullish: t('market:elliott.directionBullish'), bearish: t('market:elliott.directionBearish'), neutral: t('market:elliott.directionNeutral') }
  const stats = [
    { labelKey: 'pattern', value: patternMap[wc.pattern] || wc.pattern || '--' },
    { labelKey: 'currentWave', value: wc.current_wave || '--' },
    { labelKey: 'direction', value: dirMap[wc.direction] || wc.direction || '--' },
    { labelKey: 'confidence', value: data.confidence != null ? `${(data.confidence * 100).toFixed(0)}%` : '--' },
    { labelKey: 'divergences', value: data.divergences?.length || '0' },
    { labelKey: 'waveCount', value: wc.waves?.length || '0' },
  ]

  const labelMap = {
    pattern: t('market:elliott.pattern'),
    currentWave: t('market:elliott.currentWave'),
    direction: t('market:elliott.direction'),
    confidence: t('common:confidence'),
    divergences: t('market:elliott.divergence'),
    waveCount: t('market:elliott.waveCount'),
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {stats.map((s) => (
        <div key={s.labelKey} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{labelMap[s.labelKey]}</div>
          <div className="text-text-primary text-sm font-bold capitalize">{s.value}</div>
        </div>
      ))}
    </div>
  )
}

export default function ElliottWave() {
  const { t } = useTranslation(['market', 'common'])
  const [current, setCurrent] = useState(null)
  const [historical, setHistorical] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeframe, setTimeframe] = useState('4h')

  const MARKET_TABS = [
    { path: '/liquidations', label: t('common:link.liquidations') },
    { path: '/powerlaw', label: t('common:link.powerLaw') },
    { path: '/elliott-wave', label: t('common:link.elliottWave') },
    { path: '/events', label: t('common:link.events') },
    { path: '/tools', label: t('common:link.tools') },
    { path: '/learn', label: t('common:link.learn') },
  ]

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
      setError(err.message || t('common:widget.failedToLoad', { name: t('market:elliott.title') }))
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
        <h1 className="text-lg font-bold">{t('market:elliott.title')}</h1>
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
        <h1 className="text-lg font-bold">{t('market:elliott.title')}</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{t('common:widget.failedToLoad', { name: t('market:elliott.title') })}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">{t('common:app.retry')}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">{t('market:elliott.title')}</h1>
        <TimeframeSelector selected={timeframe} onChange={setTimeframe} t={t} />
      </div>

      <WaveStatusCard data={current} t={t} />
      <WaveChart historicalData={historical} timeframe={timeframe} t={t} />
      <FibTargets targets={current?.fibonacci_targets} t={t} />
      <DivergenceAlerts divergences={current?.divergences} t={t} />
      <StatsGrid data={current} t={t} />

      {current?.wave_count && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h3 className="text-text-secondary text-xs font-semibold mb-2">{String(t('market:elliott.waveStatus')).toUpperCase()}</h3>
          <p className="text-text-muted text-[11px] leading-relaxed">
            {(() => {
              const wc = current.wave_count
              const dir = wc.direction === 'bullish' ? t('market:elliott.directionBullish').toLowerCase() : wc.direction === 'bearish' ? t('market:elliott.directionBearish').toLowerCase() : t('market:elliott.directionNeutral').toLowerCase()
              let summary
              if (wc.pattern === 'impulse') {
                summary = t('market:elliott.summaryImpulse', { wave: wc.current_wave, direction: dir })
              } else if (wc.pattern === 'corrective') {
                summary = t('market:elliott.summaryCorrective', { wave: wc.current_wave, direction: dir })
              } else {
                summary = t('market:elliott.summaryUnclear')
              }
              if (current.divergences?.length) {
                const last = current.divergences[current.divergences.length - 1]
                const divType = last.type === 'bullish' ? t('market:elliott.directionBullish') : t('market:elliott.directionBearish')
                summary += ' ' + t('market:elliott.divergenceDetected', { type: divType, indicator: last.indicator })
              }
              return summary
            })()}
          </p>
        </div>
      )}

      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('market:elliott.title').toUpperCase()}</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>{t('market:elliott.theoryDescription')}</p>
          <p>{t('market:elliott.threeRules')}</p>
          <p>{t('market:elliott.fibRatios')}</p>
          <p>{t('market:elliott.divergenceInfo')}</p>
        </div>
      </div>

      <DataSourceFooter sources={['binance', 'coingecko', 'ta']} />
    </div>
  )
}
