import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPrice, formatNumber } from '../utils/format'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts'

const POLL_INTERVAL = 60_000

function SummaryCard({ data }) {
  if (!data) return null
  const { current_price, summary } = data
  const moreShorts = (summary.short_pct || 0) > (summary.long_pct || 0)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">BTC PRICE</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {formatPrice(current_price)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">OPEN INTEREST</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            ${formatNumber(summary.total_oi_usd)}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-xs font-bold px-2 py-1 rounded border ${
          moreShorts
            ? 'bg-accent-green/10 border-accent-green/30 text-accent-green'
            : 'bg-accent-red/10 border-accent-red/30 text-accent-red'
        }`}>
          {moreShorts ? 'More Shorts at Risk' : 'More Longs at Risk'}
        </span>
        <span className="text-text-muted text-[10px]">
          L {summary.long_pct?.toFixed(1)}% / S {summary.short_pct?.toFixed(1)}%
        </span>
        {summary.funding_rate != null && (
          <span className={`text-[10px] font-mono ${summary.funding_rate >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            FR: {(summary.funding_rate * 100).toFixed(4)}%
          </span>
        )}
      </div>
    </div>
  )
}

function LiquidationHeatmap({ data }) {
  if (!data?.bins?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-[400px] flex items-center justify-center">
        <span className="text-text-muted text-sm">No liquidation data</span>
      </div>
    )
  }

  const { bins, current_price } = data

  // Transform: long liquidations go negative (left), short positive (right)
  const chartData = bins.map((b) => ({
    price: `$${(b.price / 1000).toFixed(1)}k`,
    priceRaw: b.price,
    longLiq: -b.long_liq_volume,
    shortLiq: b.short_liq_volume,
    longVol: b.long_liq_volume,
    shortVol: b.short_liq_volume,
  }))

  const currentPriceLabel = `$${(current_price / 1000).toFixed(1)}k`

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">LIQUIDATION HEATMAP</h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} layout="vertical" barGap={0}>
          <XAxis
            type="number"
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => `${v >= 0 ? '' : '-'}$${formatNumber(Math.abs(v))}`}
          />
          <YAxis
            type="category"
            dataKey="price"
            tick={{ fontSize: 9, fill: '#888' }}
            width={55}
          />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v, name) => {
              const label = name === 'longLiq' ? 'Long Liquidations' : 'Short Liquidations'
              return [`$${formatNumber(Math.abs(v))}`, label]
            }}
          />
          <ReferenceLine
            y={currentPriceLabel}
            stroke="#4a9eff"
            strokeWidth={2}
            strokeDasharray="4 4"
            label={{ value: 'Price', fill: '#4a9eff', fontSize: 10 }}
          />
          <Bar dataKey="longLiq" name="longLiq" stackId="a" radius={[4, 0, 0, 4]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill="rgba(255,77,106,0.7)" />
            ))}
          </Bar>
          <Bar dataKey="shortLiq" name="shortLiq" stackId="a" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill="rgba(0,200,83,0.7)" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 mt-2 text-[10px] text-text-muted">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-accent-red inline-block" /> Long Liquidations (below)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-accent-green inline-block" /> Short Liquidations (above)
        </span>
      </div>
    </div>
  )
}

