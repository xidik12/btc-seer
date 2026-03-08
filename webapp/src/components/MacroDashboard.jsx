import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api.js'
import { formatPricePrecise, formatPercent } from '../utils/format.js'
import CardShareButton from './CardShareButton'

const CORE_ITEMS = [
  { key: 'dxy', labelKey: 'macro.dxy', icon: '$' },
  { key: 'gold', labelKey: 'macro.gold', icon: 'Au' },
  { key: 'sp500', labelKey: 'macro.sp500', icon: 'SP' },
  { key: 'treasury_10y', labelKey: 'macro.treasury10y', icon: '10Y' },
  { key: 'nasdaq', labelKey: 'macro.nasdaq', icon: 'NDQ' },
  { key: 'vix', labelKey: 'macro.vix', icon: 'VX' },
  { key: 'eurusd', labelKey: 'macro.eurusd', icon: 'EU' },
]

const EXTENDED_ITEMS = [
  // Forex
  { key: 'gbpusd', labelKey: 'macro.gbpusd', icon: 'GB' },
  { key: 'usdjpy', labelKey: 'macro.usdjpy', icon: 'JP' },
  { key: 'usdchf', labelKey: 'macro.usdchf', icon: 'CH' },
  { key: 'audusd', labelKey: 'macro.audusd', icon: 'AU' },
  { key: 'usdcad', labelKey: 'macro.usdcad', icon: 'CA' },
  { key: 'nzdusd', labelKey: 'macro.nzdusd', icon: 'NZ' },
  // Commodities
  { key: 'wti_oil', labelKey: 'macro.wtiOil', icon: 'OIL' },
  { key: 'silver', labelKey: 'macro.silver', icon: 'Ag' },
  { key: 'copper', labelKey: 'macro.copper', icon: 'Cu' },
  { key: 'natural_gas', labelKey: 'macro.naturalGas', icon: 'NG' },
  // Indices
  { key: 'dow_jones', labelKey: 'macro.dowJones', icon: 'DJI' },
  { key: 'russell_2000', labelKey: 'macro.russell', icon: 'RUT' },
  { key: 'dax', labelKey: 'macro.dax', icon: 'DAX' },
  { key: 'nikkei_225', labelKey: 'macro.nikkei', icon: 'N225' },
  { key: 'ftse_100', labelKey: 'macro.ftse', icon: 'FTSE' },
  // Treasury yields
  { key: 'treasury_2y', labelKey: 'macro.treasury2y', icon: '2Y' },
  { key: 'treasury_5y', labelKey: 'macro.treasury5y', icon: '5Y' },
  { key: 'treasury_30y', labelKey: 'macro.treasury30y', icon: '30Y' },
]

const KEY_ALIASES = {
  dxy: ['dxy', 'DXY', 'usd_index', 'dollar_index'],
  gold: ['gold', 'GOLD', 'xauusd', 'XAUUSD'],
  sp500: ['sp500', 'SP500', 'spx', 'SPX', 's&p500', 'sp_500'],
  treasury_10y: ['treasury_10y', 'treasury10y', '10y', '10Y', 'us10y', 'US10Y'],
  nasdaq: ['nasdaq', 'NASDAQ', 'ndx', 'NDX', 'nasdaq100'],
  vix: ['vix', 'VIX', 'cboe_vix'],
  eurusd: ['eurusd', 'EURUSD', 'eur_usd', 'EUR/USD'],
}

function findValue(data, key) {
  if (!data) return null
  if (data[key] !== undefined) return data[key]
  const aliases = KEY_ALIASES[key] || []
  for (const alias of aliases) {
    if (data[alias] !== undefined) return data[alias]
  }
  if (Array.isArray(data)) {
    const match = data.find(
      (item) =>
        aliases.includes(item.key) ||
        aliases.includes(item.symbol) ||
        aliases.includes(item.name?.toLowerCase())
    )
    return match || null
  }
  return null
}

function extractPrice(val) {
  if (val === null || val === undefined) return null
  if (typeof val === 'number') return val
  return val?.price ?? val?.value ?? val?.last ?? null
}

function extractChange(val) {
  if (val === null || val === undefined) return null
  if (typeof val === 'number') return null
  return val?.change_1h ?? val?.change1h ?? val?.change ?? val?.pct_change ?? null
}

function MacroCard({ label, icon, price, change }) {
  const hasPrice = price !== null && price !== undefined
  const hasChange = change !== null && change !== undefined
  const isPositive = change >= 0

  return (
    <div className="bg-bg-secondary rounded-xl p-3 flex flex-col justify-between min-h-[80px]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-secondary text-xs">{label}</span>
        <span className="text-text-muted text-[10px] font-mono bg-bg-card rounded px-1.5 py-0.5">
          {icon}
        </span>
      </div>
      <div>
        {hasPrice ? (
          <p className="text-text-primary font-semibold text-sm">
            {formatPricePrecise(price)}
          </p>
        ) : (
          <p className="text-text-muted text-sm">--</p>
        )}
        {hasChange ? (
          <p
            className={`text-xs mt-0.5 ${
              isPositive ? 'text-accent-green' : 'text-accent-red'
            }`}
          >
            {formatPercent(change)}
          </p>
        ) : (
          <p className="text-text-muted text-xs mt-0.5">--</p>
        )}
      </div>
    </div>
  )
}

export default function MacroDashboard() {
  const { t } = useTranslation('dashboard')
  const [macroData, setMacroData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAll, setShowAll] = useState(false)
  const cardRef = useRef(null)

  const fetchMacro = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getMacroData()
      setMacroData(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMacro()
    const interval = setInterval(fetchMacro, 300_000)
    return () => clearInterval(interval)
  }, [fetchMacro])

  const items = showAll ? [...CORE_ITEMS, ...EXTENDED_ITEMS] : CORE_ITEMS

  return (
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary font-semibold text-sm">
          {t('macro.title')}
        </h3>
        {!loading && !error && (
          <div className="flex items-center gap-2">
            <CardShareButton cardRef={cardRef} label="Macro Dashboard" filename="macro.png" />
            <span className="text-text-muted text-[10px]">
              {t('macro.updatesEvery5m')}
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div
              key={i}
              className="bg-bg-secondary rounded-xl p-3 animate-pulse min-h-[80px]"
            >
              <div className="h-2 w-12 bg-bg-card rounded mb-3" />
              <div className="h-4 w-16 bg-bg-card rounded mb-1" />
              <div className="h-2 w-10 bg-bg-card rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('macro.title') })}</p>
          <button
            onClick={fetchMacro}
            className="text-accent-blue text-xs hover:underline"
          >
            {t('common:app.retry')}
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {items.map(({ key, labelKey, icon }) => {
              const raw = findValue(macroData, key)
              const price = extractPrice(raw)
              const change = extractChange(raw)
              return (
                <MacroCard
                  key={key}
                  label={t(labelKey)}
                  icon={icon}
                  price={price}
                  change={change}
                />
              )
            })}
          </div>
          <button
            onClick={() => setShowAll(!showAll)}
            className="w-full text-center text-accent-blue text-[10px] mt-3 hover:underline"
          >
            {showAll ? t('macro.showLess') : t('macro.showAll')}
          </button>
        </>
      )}
    </div>
  )
}
