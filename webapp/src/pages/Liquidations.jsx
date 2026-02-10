import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPrice, formatNumber } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'
import SubTabBar from '../components/SubTabBar'
import {
  ResponsiveContainer,
  BarChart,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
  Brush,
  CartesianGrid,
} from 'recharts'

const POLL_INTERVAL = 60_000

const MARKET_TABS = [
  { path: '/liquidations', labelKey: 'common:link.liquidations' },
  { path: '/powerlaw', labelKey: 'common:link.powerLaw' },
  { path: '/elliott-wave', labelKey: 'common:link.elliottWave' },
  { path: '/events', labelKey: 'common:link.events' },
  { path: '/tools', labelKey: 'common:link.tools' },
  { path: '/learn', labelKey: 'common:link.learn' },
]

// ── Color helpers ──

function liqIntensityColor(volume, maxVolume, type) {
  const ratio = Math.min(volume / (maxVolume || 1), 1)
  if (type === 'long') {
    // Red gradient: darker = more volume
    const alpha = 0.25 + ratio * 0.75
    return `rgba(255, 50, 80, ${alpha})`
  }
  // Short: cyan-green gradient
  const alpha = 0.25 + ratio * 0.75
  return `rgba(0, 220, 130, ${alpha})`
}

// ── Risk Meter ──

function RiskMeter({ longPct, shortPct, fundingRate, t }) {
  // Determine overall market risk direction
  const isLongHeavy = longPct > shortPct
  const imbalance = Math.abs(longPct - shortPct)
  const fundingBias = fundingRate > 0 ? 'long' : fundingRate < 0 ? 'short' : 'neutral'

  let riskLabel, riskColor, riskDesc
  if (imbalance < 3) {
    riskLabel = 'BALANCED'
    riskColor = 'text-accent-yellow'
    riskDesc = 'Market is balanced. No strong liquidation bias.'
  } else if (isLongHeavy) {
    riskLabel = 'LONG HEAVY'
    riskColor = 'text-accent-red'
    riskDesc = `${longPct.toFixed(1)}% longs — a dip could trigger cascading long liquidations.`
  } else {
    riskLabel = 'SHORT HEAVY'
    riskColor = 'text-accent-green'
    riskDesc = `${shortPct.toFixed(1)}% shorts — a pump could trigger a short squeeze.`
  }

  const needlePos = longPct // 0-100, 50 = balanced
  const needlePct = Math.max(5, Math.min(95, needlePos))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:liquidations.riskMeter').toUpperCase()}</h3>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
          riskColor === 'text-accent-red' ? 'bg-accent-red/10 border-accent-red/30' :
          riskColor === 'text-accent-green' ? 'bg-accent-green/10 border-accent-green/30' :
          'bg-accent-yellow/10 border-accent-yellow/30'
        } ${riskColor}`}>{riskLabel}</span>
      </div>

      {/* Gradient bar */}
      <div className="relative h-3 rounded-full bg-gradient-to-r from-accent-green via-accent-yellow to-accent-red mb-1">
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg border-2 border-bg-primary transition-all duration-500"
          style={{ left: `calc(${needlePct}% - 6px)` }}
        />
      </div>
      <div className="flex justify-between text-[9px] text-text-muted mb-2">
        <span>Short Heavy</span>
        <span>Balanced</span>
        <span>Long Heavy</span>
      </div>
      <p className="text-text-muted text-[10px]">{riskDesc}</p>
      {fundingRate != null && (
        <div className="flex items-center gap-2 mt-2 text-[10px]">
          <span className="text-text-muted">Funding confirms:</span>
          <span className={fundingRate >= 0 ? 'text-accent-green font-medium' : 'text-accent-red font-medium'}>
            {fundingBias === 'long' ? 'Longs paying shorts' : fundingBias === 'short' ? 'Shorts paying longs' : 'Neutral'}
            {' '}({(fundingRate * 100).toFixed(4)}%)
          </span>
        </div>
      )}
    </div>
  )
}

// ── Summary Card ──

function SummaryCard({ data, t }) {
  if (!data) return null
  const { current_price, summary } = data

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">{t('common:price.btcPrice').toUpperCase()}</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {formatPrice(current_price)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">{t('market:liquidations.openInterest').toUpperCase()}</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            ${formatNumber(summary.total_oi_usd)}
          </div>
        </div>
      </div>

      {/* OI Split Bar */}
      <div className="mb-2">
        <div className="flex h-2 rounded-full overflow-hidden">
          <div
            className="bg-accent-green transition-all duration-500"
            style={{ width: `${summary.long_pct || 50}%` }}
          />
          <div
            className="bg-accent-red transition-all duration-500"
            style={{ width: `${summary.short_pct || 50}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-[9px]">
          <span className="text-accent-green font-medium">
            Long {summary.long_pct?.toFixed(1)}% (${formatNumber(summary.long_oi_usd)})
          </span>
          <span className="text-accent-red font-medium">
            Short {summary.short_pct?.toFixed(1)}% (${formatNumber(summary.short_oi_usd)})
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Heatmap with intensity colors ──

