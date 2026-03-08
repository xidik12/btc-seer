import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatNumber } from '../utils/format'
import SubTabBar from '../components/SubTabBar'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts'

const TABS = [
  { path: '/whales', labelKey: 'common:link.whales' },
  { path: '/address-distribution', labelKey: 'common:link.addressDist' },
]

const BUCKET_COLORS = [
  '#94a3b8', // Dust — slate
  '#a1a1aa', // Micro — zinc
  '#6366f1', // Shrimp — indigo
  '#8b5cf6', // Crab — violet
  '#a78bfa', // Octopus — light violet
  '#3b82f6', // Fish — blue
  '#06b6d4', // Dolphin — cyan
  '#14b8a6', // Shark — teal
  '#f59e0b', // Whale — amber
  '#f97316', // Humpback — orange
  '#ef4444', // Mega Whale — red
]

export default function AddressDistribution() {
  const { t } = useTranslation(['market', 'common'])
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getAddressDistribution()
      setData(result)
    } catch (err) {
      console.error('Address distribution error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 300_000) // 5 min
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <SubTabBar tabs={TABS} />
        <h1 className="text-lg font-bold">{t('market:addressDist.title')}</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-20 bg-bg-card rounded-2xl" />
          <div className="h-[300px] bg-bg-card rounded-2xl" />
          <div className="h-48 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  const buckets = data?.buckets || []
  const chartData = buckets.map((b, i) => ({
    name: b.label,
    count: b.count,
    pct: b.pct,
    fill: BUCKET_COLORS[i] || '#4a9eff',
  }))

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={TABS} />
      <h1 className="text-lg font-bold">{t('market:addressDist.title')}</h1>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">{t('market:addressDist.totalAddresses')}</p>
          <p className="text-text-primary text-xl font-bold tabular-nums">
            {data?.total_addresses ? formatNumber(data.total_addresses) : '--'}
          </p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">{t('market:addressDist.totalWithBalance')}</p>
          <p className="text-text-primary text-xl font-bold tabular-nums">
            {data?.total_with_balance ? formatNumber(data.total_with_balance) : '--'}
          </p>
        </div>
      </div>

      {/* Bar Chart */}
      {buckets.length > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <XAxis
                  type="number"
                  tick={{ fontSize: 9, fill: '#5a5a70' }}
                  tickFormatter={v => formatNumber(v)}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10, fill: '#8b8b9e' }}
                  width={75}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1a1a2e',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 10,
                    fontSize: 11,
                    padding: '8px 12px',
                  }}
                  formatter={(v) => [formatNumber(v), t('market:addressDist.count')]}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Table */}
      {buckets.length > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-white/5">
                  <th className="text-left py-2 font-medium">{t('market:addressDist.bucket')}</th>
                  <th className="text-left py-2 font-medium">{t('market:addressDist.btcRange')}</th>
                  <th className="text-right py-2 font-medium">{t('market:addressDist.count')}</th>
                  <th className="text-right py-2 font-medium">{t('market:addressDist.percentage')}</th>
                </tr>
              </thead>
              <tbody>
                {buckets.map((b, i) => (
                  <tr key={b.label} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-sm" style={{ background: BUCKET_COLORS[i] }} />
                        <span className="text-text-primary font-medium">{b.label}</span>
                      </div>
                    </td>
                    <td className="py-2.5 text-text-muted font-mono text-[10px]">{b.btc_range} BTC</td>
                    <td className="py-2.5 text-right text-text-primary tabular-nums font-medium">
                      {b.count?.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{ width: `${Math.min(b.pct, 100)}%`, background: BUCKET_COLORS[i] }}
                          />
                        </div>
                        <span className="text-text-muted tabular-nums w-12 text-right">{b.pct}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