function LeverageTable({ levels }) {
  if (!levels?.levels?.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">LEVERAGE LIQUIDATION LEVELS</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-white/5">
              <th className="text-left py-2 font-medium">Leverage</th>
              <th className="text-right py-2 font-medium">Long Liq</th>
              <th className="text-right py-2 font-medium">Dist %</th>
              <th className="text-right py-2 font-medium">Short Liq</th>
              <th className="text-right py-2 font-medium">Dist %</th>
            </tr>
          </thead>
          <tbody>
            {levels.levels.map((l) => (
              <tr key={l.leverage} className="border-b border-white/5">
                <td className="py-2 font-bold text-text-primary">{l.leverage}</td>
                <td className="py-2 text-right text-accent-red tabular-nums">
                  {formatPrice(l.long_liq_price)}
                </td>
                <td className="py-2 text-right text-accent-red tabular-nums text-[10px]">
                  -{l.long_distance_pct?.toFixed(2)}%
                </td>
                <td className="py-2 text-right text-accent-green tabular-nums">
                  {formatPrice(l.short_liq_price)}
                </td>
                <td className="py-2 text-right text-accent-green tabular-nums text-[10px]">
                  +{l.short_distance_pct?.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function KeyLevels({ data }) {
  if (!data?.summary) return null
  const { summary, current_price } = data
  const longCluster = summary.nearest_long_cluster
  const shortCluster = summary.nearest_short_cluster

  if (!longCluster && !shortCluster) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">KEY LIQUIDATION LEVELS</h3>
      <div className="space-y-2">
        {longCluster && (
          <div className="flex items-center justify-between p-2 rounded-xl bg-accent-red/5 border border-accent-red/15">
            <div>
              <div className="text-[10px] text-text-muted">Largest Long Cluster</div>
              <div className="text-sm font-bold text-accent-red tabular-nums">
                {formatPrice(longCluster.price)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-text-muted">Distance</div>
              <div className="text-sm font-bold text-accent-red tabular-nums">
                -{longCluster.distance_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-text-muted">Volume</div>
              <div className="text-sm font-bold text-text-primary tabular-nums">
                ${formatNumber(longCluster.volume)}
              </div>
            </div>
          </div>
        )}
        {shortCluster && (
          <div className="flex items-center justify-between p-2 rounded-xl bg-accent-green/5 border border-accent-green/15">
            <div>
              <div className="text-[10px] text-text-muted">Largest Short Cluster</div>
              <div className="text-sm font-bold text-accent-green tabular-nums">
                {formatPrice(shortCluster.price)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-text-muted">Distance</div>
              <div className="text-sm font-bold text-accent-green tabular-nums">
                +{shortCluster.distance_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-text-muted">Volume</div>
              <div className="text-sm font-bold text-text-primary tabular-nums">
                ${formatNumber(shortCluster.volume)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatsGrid({ stats }) {
  if (!stats) return null

  const items = [
    { label: 'OI (BTC)', value: stats.open_interest_btc ? formatNumber(stats.open_interest_btc) : '--' },
    { label: 'OI (USD)', value: stats.open_interest_usd ? `$${formatNumber(stats.open_interest_usd)}` : '--' },
    {
      label: 'L/S Ratio',
      value: stats.long_short_ratio?.long_short_ratio?.toFixed(2) ?? '--',
    },
    {
      label: 'Top Traders L/S',
      value: stats.top_trader_ratio?.long_short_ratio?.toFixed(2) ?? '--',
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

export default function Liquidations() {
  const [mapData, setMapData] = useState(null)
  const [levels, setLevels] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [map, lvl, st] = await Promise.all([
        api.getLiquidationMap(),
        api.getLiquidationLevels(),
        api.getLiquidationStats(),
      ])
      setMapData(map)
      setLevels(lvl)
      setStats(st)
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
        <h1 className="text-lg font-bold">Liquidation Map</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-bg-card rounded-2xl" />
          <div className="h-[400px] bg-bg-card rounded-2xl" />
          <div className="h-48 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-4">
      <h1 className="text-lg font-bold">Liquidation Map</h1>

      <SummaryCard data={mapData} />
      <LiquidationHeatmap data={mapData} />
      <LeverageTable levels={levels} />
      <KeyLevels data={mapData} />
      <StatsGrid stats={stats} />

      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">HOW IT WORKS</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>
            This map estimates where leveraged BTC positions would get liquidated based on
            current open interest, long/short ratios, and recent volume profile.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Red bars</span> show estimated
            long liquidation clusters (below current price). <span className="text-text-secondary font-semibold">Green bars</span> show
            short liquidation clusters (above current price). Large clusters act as price magnets.
          </p>
          <p>
            <span className="text-text-secondary font-semibold">Note:</span> These are estimates
            based on public data and assumed leverage distribution. Actual liquidation levels
            depend on individual trader entries, leverage, and margin.
          </p>
        </div>
      </div>
    </div>
  )
}
