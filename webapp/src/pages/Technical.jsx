import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPrice, formatTimeAgo } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'
import SubTabBar from '../components/SubTabBar'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

const ANALYSIS_TABS = [
  { path: '/technical', labelKey: 'link.technical' },
  { path: '/signals', labelKey: 'link.signals' },
]

const POLL_INTERVAL = 60_000

// ── Reusable components ──

function IndicatorRow({ label, value, unit, signal, description, t }) {
  if (value == null) return null
  const signalColor =
    signal === 'bullish' ? 'text-accent-green' :
    signal === 'bearish' ? 'text-accent-red' :
    signal === 'neutral' ? 'text-accent-yellow' : 'text-text-primary'

  return (
    <div className="py-2.5 border-b border-white/5 last:border-0">
      <div className="flex items-center justify-between">
        <span className="text-text-secondary text-xs">{label}</span>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold tabular-nums ${signalColor}`}>
            {typeof value === 'number' ? value.toFixed(2) : value}
          </span>
          {unit && <span className="text-text-muted text-[9px]">{unit}</span>}
          {signal && t && (
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
              signal === 'bullish' ? 'bg-accent-green/15 text-accent-green' :
              signal === 'bearish' ? 'bg-accent-red/15 text-accent-red' :
              'bg-accent-yellow/15 text-accent-yellow'
            }`}>
              {signal === 'bullish' ? t('common:signal.buy') : signal === 'bearish' ? t('common:signal.sell') : t('common:signal.hold')}
            </span>
          )}
        </div>
      </div>
      {description && (
        <p className="text-text-muted text-[10px] mt-1 leading-relaxed">{description}</p>
      )}
    </div>
  )
}

function GaugeBar({ value, min, max, zones, label, explanation }) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100))
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-text-secondary text-xs">{label}</span>
        <span className="text-text-primary text-sm font-bold tabular-nums">{value?.toFixed(1)}</span>
      </div>
      <div className="relative w-full h-3 rounded-full overflow-hidden flex">
        {zones.map((z, i) => (
          <div key={i} className={`h-full ${z.color}`} style={{ width: z.width }} />
        ))}
      </div>
      <div className="relative h-0">
        <div
          className="absolute -top-3 w-0.5 h-3 bg-white shadow-lg shadow-white/50"
          style={{ left: `${pct}%`, transform: 'translateX(-50%)' }}
        />
      </div>
      {explanation && (
        <p className="text-text-muted text-[10px] mt-2 leading-relaxed">{explanation}</p>
      )}
    </div>
  )
}

function Section({ title, color, explain, children }) {
  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className={`text-sm font-semibold mb-1 ${color || 'text-text-primary'}`}>{title}</h3>
      {explain && (
        <p className="text-text-muted text-[10px] leading-relaxed mb-3">{explain}</p>
      )}
      {children}
    </div>
  )
}

// ── Signal helpers ──

function getRsiSignal(rsi) {
  if (rsi == null) return null
  if (rsi > 70) return 'bearish'
  if (rsi < 30) return 'bullish'
  return 'neutral'
}
function getMacdSignal(hist) {
  if (hist == null) return null
  return hist > 0 ? 'bullish' : hist < 0 ? 'bearish' : 'neutral'
}
function getBbSignal(pos) {
  if (pos == null) return null
  if (pos > 0.8) return 'bearish'
  if (pos < 0.2) return 'bullish'
  return 'neutral'
}
function getMaSignal(pvm) {
  if (pvm == null) return null
  if (pvm > 1) return 'bullish'
  if (pvm < -1) return 'bearish'
  return 'neutral'
}
function getVolSignal(r) {
  if (r == null) return null
  if (r > 1.5) return 'bullish'
  if (r < 0.5) return 'bearish'
  return 'neutral'
}

// ── Dynamic explanation generators ──

function rsiExplain(rsi) {
  if (rsi == null) return ''
  if (rsi > 80) return `At ${rsi.toFixed(0)}, Bitcoin is heavily overbought. Too many people bought recently — price often drops after this. Think of it like a rubber band stretched too far.`
  if (rsi > 70) return `At ${rsi.toFixed(0)}, Bitcoin is overbought. Buyers are running out of steam. A price pullback is likely soon.`
  if (rsi > 55) return `At ${rsi.toFixed(0)}, buyers have slight control. Momentum is mildly positive — the price is leaning upward but nothing extreme.`
  if (rsi > 45) return `At ${rsi.toFixed(0)}, the market is balanced. Neither buyers nor sellers are in control — price could go either way.`
  if (rsi > 30) return `At ${rsi.toFixed(0)}, sellers have slight control. Momentum is mildly negative — the price is drifting down slowly.`
  if (rsi > 20) return `At ${rsi.toFixed(0)}, Bitcoin is oversold. Too many people sold recently — this is often a good buying opportunity.`
  return `At ${rsi.toFixed(0)}, Bitcoin is extremely oversold. Panic selling has pushed it very low — historically the price bounces back from here.`
}

function macdExplain(hist) {
  if (hist == null) return ''
  if (hist > 100) return 'Very strong upward push. Buyers are in full control and the price is rising with strong momentum.'
  if (hist > 0) return 'Positive momentum — buyers are winning. The price trend is moving upward. The bigger this number, the stronger the push.'
  if (hist > -100) return 'Negative momentum — sellers are winning. The price trend is moving downward. This suggests continued falling prices.'
  return 'Very strong downward push. Sellers are in full control and price is dropping fast.'
}

function bbExplain(pos, width) {
  if (pos == null) return ''
  let posText = ''
  if (pos > 0.8) posText = `Price is near the top of its normal range (${(pos * 100).toFixed(0)}%). Like a ball bouncing between walls — it tends to come back down.`
  else if (pos < 0.2) posText = `Price is near the bottom of its normal range (${(pos * 100).toFixed(0)}%). Like a ball that bounced off the floor — it tends to go back up.`
  else posText = `Price is in the middle of its normal range (${(pos * 100).toFixed(0)}%). No extreme position — could go either way.`

  if (width > 0.06) posText += ' Bands are wide = high volatility (big price swings expected).'
  else if (width < 0.03) posText += ' Bands are narrow = low volatility (a big move is building up, direction unknown).'
  return posText
}

