import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent } from '../utils/format'
import SubTabBar from '../components/SubTabBar'
import ForexTable from '../components/ForexTable'
import CryptoHeatmap from '../components/CryptoHeatmap'
import EconomicCalendar from '../components/EconomicCalendar'
import DataSourceFooter from '../components/DataSourceFooter'

const SECTION_TABS = [
  { path: 'crypto', labelKey: 'markets.crypto', icon: '\u{1F4B0}' },
  { path: 'indices', labelKey: 'markets.indices', icon: '\u{1F4CA}' },
  { path: 'forex', labelKey: 'markets.forex', icon: '\u{1F4B1}' },
  { path: 'commodities', labelKey: 'markets.commodities', icon: '\u{1F48E}' },
]

function AssetRow({ name, icon, price, change, rank }) {
  const isUp = change >= 0
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0 group">
      <div className="flex items-center gap-3">
        {rank && (
          <span className="text-[9px] text-text-muted w-4 text-right tabular-nums">{rank}</span>
        )}
        <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center border border-white/[0.06]">
          <span className="text-[10px] font-bold text-text-secondary">{icon}</span>
        </div>
        <span className="text-text-primary text-sm font-medium">{name}</span>
      </div>
      <div className="text-right flex items-center gap-3">
        <p className="text-text-primary text-sm font-semibold tabular-nums">
          {price != null ? formatPricePrecise(price) : '--'}
        </p>
        {change != null && (
          <div className={`px-2 py-0.5 rounded-md text-[11px] font-semibold tabular-nums ${
            isUp
              ? 'bg-accent-green/10 text-accent-green'
              : 'bg-accent-red/10 text-accent-red'
          }`}>
            {formatPercent(change)}
          </div>
        )}
      </div>
    </div>
  )
}

function LoadingSkeleton({ rows = 5 }) {
  return (
    <div className="bg-bg-card rounded-2xl p-4 space-y-3 animate-pulse">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-bg-secondary" />
          <div className="flex-1">
            <div className="h-3 w-20 bg-bg-secondary rounded" />
          </div>
          <div className="h-3 w-16 bg-bg-secondary rounded" />
          <div className="h-5 w-14 bg-bg-secondary rounded-md" />
        </div>
      ))}
    </div>
  )
}

function SectionCard({ title, children }) {
  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/[0.04]">
      {title && (
        <h3 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">{title}</h3>
      )}
      {children}
    </div>
  )
}

function CryptoSection() {
  const [coins, setCoins] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTrackedCoins()
      .then((data) => setCoins(Array.isArray(data) ? data : data?.coins ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={6} />

  return (
    <div className="space-y-3">
      <SectionCard>
        <CryptoHeatmap coins={coins} loading={loading} />
      </SectionCard>
      <SectionCard title="Top Assets">
        {coins.map((c, i) => (
          <AssetRow
            key={c.coin_id || c.symbol}
            name={c.name || c.symbol}
            icon={c.symbol?.toUpperCase()?.slice(0, 3) || '?'}
            price={c.current_price}
            change={c.price_change_24h}
            rank={i + 1}
          />
        ))}
      </SectionCard>
    </div>
  )
}

function IndicesSection() {
  const [macro, setMacro] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getMacroData().then(setMacro).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={7} />

  const indices = [
    { key: 'sp500', name: 'S&P 500', icon: 'SPX' },
    { key: 'nasdaq', name: 'NASDAQ', icon: 'NDX' },
    { key: 'dow_jones', name: 'Dow Jones', icon: 'DJI' },
    { key: 'dax', name: 'DAX 40', icon: 'DAX' },
    { key: 'nikkei_225', name: 'Nikkei 225', icon: 'NKY' },
    { key: 'ftse_100', name: 'FTSE 100', icon: 'UKX' },
    { key: 'russell_2000', name: 'Russell 2000', icon: 'RUT' },
  ]

  // Summary stats
  const gainers = indices.filter(idx => {
    const val = macro?.[idx.key]
    const change = val?.change_1h ?? val?.change_24h ?? 0
    return change > 0
  }).length
  const losers = indices.length - gainers

  return (
    <div className="space-y-3">
      {/* Mini summary */}
      <div className="flex gap-2">
        <div className="flex-1 bg-accent-green/5 rounded-xl px-3 py-2 border border-accent-green/10">
          <p className="text-accent-green text-lg font-bold">{gainers}</p>
          <p className="text-accent-green/60 text-[10px]">Gainers</p>
        </div>
        <div className="flex-1 bg-accent-red/5 rounded-xl px-3 py-2 border border-accent-red/10">
          <p className="text-accent-red text-lg font-bold">{losers}</p>
          <p className="text-accent-red/60 text-[10px]">Losers</p>
        </div>
      </div>

      <SectionCard title="Global Indices">
        {indices.map((idx) => {
          const val = macro?.[idx.key]
          const price = val?.price ?? (typeof val === 'number' ? val : null)
          const change = val?.change_1h ?? val?.change_24h ?? null
          return (
            <AssetRow key={idx.key} name={idx.name} icon={idx.icon} price={price} change={change} />
          )
        })}
      </SectionCard>
    </div>
  )
}

function CommoditiesSection() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getCommoditiesData().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={5} />

  const items = [
    { key: 'gold', name: 'Gold', icon: 'XAU' },
    { key: 'silver', name: 'Silver', icon: 'XAG' },
    { key: 'wti_oil', name: 'Crude Oil WTI', icon: 'CL' },
    { key: 'copper', name: 'Copper', icon: 'HG' },
    { key: 'natural_gas', name: 'Natural Gas', icon: 'NG' },
  ]

  return (
    <SectionCard title="Commodities">
      {items.map((item) => {
        const val = data?.[item.key]
        const price = val?.price ?? (typeof val === 'number' ? val : null)
        const change = val?.change_1h ?? val?.change_24h ?? null
        return (
          <AssetRow key={item.key} name={item.name} icon={item.icon} price={price} change={change} />
        )
      })}
    </SectionCard>
  )
}

export default function MarketOverview() {
  const { t } = useTranslation('common')
  const [activeTab, setActiveTab] = useState('crypto')

  return (
    <div className="px-4 pt-4 space-y-4 pb-4">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-text-primary">Markets</h1>
          <p className="text-text-muted text-[10px] mt-0.5">Real-time global market data</p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-green pulse-glow" />
          <span className="text-text-muted text-[10px]">Live</span>
        </div>
      </header>

      {/* Segmented Tab Bar */}
      <div className="bg-bg-secondary/60 rounded-xl p-1 flex gap-0.5">
        {SECTION_TABS.map((tab) => (
          <button
            key={tab.path}
            onClick={() => setActiveTab(tab.path)}
            className={`flex-1 py-2 rounded-lg text-[11px] font-semibold transition-all duration-200 ${
              activeTab === tab.path
                ? 'bg-bg-card text-text-primary shadow-sm border border-white/[0.06]'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t(tab.labelKey, { defaultValue: tab.path.charAt(0).toUpperCase() + tab.path.slice(1) })}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'crypto' && <CryptoSection />}
      {activeTab === 'indices' && <IndicesSection />}
      {activeTab === 'forex' && <ForexTable />}
      {activeTab === 'commodities' && <CommoditiesSection />}

      {/* Economic Calendar */}
      <EconomicCalendar />

      <DataSourceFooter sources={['yahoo', 'fred', 'coingecko']} />
    </div>
  )
}
