import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPrice } from '../utils/format'
import SubTabBar from '../components/SubTabBar'
import DataSourceFooter from '../components/DataSourceFooter'
import { useChartZoom } from '../hooks/useChartZoom'

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

// ── Wave label color scheme ─────────────────────────────────────────────────
const IMPULSE_RE = /^[12345]$/
const CORRECTIVE_RE = /^[ABC]$/i
function waveLabelStyle(label) {
  const raw = label?.replace(/[()[\]]/g, '') || ''
  if (IMPULSE_RE.test(raw)) return { fill: '#ffffff', stroke: '#ffffff', text: '#131722' }
  if (CORRECTIVE_RE.test(raw)) return { fill: 'transparent', stroke: '#ef5350', text: '#ef5350' }
  return { fill: 'transparent', stroke: '#f59e0b', text: '#f59e0b' }
}

function WaveChart({ historicalData, currentData, timeframe, t }) {
  const containerRef = useRef(null)
  const [svgWidth, setSvgWidth] = useState(375)

  const { data: pts, bindGestures, isZoomed, resetZoom } = useChartZoom(
    historicalData?.points || [],
    { minWindow: 10 }
  )

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setSvgWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (!pts?.length) {
    return (
      <div ref={containerRef} className="bg-[#131722] rounded-2xl h-72 flex items-center justify-center border border-white/5">
        <span className="text-[#555] text-sm">{t('common:chart.loadingChart')}</span>
      </div>
    )
  }
  const fibLevels = historicalData.fib_levels || []
  const fibTargets = currentData?.fibonacci_targets || {}
  const resistanceLvls = [...(fibTargets.resistance_levels || [])].sort((a, b) => a.price - b.price)
  const supportLvls = [...(fibTargets.support_levels || [])].sort((a, b) => a.price - b.price)

  // ── Layout ────────────────────────────────────────────────────────────────
  const W = svgWidth
  const TOTAL_H = 420
  const OSC_H = 62
  const OSC_GAP = 8
  const XAXIS_H = 18
  const MR = 68   // right margin for fib labels
  const ML = 2
  const MT = 10
  const MB = 4
  const MAIN_H = TOTAL_H - OSC_H - OSC_GAP - XAXIS_H
  const CW = W - ML - MR   // chart content width
  const CH = MAIN_H - MT - MB
  const OSC_TOP = MAIN_H + OSC_GAP
  const OSC_MID = OSC_TOP + OSC_H / 2

  // ── Price domain ──────────────────────────────────────────────────────────
  const prices = pts.flatMap(p => [p.high, p.low].filter(v => v != null && v > 0))
  if (!prices.length) return null
  const rawMin = Math.min(...prices)
  const rawMax = Math.max(...prices)
  const pad = (rawMax - rawMin) * 0.09
  const yMin = rawMin - pad
  const yMax = rawMax + pad

  const xOf = (i) => ML + (i + 0.5) * (CW / pts.length)
  const yOf = (price) => MT + CH - ((price - yMin) / (yMax - yMin)) * CH
  const cw = Math.max(1.5, (CW / pts.length) * 0.72)

  // ── Swing points with labels ──────────────────────────────────────────────
  const swings = pts.map((p, i) => ({ ...p, i })).filter(p => p.is_swing && p.wave_label)

  // ── Fibonacci target boxes ────────────────────────────────────────────────
  const boxes = []
  if (resistanceLvls.length >= 2) {
    const lo = yOf(resistanceLvls[0].price)
    const hi = yOf(resistanceLvls[resistanceLvls.length - 1].price)
    const top = Math.min(lo, hi)
    const h = Math.max(Math.abs(lo - hi), 6)
    if (top > -60 && top < MAIN_H + 60) {
      boxes.push({
        x: ML + CW * 0.58, y: top, w: CW * 0.4, h,
        fill: 'rgba(30,100,255,0.10)', stroke: 'rgba(60,140,255,0.55)',
        label: `${resistanceLvls[0].ratio}–${resistanceLvls[resistanceLvls.length - 1].ratio}`,
      })
    }
  }
  if (supportLvls.length >= 2) {
    const lo = yOf(supportLvls[0].price)
    const hi = yOf(supportLvls[Math.min(2, supportLvls.length - 1)].price)
    const top = Math.min(lo, hi)
    const h = Math.max(Math.abs(lo - hi), 6)
    if (top > -60 && top < MAIN_H + 60) {
      boxes.push({
        x: ML + CW * 0.45, y: top, w: CW * 0.53, h,
        fill: 'rgba(180,140,0,0.09)', stroke: 'rgba(200,160,0,0.50)',
        label: `${supportLvls[0].ratio}–${supportLvls[Math.min(2, supportLvls.length - 1)].ratio}`,
      })
    }
  }

  // ── Momentum oscillator ───────────────────────────────────────────────────
  const momVals = pts.map((p, i) =>
    i === 0 ? 0 : ((p.price - pts[i - 1].price) / pts[i - 1].price) * 100
  )
  const momPeak = Math.max(Math.abs(Math.min(...momVals)), Math.abs(Math.max(...momVals)), 0.01)
  const oscBar = (v) => (v / momPeak) * (OSC_H / 2 - 6)

  // ── Grid Y ticks ─────────────────────────────────────────────────────────
  const gridTicks = [0, 0.2, 0.4, 0.6, 0.8, 1.0].map(pct => ({
    y: MT + pct * CH,
    price: yMax - pct * (yMax - yMin),
  }))

  // ── Last price ───────────────────────────────────────────────────────────
  const lastPt = pts[pts.length - 1]
  const lastY = yOf(lastPt.price)

  return (
    <div
      ref={containerRef}
      className="rounded-2xl overflow-hidden border border-white/[0.06]"
      style={{ background: '#131722', ...bindGestures.style }}
      onTouchStart={bindGestures.onTouchStart}
      onTouchMove={bindGestures.onTouchMove}
      onTouchEnd={bindGestures.onTouchEnd}
      onClick={bindGestures.onClick}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.05]">
        <span className="text-[#c8c8d0] text-[11px] font-bold tracking-wide">BTC / USDT</span>
        <span className="text-[#3a3a4a] text-[9px] select-none">·</span>
        <span className="text-[#6b6b80] text-[9px] font-semibold">{timeframe.toUpperCase()}</span>
        {isZoomed ? (
          <button
            onTouchEnd={(e) => { e.stopPropagation(); resetZoom() }}
            onClick={(e) => { e.stopPropagation(); resetZoom() }}
            className="ml-auto px-2 py-0.5 rounded-full bg-accent-blue/20 text-accent-blue text-[9px] font-semibold border border-accent-blue/30"
          >
            Reset zoom
          </button>
        ) : (
          <span className="ml-auto text-[#454555] text-[9px]">{t('market:elliott.title')}</span>
        )}
      </div>

      <svg width={W} height={TOTAL_H} style={{ display: 'block' }}>
        {/* ── Grid ──────────────────────────────────────────────── */}
        {gridTicks.map((tk, i) => (
          <g key={i}>
            <line x1={ML} y1={tk.y} x2={ML + CW} y2={tk.y}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1} />
            <text x={ML + CW + 3} y={tk.y + 3} fill="#3a3a4a" fontSize={7.5} fontFamily="monospace">
              {tk.price >= 1000 ? `${(tk.price / 1000).toFixed(1)}k` : tk.price.toFixed(0)}
            </text>
          </g>
        ))}

        {/* ── Soft S/R bands from key fib levels ────────────────── */}
        {fibLevels.filter(f => f.ratio === 0.618 || f.ratio === 0.786).map((f, i) => {
          const y = yOf(f.price)
          if (y < MT - 5 || y > MAIN_H + 5) return null
          return (
            <rect key={i} x={ML} y={y - 5} width={CW} height={10}
              fill={f.type === 'support' ? 'rgba(38,166,154,0.06)' : 'rgba(239,83,80,0.06)'} />
          )
        })}

        {/* ── Fibonacci target boxes ─────────────────────────────── */}
        {boxes.map((b, i) => (
          <g key={i}>
            <rect x={b.x} y={b.y} width={b.w} height={b.h}
              fill={b.fill} stroke={b.stroke} strokeWidth={0.8} rx={1} />
          </g>
        ))}

        {/* ── Fibonacci level lines + right labels ──────────────── */}
        {fibLevels.slice(0, 8).map((fib, i) => {
          const y = yOf(fib.price)
          if (y < MT - 4 || y > MAIN_H + 4) return null
          const col = fib.type === 'support' ? '#26a69a' : '#ef5350'
          const priceLabel = fib.price >= 1000
            ? fib.price.toLocaleString('en-US', { maximumFractionDigits: 0 })
            : fib.price.toFixed(2)
          return (
            <g key={i}>
              <line x1={ML} y1={y} x2={ML + CW} y2={y}
                stroke={col} strokeWidth={0.55} strokeDasharray="3 5" opacity={0.75} />
              <text x={ML + CW + 3} y={y - 1} fill={col} fontSize={7} fontFamily="monospace" fontWeight="700">
                {fib.ratio}
              </text>
              <text x={ML + CW + 3} y={y + 8} fill={col} fontSize={6.5} fontFamily="monospace" opacity={0.8}>
                ({priceLabel})
              </text>
            </g>
          )
        })}

        {/* ── Wave connecting lines ──────────────────────────────── */}
        {swings.map((s, k) => {
          const next = swings[k + 1]
          if (!next) return null
          return (
            <line key={k}
              x1={xOf(s.i)} y1={yOf(s.price)}
              x2={xOf(next.i)} y2={yOf(next.price)}
              stroke="rgba(200,200,210,0.45)" strokeWidth={1.1} />
          )
        })}

        {/* ── Candlesticks ───────────────────────────────────────── */}
        {pts.map((p, i) => {
          if (!p.high || !p.low) return null
          const x = xOf(i)
          const green = p.price >= (p.open ?? p.price)
          const col = green ? '#26a69a' : '#ef5350'
          const wickCol = green ? '#1d7a73' : '#b03030'
          const openY = yOf(p.open ?? p.price)
          const closeY = yOf(p.price)
          const bodyTop = Math.min(openY, closeY)
          const bodyH = Math.max(Math.abs(openY - closeY), 1)
          return (
            <g key={i}>
              <line x1={x} y1={yOf(p.high)} x2={x} y2={yOf(p.low)} stroke={wickCol} strokeWidth={0.8} />
              <rect x={x - cw / 2} y={bodyTop} width={cw} height={bodyH} fill={col} />
            </g>
          )
        })}

        {/* ── Wave labels ────────────────────────────────────────── */}
        {swings.map((s, k) => {
          const x = xOf(s.i)
          const priceY = yOf(s.price)
          const isHigh = s.swing_type === 'high'
          const labelY = isHigh ? priceY - 18 : priceY + 18
          const label = s.wave_label || ''
          const raw = label.replace(/[()[\]]/g, '')
          const styled = waveLabelStyle(label)
          const isParenthesized = label.includes('(')
          return (
            <g key={k}>
              {/* dot on price */}
              <circle cx={x} cy={priceY} r={2} fill={styled.stroke} opacity={0.85} />
              {/* circle label */}
              <circle cx={x} cy={labelY} r={8}
                fill={styled.fill} stroke={styled.stroke} strokeWidth={1.3} />
              <text x={x} y={labelY + 3.5} textAnchor="middle"
                fill={isParenthesized ? styled.stroke : styled.text}
                fontSize={raw.length > 1 ? 6 : 7.5} fontWeight="bold" fontFamily="sans-serif">
                {raw}
              </text>
            </g>
          )
        })}

        {/* ── Last price tag ─────────────────────────────────────── */}
        {lastY > MT && lastY < MAIN_H && (
          <g>
            <line x1={ML} y1={lastY} x2={ML + CW} y2={lastY}
              stroke="#f59e0b" strokeWidth={0.7} strokeDasharray="2 4" opacity={0.6} />
            <rect x={ML + CW} y={lastY - 7.5} width={MR - 1} height={15} fill="#f59e0b" rx={2} />
            <text x={ML + CW + MR / 2 - 1} y={lastY + 4}
              textAnchor="middle" fill="#131722" fontSize={8.5} fontWeight="bold" fontFamily="monospace">
              {lastPt.price >= 1000
                ? lastPt.price.toLocaleString('en-US', { maximumFractionDigits: 0 })
                : lastPt.price.toFixed(2)}
            </text>
          </g>
        )}

        {/* ── X-axis date labels ─────────────────────────────────── */}
        {pts.map((p, i) => {
          const step = Math.max(1, Math.floor(pts.length / 7))
          if (i % step !== 0) return null
          const dateStr = p.date
            ? (timeframe === '1mo' ? p.date.slice(0, 7) : p.date.slice(5, 10))
            : ''
          return (
            <text key={i} x={xOf(i)} y={MAIN_H + 5}
              textAnchor="middle" fill="#3a3a52" fontSize={8} fontFamily="monospace">
              {dateStr}
            </text>
          )
        })}

        {/* ── Oscillator panel ───────────────────────────────────── */}
        <rect x={ML} y={OSC_TOP} width={CW} height={OSC_H}
          fill="rgba(255,255,255,0.015)" rx={2} />
        <line x1={ML} y1={OSC_MID} x2={ML + CW} y2={OSC_MID}
          stroke="rgba(255,255,255,0.10)" strokeWidth={0.6} />

        {momVals.map((v, i) => {
          const x = xOf(i)
          const bh = Math.max(Math.abs(oscBar(v)), 0.5)
          const by = v >= 0 ? OSC_MID - bh : OSC_MID
          return (
            <rect key={i} x={x - cw / 2} y={by} width={cw} height={bh}
              fill={v >= 0 ? '#26a69a' : '#ef5350'} opacity={0.75} />
          )
        })}

        <text x={ML + 3} y={OSC_TOP + 9} fill="#3a3a52" fontSize={7} fontFamily="monospace">
          MOMENTUM
        </text>
      </svg>
      {!isZoomed && (
        <div className="px-3 pb-2 text-[9px] text-[#3a3a52] text-center select-none">
          Pinch to zoom · Drag to pan
        </div>
      )}
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
      <WaveChart historicalData={historical} currentData={current} timeframe={timeframe} t={t} />
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