// ── Indicator History Chart ──

function IndicatorHistory() {
  const { t } = useTranslation(['market', 'common'])
  const [histData, setHistData] = useState(null)
  const [histLoading, setHistLoading] = useState(true)

  useEffect(() => {
    api.getIndicatorHistory()
      .then(d => setHistData(d))
      .catch(() => {})
      .finally(() => setHistLoading(false))
  }, [])

  if (histLoading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-5 w-40 bg-bg-hover rounded mb-4" />
        <div className="h-[180px] bg-bg-hover rounded" />
      </div>
    )
  }

  const points = histData?.history || histData?.points || []
  if (!points.length) return null

  const chartData = points.map(p => ({
    time: p.timestamp || p.time,
    rsi: p.rsi,
    macd: p.macd_histogram || p.macd,
  }))

  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <Section
      title={t('market:technical.indicatorHistory.title')}
      color="text-accent-blue"
      explain={t('market:technical.indicatorHistory.explain')}
    >
      {isZoomed && (
        <button onClick={resetZoom} className="text-[10px] text-accent-blue mb-2">{t('market:technical.indicatorHistory.resetZoom')}</button>
      )}
      <div className="h-[200px]" {...bindGestures}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visibleData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 6" stroke="#1e1e30" vertical={false} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              tickFormatter={(v) => v?.slice(11, 16) || v?.slice(5, 10) || ''}
              axisLine={false}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              yAxisId="rsi"
              domain={[0, 100]}
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis yAxisId="macd" orientation="right" hide />
            <Tooltip
              contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              formatter={(v, name) => [v?.toFixed(2), name === 'rsi' ? 'RSI' : 'MACD']}
              labelFormatter={(v) => v}
            />
            <Area
              yAxisId="rsi"
              type="monotone"
              dataKey="rsi"
              stroke="#4a9eff"
              strokeWidth={1.5}
              fill="rgba(74, 158, 255, 0.1)"
              dot={false}
              name="rsi"
            />
            <Line
              yAxisId="macd"
              type="monotone"
              dataKey="macd"
              stroke="#a78bfa"
              strokeWidth={1}
              dot={false}
              name="macd"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-center gap-4 mt-2 text-[9px]">
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-accent-blue inline-block rounded" /> RSI
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-accent-purple inline-block rounded" /> MACD
        </span>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-1">{t('common:chart.pinchZoom')}</p>
    </Section>
  )
}

// ── Main Component ──

