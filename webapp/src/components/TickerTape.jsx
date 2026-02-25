import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatPricePrecise, formatPercent } from '../utils/format'

const TICKER_ITEMS = [
  { key: 'btc', label: 'BTC', fetch: 'price' },
  { key: 'gold', label: 'Gold', fetch: 'macro' },
  { key: 'sp500', label: 'S&P500', fetch: 'macro' },
  { key: 'dxy', label: 'DXY', fetch: 'macro' },
  { key: 'eurusd', label: 'EUR/USD', fetch: 'macro' },
  { key: 'wti_oil', label: 'Oil', fetch: 'macro' },
  { key: 'vix', label: 'VIX', fetch: 'macro' },
  { key: 'nasdaq', label: 'NASDAQ', fetch: 'macro' },
]

function TickerItem({ label, price, change }) {
  const isUp = change >= 0
  return (
    <span className="inline-flex items-center gap-1.5 px-3 whitespace-nowrap">
      <span className="text-text-secondary text-[10px] font-medium">{label}</span>
      <span className="text-text-primary text-[10px] font-semibold tabular-nums">
        {price != null ? formatPricePrecise(price) : '--'}
      </span>
      {change != null && (
        <span className={`text-[9px] font-bold ${isUp ? 'text-accent-green' : 'text-accent-red'}`}>
          {formatPercent(change)}
        </span>
      )}
    </span>
  )
}

export default function TickerTape() {
  const [items, setItems] = useState([])

  const fetchAll = useCallback(async () => {
    try {
      const [priceData, macroData] = await Promise.all([
        api.getCurrentPrice(),
        api.getMacroData(),
      ])

      const built = TICKER_ITEMS.map((t) => {
        if (t.key === 'btc') {
          return {
            label: t.label,
            price: priceData?.price,
            change: priceData?.change_24h,
          }
        }
        const val = macroData?.[t.key]
        return {
          label: t.label,
          price: val?.price ?? (typeof val === 'number' ? val : null),
          change: val?.change_1h ?? val?.change_24h ?? null,
        }
      })
      setItems(built)
    } catch {
      // silent
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const iv = setInterval(fetchAll, 30_000)
    return () => clearInterval(iv)
  }, [fetchAll])

  if (!items.length) return null

  return (
    <div className="overflow-hidden bg-bg-card border-b border-white/5 py-1">
      <div className="ticker-scroll flex">
        {[...items, ...items].map((item, i) => (
          <TickerItem key={i} {...item} />
        ))}
      </div>
      <style>{`
        @keyframes ticker-marquee {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        .ticker-scroll {
          animation: ticker-marquee 30s linear infinite;
          width: max-content;
        }
        .ticker-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  )
}
