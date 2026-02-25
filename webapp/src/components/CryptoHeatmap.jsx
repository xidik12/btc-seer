import { useMemo } from 'react'
import { formatPricePrecise } from '../utils/format'

function getHeatColor(change) {
  if (change == null) return { bg: 'rgba(42, 42, 56, 0.6)', text: '#9090a8' }
  const abs = Math.abs(change)
  if (change >= 0) {
    if (abs >= 7) return { bg: 'rgba(0, 200, 83, 0.35)', text: '#00d68f' }
    if (abs >= 4) return { bg: 'rgba(0, 200, 83, 0.25)', text: '#00d68f' }
    if (abs >= 2) return { bg: 'rgba(0, 200, 83, 0.15)', text: '#00d68f' }
    return { bg: 'rgba(0, 200, 83, 0.08)', text: '#5ae4a7' }
  } else {
    if (abs >= 7) return { bg: 'rgba(255, 77, 106, 0.35)', text: '#ff4d6a' }
    if (abs >= 4) return { bg: 'rgba(255, 77, 106, 0.25)', text: '#ff4d6a' }
    if (abs >= 2) return { bg: 'rgba(255, 77, 106, 0.15)', text: '#ff4d6a' }
    return { bg: 'rgba(255, 77, 106, 0.08)', text: '#ff8fa3' }
  }
}

function formatMarketCap(val) {
  if (!val) return ''
  if (val >= 1e12) return `$${(val / 1e12).toFixed(1)}T`
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
  if (val >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
  return `$${val.toLocaleString()}`
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
        <div className="flex items-center justify-between mb-3">
          <p className="text-text-secondary text-xs font-semibold">Crypto Heatmap</p>
          <span className="text-text-muted text-[10px]">24h Change</span>
        </div>
        <div className="grid grid-cols-3 gap-1 animate-pulse">
          {Array.from({ length: 9 }, (_, i) => (
            <div key={i} className="rounded-lg bg-bg-secondary" style={{ height: i < 3 ? '88px' : '72px' }} />
          ))}
        </div>
      </div>
    )
  }

  if (!sorted.length) return null

  const maxCap = sorted[0]?.market_cap || 1

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-text-secondary text-xs font-semibold">Crypto Heatmap</p>
        <span className="text-text-muted text-[10px]">24h Change</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {sorted.map((coin, i) => {
          const change = coin.price_change_24h ?? coin.change_24h ?? null
          const capRatio = (coin.market_cap || 0) / maxCap
          const { bg, text } = getHeatColor(change)
          // Top 3 get larger cells, rest proportional
          const isTop = i < 3
          const minH = 56
          const maxH = isTop ? 92 : 76
          const h = Math.round(minH + (maxH - minH) * Math.sqrt(capRatio))

          return (
            <div
              key={coin.coin_id || coin.symbol}
              className="rounded-lg flex flex-col items-center justify-center relative overflow-hidden transition-all duration-300 border border-white/[0.04]"
              style={{
                height: `${h}px`,
                background: bg,
              }}
            >
              {/* Subtle inner glow for strong movers */}
              {change != null && Math.abs(change) >= 4 && (
                <div
                  className="absolute inset-0 rounded-lg"
                  style={{
                    background: `radial-gradient(ellipse at center, ${text}15 0%, transparent 70%)`,
                  }}
                />
              )}
              <span className="text-white text-xs font-bold relative z-10 leading-none">
                {coin.symbol?.toUpperCase() || '?'}
              </span>
              {change != null && (
                <span
                  className="text-[11px] font-bold relative z-10 mt-0.5 leading-none"
                  style={{ color: text }}
                >
                  {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                </span>
              )}
              {coin.current_price && (
                <span className="text-white/40 text-[9px] relative z-10 mt-1 leading-none tabular-nums">
                  {formatPricePrecise(coin.current_price)}
                </span>
              )}
            </div>
          )
        })}
      </div>
      {/* Legend bar */}
      <div className="flex items-center justify-center gap-3 mt-2.5">
        {[
          { label: '>4%', color: 'rgba(255, 77, 106, 0.3)' },
          { label: '0-4%', color: 'rgba(255, 77, 106, 0.12)' },
          { label: '0-4%', color: 'rgba(0, 200, 83, 0.12)' },
          { label: '>4%', color: 'rgba(0, 200, 83, 0.3)' },
        ].map((item, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className="w-3 h-2 rounded-sm" style={{ background: item.color }} />
            <span className="text-text-muted text-[8px]">
              {i < 2 ? '-' : '+'}{item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
