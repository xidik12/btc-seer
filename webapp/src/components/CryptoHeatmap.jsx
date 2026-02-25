import { useMemo } from 'react'

function getChangeColor(change) {
  if (change == null) return 'bg-bg-secondary'
  if (change >= 5) return 'bg-[#166534]'
  if (change >= 3) return 'bg-[#15803d]'
  if (change >= 1) return 'bg-[#22c55e]/40'
  if (change >= 0) return 'bg-[#22c55e]/20'
  if (change >= -1) return 'bg-[#ef4444]/20'
  if (change >= -3) return 'bg-[#ef4444]/40'
  if (change >= -5) return 'bg-[#dc2626]'
  return 'bg-[#991b1b]'
}

export default function CryptoHeatmap({ coins = [], loading = false }) {
  const sorted = useMemo(() => {
    return [...coins]
      .filter((c) => c.market_cap || c.current_price)
      .sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0))
      .slice(0, 12)
  }, [coins])

  if (loading) {
    return (
      <div>
        <p className="text-text-secondary text-[10px] font-semibold mb-2">Crypto Heatmap (24h)</p>
        <div className="grid grid-cols-3 gap-1.5 animate-pulse">
          {Array.from({ length: 9 }, (_, i) => (
            <div key={i} className="rounded-lg bg-bg-secondary" style={{ height: '60px' }} />
          ))}
        </div>
      </div>
    )
  }

  if (!sorted.length) return null

  const maxCap = sorted[0]?.market_cap || 1

  return (
    <div>
      <p className="text-text-secondary text-[10px] font-semibold mb-2">Crypto Heatmap (24h)</p>
      <div className="grid grid-cols-3 gap-1.5">
        {sorted.map((coin) => {
          const change = coin.price_change_24h ?? coin.change_24h ?? null
          const capRatio = (coin.market_cap || 0) / maxCap
          const minH = 48
          const maxH = 80
          const h = Math.round(minH + (maxH - minH) * Math.sqrt(capRatio))

          return (
            <div
              key={coin.coin_id || coin.symbol}
              className={`rounded-lg flex flex-col items-center justify-center ${getChangeColor(change)} transition-colors`}
              style={{ height: `${h}px` }}
            >
              <span className="text-white text-xs font-bold">
                {coin.symbol?.toUpperCase() || '?'}
              </span>
              {change != null && (
                <span className="text-white/80 text-[10px] font-semibold">
                  {change >= 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