function LiquidationHeatmap({ data, t }) {
  if (!data?.bins?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-[420px] flex items-center justify-center">
        <span className="text-text-muted text-sm">{t('common:app.noData')}</span>
      </div>
    )
  }

  const { bins, current_price } = data

  const maxLong = Math.max(...bins.map(b => b.long_liq_volume), 1)
  const maxShort = Math.max(...bins.map(b => b.short_liq_volume), 1)

  const chartData = bins.map((b) => ({
    price: `$${(b.price / 1000).toFixed(1)}k`,
    priceRaw: b.price,
    longLiq: -b.long_liq_volume,
    shortLiq: b.short_liq_volume,
    longVol: b.long_liq_volume,
    shortVol: b.short_liq_volume,
  }))

  const currentPriceLabel = `$${(current_price / 1000).toFixed(1)}k`
  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:liquidations.heatmap').toUpperCase()}</h3>
        {isZoomed ? (
          <button onClick={resetZoom} className="text-[10px] text-accent-blue">{t('common:btn.resetZoom')}</button>
        ) : (
          <span className="text-text-muted text-[9px]">{t('common:chart.pinchZoom')}</span>
        )}
      </div>
      <div className="h-[420px]" {...bindGestures}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={visibleData} layout="vertical" barGap={0} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 6" stroke="#1a1a28" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              tickFormatter={(v) => `${v >= 0 ? '' : '-'}$${formatNumber(Math.abs(v))}`}
              axisLine={false} tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="price"
              tick={{ fontSize: 9, fill: '#8b8b9e' }}
              width={55}
              axisLine={false} tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: '#1a1a2e',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 10,
                fontSize: 11,
                padding: '8px 12px',
              }}
              formatter={(v, name) => {
                const label = name === 'longLiq' ? t('market:liquidations.longLiquidations') : t('market:liquidations.shortLiquidations')
                return [`$${formatNumber(Math.abs(v))}`, label]
              }}
              labelFormatter={(label) => `Price Level: ${label}`}
            />
            <ReferenceLine
              y={currentPriceLabel}
              stroke="#4a9eff"
              strokeWidth={2}
              strokeDasharray="5 3"
              label={{ value: `Current ${currentPriceLabel}`, fill: '#4a9eff', fontSize: 10, position: 'insideTopRight' }}
            />

            {/* Long liquidations — intensity-colored */}
            <Bar dataKey="longLiq" name="longLiq" stackId="a" radius={[4, 0, 0, 4]}>
              {visibleData.map((entry, i) => (
                <Cell key={i} fill={liqIntensityColor(entry.longVol, maxLong, 'long')} />
              ))}
            </Bar>

            {/* Short liquidations — intensity-colored */}
            <Bar dataKey="shortLiq" name="shortLiq" stackId="a" radius={[0, 4, 4, 0]}>
              {visibleData.map((entry, i) => (
                <Cell key={i} fill={liqIntensityColor(entry.shortVol, maxShort, 'short')} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-3">
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {[0.3, 0.5, 0.7, 1.0].map((a, i) => (
              <div key={i} className="w-3 h-3 rounded-sm" style={{ background: `rgba(255, 50, 80, ${a})` }} />
            ))}
          </div>
          <span className="text-[10px] text-text-muted">Long Liq (below price)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {[0.3, 0.5, 0.7, 1.0].map((a, i) => (
              <div key={i} className="w-3 h-3 rounded-sm" style={{ background: `rgba(0, 220, 130, ${a})` }} />
            ))}
          </div>
          <span className="text-[10px] text-text-muted">Short Liq (above price)</span>
        </div>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-2">Pinch to zoom &middot; Drag to pan</p>
    </div>
  )
}

// ── Leverage Table ──

function LeverageTable({ levels, currentPrice }) {
  if (!levels?.levels?.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">LIQUIDATION BY LEVERAGE</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-white/5">
              <th className="text-left py-2 font-medium">Lev</th>
              <th className="text-right py-2 font-medium">Long Liq Price</th>
              <th className="text-right py-2 font-medium">Distance</th>
              <th className="text-right py-2 font-medium">Short Liq Price</th>
              <th className="text-right py-2 font-medium">Distance</th>
            </tr>
          </thead>
          <tbody>
            {levels.levels.map((l) => {
              const longDanger = l.long_distance_pct < 5
              const shortDanger = l.short_distance_pct < 5
              return (
                <tr key={l.leverage} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="py-2.5 font-bold text-accent-blue">{l.leverage}</td>
                  <td className="py-2.5 text-right text-accent-red tabular-nums font-medium">
                    {formatPrice(l.long_liq_price)}
                  </td>
                  <td className={`py-2.5 text-right tabular-nums text-[10px] font-medium ${
                    longDanger ? 'text-accent-red animate-pulse' : 'text-accent-red/60'
                  }`}>
                    -{l.long_distance_pct?.toFixed(2)}%
                  </td>
                  <td className="py-2.5 text-right text-accent-green tabular-nums font-medium">
                    {formatPrice(l.short_liq_price)}
                  </td>
                  <td className={`py-2.5 text-right tabular-nums text-[10px] font-medium ${
                    shortDanger ? 'text-accent-green animate-pulse' : 'text-accent-green/60'
                  }`}>
                    +{l.short_distance_pct?.toFixed(2)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Key Levels ──

function KeyLevels({ data }) {
  if (!data?.summary) return null
  const { summary, current_price } = data
  const longCluster = summary.nearest_long_cluster
  const shortCluster = summary.nearest_short_cluster

  if (!longCluster && !shortCluster) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">NEAREST LIQUIDATION CLUSTERS</h3>
      <div className="space-y-2">
        {longCluster && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-accent-red/5 border border-accent-red/15">
            <div>
              <div className="text-[9px] text-text-muted font-medium">LONG CLUSTER</div>
              <div className="text-base font-bold text-accent-red tabular-nums">
                {formatPrice(longCluster.price)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-text-muted font-medium">DISTANCE</div>
              <div className={`text-base font-bold tabular-nums ${
                longCluster.distance_pct < 5 ? 'text-accent-red animate-pulse' : 'text-accent-red'
              }`}>
                -{longCluster.distance_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-text-muted font-medium">VOLUME</div>
              <div className="text-base font-bold text-text-primary tabular-nums">
                ${formatNumber(longCluster.volume)}
              </div>
            </div>
          </div>
        )}
        {shortCluster && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-accent-green/5 border border-accent-green/15">
            <div>
              <div className="text-[9px] text-text-muted font-medium">SHORT CLUSTER</div>
              <div className="text-base font-bold text-accent-green tabular-nums">
                {formatPrice(shortCluster.price)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-text-muted font-medium">DISTANCE</div>
              <div className={`text-base font-bold tabular-nums ${
                shortCluster.distance_pct < 5 ? 'text-accent-green animate-pulse' : 'text-accent-green'
              }`}>
                +{shortCluster.distance_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-text-muted font-medium">VOLUME</div>
              <div className="text-base font-bold text-text-primary tabular-nums">
                ${formatNumber(shortCluster.volume)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Stats Grid ──

function StatsGrid({ stats }) {
  if (!stats) return null

  const items = [
    { label: 'OI (BTC)', value: stats.open_interest_btc ? formatNumber(stats.open_interest_btc) : '--' },
    { label: 'OI (USD)', value: stats.open_interest_usd ? `$${formatNumber(stats.open_interest_usd)}` : '--' },
    {
      label: 'L/S Ratio',
      value: stats.long_short_ratio?.long_short_ratio?.toFixed(2) ?? '--',
      color: stats.long_short_ratio?.long_short_ratio > 1 ? 'text-accent-green' : 'text-accent-red',
    },
    {
      label: 'Top Trader L/S',
      value: stats.top_trader_ratio?.long_short_ratio?.toFixed(2) ?? '--',
      color: stats.top_trader_ratio?.long_short_ratio > 1 ? 'text-accent-green' : 'text-accent-red',
    },
    {
      label: 'Funding Rate',
      value: stats.funding_rate != null ? `${(stats.funding_rate * 100).toFixed(4)}%` : '--',
      color: stats.funding_rate >= 0 ? 'text-accent-green' : 'text-accent-red',
    },
    {
      label: 'Mark Price',
      value: stats.mark_price ? formatPrice(stats.mark_price) : '--',
    },
  ]

  return (
    <div className="grid grid-cols-3 gap-2">
      {items.map((s) => (
        <div key={s.label} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{s.label}</div>
          <div className={`text-sm font-bold tabular-nums ${s.color || 'text-text-primary'}`}>
            {s.value}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Trading Insight ──

function TradingInsight({ data, stats }) {
  if (!data?.summary || !stats) return null

  const { summary } = data
  const fundingRate = stats.funding_rate
  const lsRatio = stats.long_short_ratio?.long_short_ratio
  const topRatio = stats.top_trader_ratio?.long_short_ratio

  const insights = []

  // Funding rate insight
  if (fundingRate != null) {
    if (Math.abs(fundingRate) > 0.001) {
      insights.push({
        icon: fundingRate > 0 ? (
          <svg className="w-4 h-4 text-accent-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-accent-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        ),
        text: fundingRate > 0
          ? `High positive funding (${(fundingRate * 100).toFixed(4)}%) — longs are paying premium. Price may correct down.`
          : `Negative funding (${(fundingRate * 100).toFixed(4)}%) — shorts are paying. Potential squeeze upward.`,
      })
    }
  }

  // L/S divergence from top traders
  if (lsRatio && topRatio && Math.abs(lsRatio - topRatio) > 0.3) {
    const retailBias = lsRatio > 1 ? 'long' : 'short'
    const smartBias = topRatio > 1 ? 'long' : 'short'
    if (retailBias !== smartBias) {
      insights.push({
        icon: (
          <svg className="w-4 h-4 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18h6M10 22h4" /><path d="M12 2a7 7 0 00-4 12.9V17h8v-2.1A7 7 0 0012 2z" />
          </svg>
        ),
        text: `Smart money divergence: Retail is ${retailBias} (${lsRatio.toFixed(2)}) while top traders are ${smartBias} (${topRatio.toFixed(2)}). Follow the smart money.`,
      })
    }
  }

  // Liquidation cluster proximity
  const longCluster = summary.nearest_long_cluster
  const shortCluster = summary.nearest_short_cluster
  if (longCluster && longCluster.distance_pct < 3) {
    insights.push({
      icon: (
        <svg className="w-4 h-4 text-accent-red" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      ),
      text: `Long liquidation cluster just ${longCluster.distance_pct.toFixed(1)}% below price ($${formatNumber(longCluster.volume)}). A dip could cascade.`,
    })
  }
  if (shortCluster && shortCluster.distance_pct < 3) {
    insights.push({
      icon: (
        <svg className="w-4 h-4 text-accent-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><polyline points="16 10 11 15 8 12" />
        </svg>
      ),
      text: `Short squeeze zone just ${shortCluster.distance_pct.toFixed(1)}% above price ($${formatNumber(shortCluster.volume)}). A pump could cascade.`,
    })
  }

  if (!insights.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">TRADING INSIGHTS</h3>
      <div className="space-y-2">
        {insights.map((ins, i) => (
          <div key={i} className="flex items-start gap-2 text-[11px]">
            <span className="shrink-0 mt-0.5">{ins.icon}</span>
            <p className="text-text-secondary">{ins.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Funding Rate + OI History ──

function FundingOIChart({ fundingData }) {
  if (!fundingData?.history?.length) return null

  const chartData = fundingData.history.map((d) => ({
    time: d.time || d.timestamp,
    funding: d.funding_rate != null ? d.funding_rate * 100 : null,
    oi: d.open_interest || d.oi,
  }))

  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-text-secondary text-xs font-semibold">FUNDING RATE & OPEN INTEREST</h3>
        {isZoomed && (
          <button onClick={resetZoom} className="text-[10px] text-accent-blue">Reset</button>
        )}
      </div>
      <p className="text-text-muted text-[9px] mb-3">
        Extreme positive funding = crash risk. Negative = squeeze potential.
      </p>
      <div className="h-[220px]" {...bindGestures}>
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
              yAxisId="funding"
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              tickFormatter={(v) => `${v.toFixed(3)}%`}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="oi"
              orientation="right"
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              tickFormatter={(v) => `${(v / 1e9).toFixed(1)}B`}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              formatter={(v, name) => {
                if (name === 'funding') return [`${v.toFixed(4)}%`, 'Funding Rate']
                if (name === 'oi') return [`$${formatNumber(v)}`, 'Open Interest']
                return [v, name]
              }}
              labelFormatter={(v) => v}
            />
            <ReferenceLine yAxisId="funding" y={0} stroke="#5a5a70" strokeDasharray="3 3" strokeWidth={0.5} />
            <Bar
              yAxisId="funding"
              dataKey="funding"
              name="funding"
              radius={[2, 2, 0, 0]}
            >
              {visibleData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.funding >= 0 ? 'rgba(0, 214, 143, 0.6)' : 'rgba(255, 77, 106, 0.6)'}
                />
              ))}
            </Bar>
            <Line
              yAxisId="oi"
              type="monotone"
              dataKey="oi"
              name="oi"
              stroke="#4a9eff"
              strokeWidth={1.5}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-2">Pinch to zoom &middot; Drag to pan</p>
    </div>
  )
}

// ── Main Page ──

export default function Liquidations() {
  const { t } = useTranslation(['market', 'common'])
  const tabs = useMemo(() => MARKET_TABS.map(tab => ({ ...tab, label: t(tab.labelKey) })), [t])
  const [mapData, setMapData] = useState(null)
  const [levels, setLevels] = useState(null)
  const [stats, setStats] = useState(null)
  const [fundingData, setFundingData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [map, lvl, st, fd] = await Promise.all([
        api.getLiquidationMap(),
        api.getLiquidationLevels(),
        api.getLiquidationStats(),
        api.getFundingHistory(168).catch(() => null),
      ])
      setMapData(map)
      setLevels(lvl)
      setStats(st)
      setFundingData(fd)
    } catch (err) {
      console.error('Liquidation fetch error:', err)
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
        <h1 className="text-lg font-bold">{t('market:liquidations.title')}</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-bg-card rounded-2xl" />
          <div className="h-16 bg-bg-card rounded-2xl" />
          <div className="h-[420px] bg-bg-card rounded-2xl" />
          <div className="h-48 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  const longPct = mapData?.summary?.long_pct || 50
  const shortPct = mapData?.summary?.short_pct || 50
  const fundingRate = stats?.funding_rate

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={tabs} />
      <h1 className="text-lg font-bold">{t('market:liquidations.title')}</h1>

      <SummaryCard data={mapData} t={t} />
      <RiskMeter longPct={longPct} shortPct={shortPct} fundingRate={fundingRate} t={t} />
      <LiquidationHeatmap data={mapData} t={t} />
      <KeyLevels data={mapData} />
      <FundingOIChart fundingData={fundingData} />
      <TradingInsight data={mapData} stats={stats} />
      <LeverageTable levels={levels} currentPrice={mapData?.current_price} />
      <StatsGrid stats={stats} />

      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">HOW TO USE THIS</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            <span className="text-text-secondary font-semibold">Liquidation clusters act as price magnets.</span>{' '}
            Market makers and whales deliberately push price toward large clusters to trigger
            cascading liquidations, creating rapid moves.
          </p>
          <p>
            <span className="text-accent-red font-semibold">Red bars</span> = long liquidations (below price).
            If price drops to these levels, leveraged longs get force-closed, accelerating the dump.{' '}
            <span className="text-accent-green font-semibold">Green bars</span> = short liquidations (above price).
            A move up triggers short squeezes.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Pro tip:</span>{' '}
            When funding rate and L/S ratio diverge from top trader positions, it often signals
            an incoming liquidation event. Watch the Trading Insights section above.
          </p>
        </div>
      </div>
    </div>
  )
}
