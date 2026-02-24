import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent } from '../utils/format'
import SubTabBar from '../components/SubTabBar'
import ForexTable from '../components/ForexTable'
import CryptoHeatmap from '../components/CryptoHeatmap'
import EconomicCalendar from '../components/EconomicCalendar'
import DataSourceFooter from '../components/DataSourceFooter'

const SECTION_TABS = [
  { path: 'crypto', labelKey: 'Crypto' },
  { path: 'indices', labelKey: 'Indices' },
  { path: 'forex', labelKey: 'Forex' },
  { path: 'commodities', labelKey: 'Commodities' },
]

function AssetRow({ name, icon, price, change }) {
  const isUp = change >= 0
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-mono bg-bg-card rounded px-1.5 py-0.5 text-text-muted">{icon}</span>
        <span className="text-text-primary text-sm font-medium">{name}</span>
      </div>
      <div className="text-right">
        <p className="text-text-primary text-sm font-semibold tabular-nums">
          {price != null ? formatPricePrecise(price) : '--'}
        </p>
        {change != null && (
          <p className={`text-[10px] ${isUp ? 'text-accent-green' : 'text-accent-red'}`}>
            {formatPercent(change)}
          </p>
        )}
      </div>
    </div>
  )
}

function CryptoSection() {
  const [coins, setCoins] = useState([])

  useEffect(() => {
    api.getTrackedCoins().then(setCoins).catch(() => {})
  }, [])

  return (
    <div className="bg-bg-card rounded-xl p-4">
      <CryptoHeatmap coins={coins} />
      <div className="mt-3">
        {coins.map((c) => (
          <AssetRow
            key={c.coin_id || c.symbol}
            name={c.name || c.symbol}
            icon={c.symbol?.toUpperCase()?.slice(0, 3) || '?'}
            price={c.current_price}
            change={c.price_change_24h}
          />
        ))}
      </div>
    </div>
  )
}

function IndicesSection() {
  const [macro, setMacro] = useState(null)

  useEffect(() => {
    api.getMacroData().then(setMacro).catch(() => {})
  }, [])

  const indices = [
    { key: 'sp500', name: 'S&P 500', icon: 'SP' },
    { key: 'nasdaq', name: 'NASDAQ', icon: 'NDQ' },
    { key: 'dow_jones', name: 'Dow Jones', icon: 'DJI' },
    { key: 'dax', name: 'DAX', icon: 'DAX' },
    { key: 'nikkei_225', name: 'Nikkei 225', icon: 'N225' },
    { key: 'ftse_100', name: 'FTSE 100', icon: 'FTSE' },
    { key: 'russell_2000', name: 'Russell 2000', icon: 'RUT' },
  ]

  return (
    <div className="bg-bg-card rounded-xl p-4">
      {indices.map((idx) => {
        const val = macro?.[idx.key]
        const price = val?.price ?? (typeof val === 'number' ? val : null)
        const change = val?.change_1h ?? val?.change_24h ?? null
        return (
          <AssetRow key={idx.key} name={idx.name} icon={idx.icon} price={price} change={change} />
        )
      })}
    </div>
  )
}

function CommoditiesSection() {
  const [data, setData] = useState(null)

  useEffect(() => {
    api.getCommoditiesData().then(setData).catch(() => {})
  }, [])

  const items = [
    { key: 'gold', name: 'Gold', icon: 'Au' },
    { key: 'silver', name: 'Silver', icon: 'Ag' },
    { key: 'wti_oil', name: 'Crude Oil (WTI)', icon: 'OIL' },
    { key: 'copper', name: 'Copper', icon: 'Cu' },
    { key: 'natural_gas', name: 'Natural Gas', icon: 'NG' },
  ]

  return (
    <div className="bg-bg-card rounded-xl p-4">
      {items.map((item) => {
        const val = data?.[item.key]
        const price = val?.price ?? (typeof val === 'number' ? val : null)
        const change = val?.change_1h ?? val?.change_24h ?? null
        return (
          <AssetRow key={item.key} name={item.name} icon={item.icon} price={price} change={change} />
        )
      })}
    </div>
  )
}

export default function MarketOverview() {
  const [activeTab, setActiveTab] = useState('crypto')

  return (
    <div className="px-4 pt-4 space-y-4">
      <header>
        <h1 className="text-lg font-bold text-text-primary">Market Overview</h1>
        <p className="text-text-muted text-xs mt-0.5">TradingView-style market data</p>
      </header>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {SECTION_TABS.map((tab) => (
          <button
            key={tab.path}
            onClick={() => setActiveTab(tab.path)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.path
                ? 'bg-accent-blue text-white'
                : 'bg-bg-card text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.labelKey}
          </button>
        ))}
      </div>

      {activeTab === 'crypto' && <CryptoSection />}
      {activeTab === 'indices' && <IndicesSection />}
      {activeTab === 'forex' && <ForexTable />}
      {activeTab === 'commodities' && <CommoditiesSection />}

      <EconomicCalendar />

      <DataSourceFooter sources={['yahoo', 'fred', 'coingecko']} />
    </div>
  )
}