export default function Technical() {
  const { t } = useTranslation(['market', 'common'])
  const tabs = useMemo(() => ANALYSIS_TABS.map(tab => ({ ...tab, label: t(tab.labelKey, { ns: 'common' }) })), [t])
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getIndicators()
      if (res?.error) { setError(res.error) } else { setData(res); setError(null) }
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('technical.title')}</h1>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
            <div className="h-5 w-40 bg-bg-hover rounded mb-4" />
            <div className="space-y-3">
              <div className="h-4 w-full bg-bg-hover rounded" />
              <div className="h-4 w-3/4 bg-bg-hover rounded" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4">
        <h1 className="text-lg font-bold mb-4">{t('technical.title')}</h1>
        <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
          <p className="text-accent-red text-sm">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs mt-1 underline">{t('app.retry', { ns: 'common' })}</button>
        </div>
      </div>
    )
  }

  const ma = data?.moving_averages || {}
  const mom = data?.momentum || {}
  const vol = data?.volatility || {}
  const volume = data?.volume || {}
  const levels = data?.levels || {}
  const adv = data?.advanced || {}
  const candle = data?.candle || {}
  const stochRsi = data?.stochastic_rsi || {}
  const williamsR = data?.williams_r
  const ichimoku = data?.ichimoku || {}
  const patterns = data?.candlestick_patterns || {}
  const trend = data?.trend || {}
  const btcDom = data?.btc_dominance || {}
  const price = data?.current_price

  // Count signals
  const signals = [
    getRsiSignal(mom.rsi),
    getMacdSignal(mom.macd_histogram),
    getBbSignal(vol.bb_position),
    getMaSignal(adv.price_vs_ema9),
    getMaSignal(adv.price_vs_ema21),
    getMaSignal(adv.price_vs_ema50),
    getVolSignal(volume.volume_ratio),
    stochRsi.k > 80 ? 'bearish' : stochRsi.k < 20 ? 'bullish' : stochRsi.k != null ? 'neutral' : null,
    williamsR < -80 ? 'bullish' : williamsR > -20 ? 'bearish' : williamsR != null ? 'neutral' : null,
    price && ichimoku.senkou_a != null && ichimoku.senkou_b != null
      ? (price > Math.max(ichimoku.senkou_a, ichimoku.senkou_b) ? 'bullish'
         : price < Math.min(ichimoku.senkou_a, ichimoku.senkou_b) ? 'bearish' : 'neutral')
      : null,
    trend.short_term === 1 ? 'bullish' : trend.short_term === -1 ? 'bearish' : trend.short_term != null ? 'neutral' : null,
    trend.medium_term === 1 ? 'bullish' : trend.medium_term === -1 ? 'bearish' : trend.medium_term != null ? 'neutral' : null,
  ].filter(Boolean)

  const bullCount = signals.filter(s => s === 'bullish').length
  const bearCount = signals.filter(s => s === 'bearish').length
  const neutralCount = signals.length - bullCount - bearCount
  const overall = bullCount > bearCount ? 'bullish' : bearCount > bullCount ? 'bearish' : 'neutral'
  const overallLabel = overall === 'bullish' ? t('direction.bullish', { ns: 'common' }) : overall === 'bearish' ? t('direction.bearish', { ns: 'common' }) : t('direction.neutral', { ns: 'common' })
  const overallColor = overall === 'bullish' ? 'text-accent-green' : overall === 'bearish' ? 'text-accent-red' : 'text-accent-yellow'
  const overallBg = overall === 'bullish' ? 'bg-accent-green/15 border-accent-green/30' : overall === 'bearish' ? 'bg-accent-red/15 border-accent-red/30' : 'bg-accent-yellow/15 border-accent-yellow/30'

  const overallExplain = overall === 'bullish'
    ? t('technical.overallBullish', { count: bullCount, total: signals.length })
    : overall === 'bearish'
    ? t('technical.overallBearish', { count: bearCount, total: signals.length })
    : t('technical.overallNeutral', { bull: bullCount, bear: bearCount, neutral: neutralCount })

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <SubTabBar tabs={tabs} />
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">{t('technical.title')}</h1>
        {data?.timestamp && (
          <span className="text-text-muted text-[10px]">{formatTimeAgo(data.timestamp)}</span>
        )}
      </div>

      {/* ── Overall Summary ── */}
      <div className={`rounded-2xl p-4 border ${overallBg}`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-text-secondary text-xs">{t('technical.overallSignal')}</span>
          <span className={`text-lg font-bold ${overallColor}`}>{overallLabel}</span>
        </div>
        <div className="flex items-center gap-3 text-xs mb-2">
          <span className="text-accent-green">{t('technical.buyCount', { count: bullCount })}</span>
          <span className="text-text-muted">/</span>
          <span className="text-accent-red">{t('technical.sellCount', { count: bearCount })}</span>
          <span className="text-text-muted">/</span>
          <span className="text-accent-yellow">{t('technical.neutralCount', { count: neutralCount })}</span>
          <span className="text-text-muted ml-auto">{t('technical.ofTotal', { total: signals.length })}</span>
        </div>
        <p className="text-text-muted text-[10px] leading-relaxed">{overallExplain}</p>
        {price && (
          <div className="mt-2 pt-2 border-t border-white/10">
            <span className="text-text-muted text-xs">{t('technical.btcPrice')}: </span>
            <span className="text-text-primary text-sm font-bold">{formatPricePrecise(price)}</span>
          </div>
        )}
      </div>

      {/* ── Trend Direction ── */}
      <Section
        title={t('technical.trend.title')}
        color="text-accent-blue"
        explain={t('technical.trend.explain')}
      >
        {[
          { label: t('technical.trend.shortTerm'), val: trend.short_term, what: t('technical.trend.whatShort') },
          { label: t('technical.trend.mediumTerm'), val: trend.medium_term, what: t('technical.trend.whatMedium') },
          { label: t('technical.trend.longTerm'), val: trend.long_term, what: t('technical.trend.whatLong') },
        ].map(({ label, val, what }) => {
          const trendLabel = val === 1 ? t('technical.trend.ascending') : val === -1 ? t('technical.trend.descending') : t('technical.trend.sideways')
          const sig = val === 1 ? 'bullish' : val === -1 ? 'bearish' : 'neutral'
          const desc = val === 1
            ? t('technical.trend.ascendingDesc', { what })
            : val === -1
            ? t('technical.trend.descendingDesc', { what })
            : t('technical.trend.sidewaysDesc', { what })
          return <IndicatorRow key={label} label={label} value={trendLabel} signal={sig} description={desc} t={t} />
        })}
      </Section>

      {/* ── RSI ── */}
      <Section
        title={t('technical.rsi.title')}
        color="text-accent-blue"
        explain={t('technical.rsi.explain')}
      >
        <GaugeBar
          value={mom.rsi}
          min={0}
          max={100}
          label={t('technical.rsi.standard')}
          zones={[
            { color: 'bg-accent-green/40', width: '30%' },
            { color: 'bg-accent-yellow/30', width: '40%' },
            { color: 'bg-accent-red/40', width: '30%' },
          ]}
          explanation={rsiExplain(mom.rsi)}
        />
        <div className="flex justify-between text-[9px] text-text-muted -mt-1 mb-2">
          <span>{t('technical.rsi.oversold')}</span>
          <span>{t('technical.rsi.neutral')}</span>
          <span>{t('technical.rsi.overbought')}</span>
        </div>
        <IndicatorRow label={t('technical.rsi.fast')} value={mom.rsi_7} signal={getRsiSignal(mom.rsi_7)} t={t}
          description={mom.rsi_7 != null ? `Looks at the last 7 hours only. Quick reactions — ${mom.rsi_7 > 70 ? 'showing overbought, short-term drop likely' : mom.rsi_7 < 30 ? 'showing oversold, short-term bounce likely' : 'nothing extreme right now'}.` : null}
        />
        <IndicatorRow label={t('technical.rsi.standard')} value={mom.rsi} signal={getRsiSignal(mom.rsi)} t={t}
          description={t('technical.rsi.standardDesc')}
        />
        <IndicatorRow label={t('technical.rsi.slow')} value={mom.rsi_30} signal={getRsiSignal(mom.rsi_30)} t={t}
          description={mom.rsi_30 != null ? `Looks at the last 30 hours. Slower to react but more reliable — ${mom.rsi_30 > 70 ? 'even the slow RSI says overbought, strong sell signal' : mom.rsi_30 < 30 ? 'even the slow RSI says oversold, strong buy signal' : 'no extreme reading'}.` : null}
        />
      </Section>

      {/* ── MACD ── */}
      <Section
        title={t('technical.macd.title')}
        color="text-accent-purple"
        explain={t('technical.macd.explain')}
      >
        <IndicatorRow label={t('technical.macd.line')} value={mom.macd} signal={getMacdSignal(mom.macd)} t={t}
          description={mom.macd != null ? (mom.macd > 0 ? 'Positive — the fast average is above the slow average, meaning recent price action is stronger than the longer trend. Bullish.' : 'Negative — the fast average is below the slow average, meaning recent price action is weaker than the longer trend. Bearish.') : null}
        />
        <IndicatorRow label={t('technical.macd.signal')} value={mom.macd_signal} t={t}
          description={t('technical.macd.signalDesc')}
        />
        <IndicatorRow label={t('technical.macd.histogram')} value={mom.macd_histogram} signal={getMacdSignal(mom.macd_histogram)} t={t}
          description={macdExplain(mom.macd_histogram)}
        />
      </Section>

      {/* ── Moving Averages ── */}
      <Section
        title={t('technical.movingAverages.title')}
        color="text-accent-blue"
        explain={t('technical.movingAverages.explain')}
      >
        {[
          { label: 'EMA 9', val: ma.ema_9, desc: 'Average price over last 9 hours. Very fast — shows what happened today.' },
          { label: 'EMA 21', val: ma.ema_21, desc: 'Average price over last 21 hours (~1 day). Good for short-term trends.' },
          { label: 'SMA 20', val: ma.sma_20, desc: 'Simple average of last 20 hours. A common benchmark traders watch closely.' },
          { label: 'EMA 50', val: ma.ema_50, desc: 'Average price over last 50 hours (~2 days). Medium-term trend direction.' },
          { label: 'SMA 111', val: ma.sma_111, desc: 'Average price over ~5 days. Used in the Pi Cycle indicator to spot major tops.' },
          { label: 'EMA 200', val: ma.ema_200, desc: 'Average over ~8 days. THE most important line in trading — price above = bull market, below = bear market.' },
          { label: 'SMA 200', val: ma.sma_200, desc: 'The "golden line". If BTC is above this, the long-term trend is healthy.' },
          { label: 'SMA 350', val: ma.sma_350, desc: 'Average over ~15 days. Part of the Pi Cycle Top indicator for spotting market tops.' },
        ].map(({ label, val, desc }) => {
          const aboveBelow = price && val ? (price > val
            ? `Price is $${Math.abs(price - val).toFixed(0)} ABOVE this average — bullish.`
            : `Price is $${Math.abs(price - val).toFixed(0)} BELOW this average — bearish.`)
            : ''
          return (
            <IndicatorRow
              key={label}
              label={label}
              value={val ? formatPricePrecise(val) : null}
              signal={price && val ? (price > val ? 'bullish' : 'bearish') : null}
              description={`${desc} ${aboveBelow}`}
            />
          )
        })}
      </Section>

      {/* ── Bollinger Bands ── */}
      <Section
        title={t('technical.bollinger.title')}
        color="text-accent-yellow"
        explain={t('technical.bollinger.explain')}
      >
        <IndicatorRow label={t('technical.bollinger.upper')} value={vol.bb_upper ? formatPricePrecise(vol.bb_upper) : null} t={t}
          description="The upper limit of normal price range. If price touches this, it may be overextended."
        />
        <IndicatorRow label={t('technical.bollinger.middle')} value={vol.bb_middle ? formatPricePrecise(vol.bb_middle) : null} t={t}
          description="The 20-period average price. Think of this as the 'fair value' center."
        />
        <IndicatorRow label={t('technical.bollinger.lower')} value={vol.bb_lower ? formatPricePrecise(vol.bb_lower) : null} t={t}
          description="The lower limit of normal price range. If price touches this, it may be a bargain."
        />
        <IndicatorRow label={t('technical.bollinger.width')} value={vol.bb_width} t={t}
          description={vol.bb_width > 0.06 ? 'Bands are WIDE — high volatility. Price is making big moves. Expect continued swings.' : vol.bb_width < 0.03 ? 'Bands are NARROW (squeeze) — low volatility. A big price explosion is likely coming soon, but direction is unknown.' : 'Bands are normal width. Moderate volatility — nothing extreme.'}
        />
        <GaugeBar
          value={(vol.bb_position || 0) * 100}
          min={0}
          max={100}
          label={t('technical.bollinger.position')}
          zones={[
            { color: 'bg-accent-green/40', width: '20%' },
            { color: 'bg-accent-yellow/30', width: '60%' },
            { color: 'bg-accent-red/40', width: '20%' },
          ]}
          explanation={bbExplain(vol.bb_position, vol.bb_width)}
        />
        <div className="flex justify-between text-[9px] text-text-muted -mt-1">
          <span>{t('technical.bollinger.nearFloor')}</span>
          <span>{t('technical.bollinger.middleFair')}</span>
          <span>{t('technical.bollinger.nearCeiling')}</span>
        </div>
      </Section>

      {/* ── Volume ── */}
      <Section
        title={t('technical.volume.title')}
        color="text-accent-green"
        explain={t('technical.volume.explain')}
      >
        <IndicatorRow label={t('technical.volume.ratio')} value={volume.volume_ratio} signal={getVolSignal(volume.volume_ratio)} t={t}
          description={
            volume.volume_ratio > 2 ? `Trading volume is ${volume.volume_ratio.toFixed(1)}x the average — VERY high activity. Whatever direction the price is moving, lots of people agree. This move has strong conviction.`
            : volume.volume_ratio > 1.5 ? `Trading volume is ${volume.volume_ratio.toFixed(1)}x the average — above normal. More people are trading than usual, which gives the current price move more credibility.`
            : volume.volume_ratio > 0.8 ? `Trading volume is ${volume.volume_ratio.toFixed(1)}x the average — normal. Nothing unusual happening in terms of trading activity.`
            : volume.volume_ratio > 0.5 ? `Trading volume is ${volume.volume_ratio.toFixed(1)}x the average — below normal. Fewer people are trading. Price moves right now are less trustworthy.`
            : `Trading volume is very low at ${volume.volume_ratio?.toFixed(1)}x average. Almost nobody is trading. Any price move right now is unreliable and can easily reverse.`
          }
        />
        <IndicatorRow label={t('technical.volume.vwap')} value={volume.vwap ? formatPricePrecise(volume.vwap) : null} t={t}
          signal={price && volume.vwap ? (price > volume.vwap ? 'bullish' : 'bearish') : null}
          description={price && volume.vwap ? (price > volume.vwap
            ? 'Price is ABOVE VWAP — means the average buyer today is in profit. Bullish. Traders see this as a sign of strength.'
            : 'Price is BELOW VWAP — means the average buyer today is at a loss. Bearish. Traders see this as weakness.') : 'The average price weighted by volume — shows where the "true" average trading price is.'}
        />
        <IndicatorRow label={t('technical.volume.obv')} value={volume.obv ? (volume.obv / 1e6).toFixed(1) : null} unit="M" t={t}
          description="Running total of volume: adds volume on up days, subtracts on down days. If OBV is rising, smart money is accumulating (buying). If falling, they're distributing (selling)."
        />
      </Section>

      {/* ── Support & Resistance ── */}
      <Section
        title={t('technical.supportResistance.title')}
        color="text-accent-red"
        explain={t('technical.supportResistance.explain')}
      >
        <IndicatorRow label={t('technical.supportResistance.resistance')} value={levels.resistance_1 ? formatPricePrecise(levels.resistance_1) : null} t={t}
          description={levels.resistance_1 && price ? `Bitcoin may struggle to go above ${formatPrice(levels.resistance_1)}. If it breaks through, that's very bullish — the next move up could be strong. Price is ${price < levels.resistance_1 ? `$${(levels.resistance_1 - price).toFixed(0)} away from this ceiling` : 'already above this level — bullish breakout'}.` : 'The estimated price ceiling based on recent highs and lows.'}
        />
        <IndicatorRow label={t('technical.supportResistance.pivot')} value={levels.pivot ? formatPricePrecise(levels.pivot) : null} t={t}
          description="The balance point calculated from yesterday's high, low, and close. Above pivot = bullish day, below = bearish day. Traders use this to judge the overall mood."
        />
        <IndicatorRow label={t('technical.supportResistance.support')} value={levels.support_1 ? formatPricePrecise(levels.support_1) : null} t={t}
          description={levels.support_1 && price ? `Bitcoin should find buyers around ${formatPrice(levels.support_1)}. If it breaks below, that's bearish — more selling could follow. Price is ${price > levels.support_1 ? `$${(price - levels.support_1).toFixed(0)} above this floor` : 'dangerously close to or below this support'}.` : 'The estimated price floor based on recent highs and lows.'}
        />
      </Section>

      {/* ── Trend Strength (ADX) ── */}
      <Section
        title={t('technical.trendStrength.title')}
        color="text-accent-purple"
        explain={t('technical.trendStrength.explain')}
      >
        <GaugeBar
          value={mom.adx || 0}
          min={0}
          max={75}
          label={t('technical.trendStrength.adx')}
          zones={[
            { color: 'bg-text-muted/30', width: '27%' },
            { color: 'bg-accent-yellow/40', width: '33%' },
            { color: 'bg-accent-green/40', width: '40%' },
          ]}
          explanation={
            mom.adx > 50 ? `ADX is ${mom.adx?.toFixed(0)} — very strong trend. Whatever direction BTC is going, it's moving there with conviction. Don't fight this trend.`
            : mom.adx > 25 ? `ADX is ${mom.adx?.toFixed(0)} — a clear trend exists. The price is consistently moving in one direction. This is a good time for trend-following strategies.`
            : mom.adx > 20 ? `ADX is ${mom.adx?.toFixed(0)} — borderline. A trend might be forming but it's not confirmed yet. Wait for it to go above 25 for more certainty.`
            : `ADX is ${mom.adx?.toFixed(0)} — no clear trend. The market is choppy and directionless. Price is bouncing randomly. Not a great time to trade trends.`
          }
        />
        <div className="flex justify-between text-[9px] text-text-muted -mt-1 mb-2">
          <span>{t('technical.trendStrength.noTrend')}</span>
          <span>{t('technical.trendStrength.moderateTrend')}</span>
          <span>{t('technical.trendStrength.strongTrend')}</span>
        </div>
        <IndicatorRow label={t('technical.trendStrength.atr')} value={vol.atr} t={t}
          description={vol.atr ? `Bitcoin's average price swing is $${vol.atr.toFixed(0)} per hour. This tells you how much the price typically moves — useful for setting stop-losses. Bigger = more volatile.` : null}
        />
        <IndicatorRow label={t('technical.trendStrength.volatility24h')} value={vol.volatility_24h} unit="%" t={t}
          description={vol.volatility_24h > 3 ? 'HIGH volatility — price is swinging wildly. Bigger potential profits but also bigger risks. Be extra careful with positions.' : vol.volatility_24h > 1.5 ? 'MODERATE volatility — normal market conditions. Reasonable price swings.' : 'LOW volatility — very calm market. Small price movements. A breakout might be approaching.'}
        />
      </Section>

      {/* ── BTC Dominance ── */}
      {btcDom.btc_dominance != null && (
        <Section
          title={t('technical.btcDominance.title')}
          color="text-accent-yellow"
          explain={t('technical.btcDominance.explain')}
        >
          <GaugeBar
            value={btcDom.btc_dominance || 0}
            min={30}
            max={70}
            label={t('technical.btcDominance.marketShare')}
            zones={[
              { color: 'bg-accent-red/40', width: '30%' },
              { color: 'bg-accent-yellow/30', width: '40%' },
              { color: 'bg-accent-green/40', width: '30%' },
            ]}
            explanation={
              btcDom.btc_dominance > 55 ? `At ${btcDom.btc_dominance.toFixed(1)}%, Bitcoin dominates the crypto market. Money is flowing into BTC — this usually means people are playing it safe. Bullish for Bitcoin specifically.`
              : btcDom.btc_dominance > 45 ? `At ${btcDom.btc_dominance.toFixed(1)}%, Bitcoin has a moderate market share. Neither extreme — normal conditions.`
              : `At ${btcDom.btc_dominance.toFixed(1)}%, Bitcoin's share is low. Money is flowing into altcoins — this is called "altcoin season". Can mean traders are more risk-hungry.`
            }
          />
          <div className="flex justify-between text-[9px] text-text-muted -mt-1 mb-2">
            <span>{t('technical.btcDominance.altcoinSeason')}</span>
            <span>{t('technical.btcDominance.normal')}</span>
            <span>{t('technical.btcDominance.btcSeason')}</span>
          </div>
          {btcDom.eth_dominance != null && (
            <IndicatorRow label={t('technical.btcDominance.ethDominance')} value={btcDom.eth_dominance} unit="%" t={t}
              description="Ethereum's share of the crypto market. When ETH dominance rises, it often signals growing interest in DeFi and altcoins."
            />
          )}
          {btcDom.market_cap_change_24h != null && (
            <IndicatorRow label={t('technical.btcDominance.totalMarket24h')} value={btcDom.market_cap_change_24h} unit="%" t={t}
              signal={btcDom.market_cap_change_24h > 0 ? 'bullish' : 'bearish'}
              description={btcDom.market_cap_change_24h > 0 ? 'The entire crypto market grew in the last 24 hours — money is coming into crypto overall.' : 'The entire crypto market shrank — money is leaving crypto. Even strong coins can fall in this environment.'}
            />
          )}
        </Section>
      )}

      {/* ── Stochastic RSI ── */}
      <Section
        title={t('technical.stochRsi.title')}
        color="text-accent-purple"
        explain={t('technical.stochRsi.explain')}
      >
        <GaugeBar
          value={stochRsi.k || 0}
          min={0}
          max={100}
          label={t('technical.stochRsi.kFast')}
          zones={[
            { color: 'bg-accent-green/40', width: '20%' },
            { color: 'bg-accent-yellow/30', width: '60%' },
            { color: 'bg-accent-red/40', width: '20%' },
          ]}
          explanation={
            stochRsi.k > 80 ? `At ${stochRsi.k?.toFixed(0)}, Bitcoin is extremely overbought in the short term. This indicator reacts fast — a quick pullback is very likely. Short-term traders would sell here.`
            : stochRsi.k < 20 ? `At ${stochRsi.k?.toFixed(0)}, Bitcoin is extremely oversold in the short term. This often marks a local bottom. Short-term traders would look to buy here.`
            : `At ${stochRsi.k?.toFixed(0)}, no extreme reading. The short-term momentum is neutral — wait for it to reach the zones above 80 or below 20 for clearer signals.`
          }
        />
        <div className="flex justify-between text-[9px] text-text-muted -mt-1 mb-2">
          <span>{t('technical.stochRsi.buyZone')}</span>
          <span>{t('technical.stochRsi.neutral')}</span>
          <span>{t('technical.stochRsi.sellZone')}</span>
        </div>
        <IndicatorRow label={t('technical.stochRsi.kFast')} value={stochRsi.k} t={t}
          signal={stochRsi.k > 80 ? 'bearish' : stochRsi.k < 20 ? 'bullish' : 'neutral'}
          description="The fast-reacting line. When it enters extreme zones (above 80 or below 20), pay attention."
        />
        <IndicatorRow label={t('technical.stochRsi.dSlow')} value={stochRsi.d} t={t}
          signal={stochRsi.k > stochRsi.d ? 'bullish' : 'bearish'}
          description={stochRsi.k > stochRsi.d ? 'The fast line (%K) is ABOVE the slow line (%D) — this is a buy signal. Momentum is shifting upward.' : 'The fast line (%K) is BELOW the slow line (%D) — this is a sell signal. Momentum is shifting downward.'}
        />
      </Section>

      {/* ── Williams %R ── */}
      <Section
        title={t('technical.williamsR.title')}
        color="text-accent-red"
        explain={t('technical.williamsR.explain')}
      >
        <GaugeBar
          value={williamsR != null ? williamsR + 100 : 50}
          min={0}
          max={100}
          label="Williams %R"
          zones={[
            { color: 'bg-accent-green/40', width: '20%' },
            { color: 'bg-accent-yellow/30', width: '60%' },
            { color: 'bg-accent-red/40', width: '20%' },
          ]}
          explanation={
            williamsR < -80 ? `At ${williamsR?.toFixed(0)}, the price is near its recent LOWEST point. Historically, this is where bounces happen. Think of it as a sale — Bitcoin is trading at the bottom of its recent range.`
            : williamsR > -20 ? `At ${williamsR?.toFixed(0)}, the price is near its recent HIGHEST point. It may struggle to go higher and could pull back. Think of it as Bitcoin being "expensive" relative to recent prices.`
            : `At ${williamsR?.toFixed(0)}, the price is in the middle of its recent range. Neither cheap nor expensive right now.`
          }
        />
        <div className="flex justify-between text-[9px] text-text-muted -mt-1">
          <span>{t('technical.williamsR.nearLows')}</span>
          <span>{t('technical.williamsR.midRange')}</span>
          <span>{t('technical.williamsR.nearHighs')}</span>
        </div>
      </Section>

      {/* ── Ichimoku Cloud ── */}
      <Section
        title={t('technical.ichimoku.title')}
        color="text-accent-green"
        explain={t('technical.ichimoku.explain')}
      >
        <IndicatorRow label={t('technical.ichimoku.tenkan')} value={ichimoku.tenkan ? formatPricePrecise(ichimoku.tenkan) : null} t={t}
          signal={price && ichimoku.tenkan ? (price > ichimoku.tenkan ? 'bullish' : 'bearish') : null}
          description={price && ichimoku.tenkan ? (price > ichimoku.tenkan
            ? 'Price is above the conversion line — short-term momentum is up. Like having the wind at your back.'
            : 'Price is below the conversion line — short-term momentum is down. Buyers are struggling.') : 'The short-term trend line (average of 9-period high and low).'}
        />
        <IndicatorRow label={t('technical.ichimoku.kijun')} value={ichimoku.kijun ? formatPricePrecise(ichimoku.kijun) : null} t={t}
          signal={price && ichimoku.kijun ? (price > ichimoku.kijun ? 'bullish' : 'bearish') : null}
          description={price && ichimoku.kijun ? (price > ichimoku.kijun
            ? 'Price is above the base line — medium-term trend is bullish. This is the more important of the two lines.'
            : 'Price is below the base line — medium-term trend is bearish. This is a stronger bearish signal than being below Tenkan.') : 'The medium-term trend line (average of 26-period high and low).'}
        />
        <IndicatorRow label={t('technical.ichimoku.cloudTop')} value={ichimoku.senkou_a ? formatPricePrecise(ichimoku.senkou_a) : null} t={t}
          description="The top edge of the cloud. Acts as support when price is above the cloud, or resistance when below."
        />
        <IndicatorRow label={t('technical.ichimoku.cloudBottom')} value={ichimoku.senkou_b ? formatPricePrecise(ichimoku.senkou_b) : null} t={t}
          description="The bottom edge of the cloud. This is the stronger support/resistance level."
        />
        {ichimoku.senkou_a != null && ichimoku.senkou_b != null && (
          <div className={`mt-2 px-3 py-2 rounded-lg border text-xs font-medium ${
            price > Math.max(ichimoku.senkou_a, ichimoku.senkou_b)
              ? 'bg-accent-green/10 border-accent-green/20 text-accent-green'
              : price < Math.min(ichimoku.senkou_a, ichimoku.senkou_b)
              ? 'bg-accent-red/10 border-accent-red/20 text-accent-red'
              : 'bg-accent-yellow/10 border-accent-yellow/20 text-accent-yellow'
          }`}>
            {price > Math.max(ichimoku.senkou_a, ichimoku.senkou_b)
              ? t('technical.ichimoku.aboveCloud')
              : price < Math.min(ichimoku.senkou_a, ichimoku.senkou_b)
              ? t('technical.ichimoku.belowCloud')
              : t('technical.ichimoku.insideCloud')}
          </div>
        )}
      </Section>

      {/* ── Candlestick Patterns ── */}
      <Section
        title={t('technical.candlestick.title')}
        color="text-accent-yellow"
        explain={t('technical.candlestick.explain')}
      >
        {(() => {
          const active = []
          if (patterns.doji) active.push({ name: 'Doji', signal: 'neutral', desc: 'The candle opened and closed at almost the same price. This means INDECISION — buyers and sellers are equally matched. Often appears right before a reversal.' })
          if (patterns.hammer) active.push({ name: 'Hammer', signal: 'bullish', desc: 'Price dropped significantly but buyers pushed it back up. Shaped like a hammer. This is a BULLISH reversal signal — sellers tried to push price down but failed.' })
          if (patterns.inverted_hammer) active.push({ name: 'Inverted Hammer', signal: 'bullish', desc: 'Price rose significantly but sellers pushed it back down, then buyers recovered some. Can signal a BOTTOM is forming — next candle confirms.' })
          if (patterns.bullish_engulfing) active.push({ name: 'Bullish Engulfing', signal: 'bullish', desc: 'Today\'s green candle completely "swallowed" yesterday\'s red candle. This is a STRONG BUY signal — buyers have completely overwhelmed sellers.' })
          if (patterns.bearish_engulfing) active.push({ name: 'Bearish Engulfing', signal: 'bearish', desc: 'Today\'s red candle completely "swallowed" yesterday\'s green candle. This is a STRONG SELL signal — sellers have completely overwhelmed buyers.' })
          if (patterns.morning_star) active.push({ name: 'Morning Star', signal: 'bullish', desc: 'A 3-candle pattern: big red candle, tiny candle (indecision), then big green candle. Like dawn after a dark night — signals the downtrend is ENDING and price will rise.' })
          if (patterns.evening_star) active.push({ name: 'Evening Star', signal: 'bearish', desc: 'A 3-candle pattern: big green candle, tiny candle, then big red candle. Like sunset — signals the uptrend is ENDING and price will fall.' })

          if (active.length === 0) {
            return <p className="text-text-muted text-xs">{t('technical.candlestick.noPatterns')}</p>
          }
          return active.map((p) => (
            <IndicatorRow key={p.name} label={p.name} value={t('technical.candlestick.detected')} signal={p.signal} description={p.desc} t={t} />
          ))
        })()}
        <div className="mt-2 pt-2 border-t border-white/5">
          <IndicatorRow label={t('technical.candlestick.bodySize')} value={candle.body_size} unit="%" t={t}
            description={candle.body_size > 1 ? 'Large body — strong conviction in the direction. Buyers or sellers clearly won this candle.' : candle.body_size > 0.3 ? 'Medium body — moderate move. Neither side dominated strongly.' : 'Tiny body — almost no difference between open and close. The market is undecided.'}
          />
          <IndicatorRow label={t('technical.candlestick.upperShadow')} value={candle.upper_shadow} unit="%" t={t}
            description={candle.upper_shadow > 0.5 ? 'Long upper shadow — sellers pushed the price down from the high. There\'s selling pressure above current price.' : 'Short upper shadow — not much selling pressure above. Buyers stayed in control.'}
          />
          <IndicatorRow label={t('technical.candlestick.lowerShadow')} value={candle.lower_shadow} unit="%" t={t}
            description={candle.lower_shadow > 0.5 ? 'Long lower shadow — buyers pushed the price up from the low. There are buyers waiting below, providing support.' : 'Short lower shadow — price didn\'t dip much. No significant buying interest at lower prices.'}
          />
        </div>
      </Section>

      {/* ── Advanced Metrics ── */}
      <Section
        title={t('technical.advanced.title')}
        color="text-accent-blue"
        explain={t('technical.advanced.explain')}
      >
        <IndicatorRow label={t('technical.advanced.mayer')} value={adv.mayer_multiple} t={t}
          signal={adv.mayer_multiple > 2.4 ? 'bearish' : adv.mayer_multiple < 0.8 ? 'bullish' : 'neutral'}
          description={
            adv.mayer_multiple > 2.4 ? `At ${adv.mayer_multiple?.toFixed(2)}, Bitcoin is MORE THAN 2.4x its 200-period average. Historically, this means it's dangerously overheated — major corrections have followed. Extreme caution.`
            : adv.mayer_multiple > 1.5 ? `At ${adv.mayer_multiple?.toFixed(2)}, Bitcoin is well above its long-term average. It's doing great but getting expensive. Not the best time to buy new positions.`
            : adv.mayer_multiple > 1 ? `At ${adv.mayer_multiple?.toFixed(2)}, Bitcoin is above its long-term average — healthy and positive. This is a normal bull market reading.`
            : adv.mayer_multiple > 0.8 ? `At ${adv.mayer_multiple?.toFixed(2)}, Bitcoin is slightly below its long-term average. It's relatively cheap compared to history — could be a buying opportunity.`
            : `At ${adv.mayer_multiple?.toFixed(2)}, Bitcoin is significantly below its long-term average. Historically, buying at this level has been very profitable long-term.`
          }
        />
        <IndicatorRow label={t('technical.advanced.piCycle')} value={adv.pi_cycle_ratio} t={t}
          signal={adv.pi_cycle_ratio > 0.95 ? 'bearish' : 'neutral'}
          description={
            adv.pi_cycle_ratio > 0.95 ? `At ${adv.pi_cycle_ratio?.toFixed(3)}, this is approaching 1.0 — DANGER ZONE. The Pi Cycle indicator has historically predicted every major Bitcoin top within 3 days when this hits 1.0.`
            : adv.pi_cycle_ratio > 0.8 ? `At ${adv.pi_cycle_ratio?.toFixed(3)}, getting warmer but not critical yet. The Pi Cycle top signal triggers when this reaches 1.0. Still some room to grow.`
            : `At ${adv.pi_cycle_ratio?.toFixed(3)}, well below the danger zone. Bitcoin still has significant room before hitting a Pi Cycle top signal. The cycle has more room to run.`
          }
        />
        <IndicatorRow label={t('technical.advanced.goldenDeath')} value={adv.ema_cross} t={t}
          signal={adv.ema_cross > 1 ? 'bullish' : 'bearish'}
          description={adv.ema_cross > 1
            ? `The 50-period average is ABOVE the 200-period average (${adv.ema_cross?.toFixed(3)}). This is called a "Golden Cross" — one of the most famous bullish signals in all of trading. It means the short-term trend is outperforming the long-term trend. Historically, big rallies follow.`
            : `The 50-period average is BELOW the 200-period average (${adv.ema_cross?.toFixed(3)}). This is called a "Death Cross" — one of the most famous bearish signals. The short-term trend is underperforming. Historically, this precedes further declines.`
          }
        />
        <IndicatorRow label={t('technical.advanced.zScore')} value={adv.zscore_20} t={t}
          signal={adv.zscore_20 > 2 ? 'bearish' : adv.zscore_20 < -2 ? 'bullish' : 'neutral'}
          description={
            adv.zscore_20 > 2 ? `At ${adv.zscore_20?.toFixed(2)} standard deviations above average — price has stretched TOO FAR above normal. Like a rubber band, it tends to snap back. Expect a pullback toward the average.`
            : adv.zscore_20 < -2 ? `At ${adv.zscore_20?.toFixed(2)} standard deviations below average — price has dropped TOO FAR below normal. Like a rubber band, it tends to snap back UP. Good buying opportunity.`
            : `At ${adv.zscore_20?.toFixed(2)} standard deviations from average — within normal range. No extreme stretching in either direction.`
          }
        />
      </Section>

      {/* ── Rate of Change ── */}
      <Section
        title={t('technical.rateOfChange.title')}
        color="text-text-secondary"
        explain={t('technical.rateOfChange.explain')}
      >
        {[
          { label: t('technical.rateOfChange.last1h'), val: mom.roc_1, period: 'the past hour' },
          { label: t('technical.rateOfChange.last6h'), val: mom.roc_6, period: 'the past 6 hours' },
          { label: t('technical.rateOfChange.last12h'), val: mom.roc_12, period: 'the past 12 hours' },
          { label: t('technical.rateOfChange.last24h'), val: mom.roc_24, period: 'the past 24 hours' },
        ].map(({ label, val, period }) => (
          <IndicatorRow key={label} label={label} value={val} unit="%" t={t}
            signal={val > 0 ? 'bullish' : val < 0 ? 'bearish' : 'neutral'}
            description={val != null ? (val > 0
              ? `Bitcoin went UP ${val.toFixed(2)}% over ${period}. ${val > 3 ? 'That\'s a significant move — strong buying pressure.' : val > 1 ? 'A moderate gain.' : 'A small gain.'}`
              : `Bitcoin went DOWN ${Math.abs(val).toFixed(2)}% over ${period}. ${val < -3 ? 'That\'s a significant drop — strong selling pressure.' : val < -1 ? 'A moderate decline.' : 'A small decline.'}`)
              : null
            }
          />
        ))}
      </Section>

      <IndicatorHistory />

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        {t('technical.updatesEveryMinute')}
      </p>
    </div>
  )
}
