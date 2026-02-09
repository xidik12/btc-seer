import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'

const COLORS = {
  'Extreme Fear': '#ff4d6a',
  'Fear': '#ff8c42',
  'Neutral': '#ffc107',
  'Greed': '#66bb6a',
  'Extreme Greed': '#00c853',
}

function getColor(value) {
  if (value <= 20) return COLORS['Extreme Fear']
  if (value <= 40) return COLORS['Fear']
  if (value <= 60) return COLORS['Neutral']
  if (value <= 80) return COLORS['Greed']
  return COLORS['Extreme Greed']
}

export default function FearGreedWidget() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getFearGreed(7)
      setData(res)
    } catch (err) {
      console.error('Fear & Greed fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 300_000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-3">Fear & Greed Index</h3>
        <div className="animate-pulse"><div className="h-20 bg-bg-secondary rounded-xl" /></div>
      </div>
    )
  }

  const current = data?.current
  if (!current) return null

  const value = current.value
  const label = current.label || 'Unknown'
  const color = getColor(value)
  const history = (data?.history || []).slice(0, 7).reverse()

  // Gauge angle: 0 = -90deg (left), 100 = 90deg (right)
  const angle = -90 + (value / 100) * 180

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <h3 className="text-text-primary font-semibold text-sm mb-3">Fear & Greed Index</h3>

      <div className="flex items-center gap-4">
        {/* Gauge */}
        <div className="relative w-24 h-14 flex-shrink-0">
          <svg viewBox="0 0 100 55" className="w-full h-full">
            {/* Background arc */}
            <path d="M 5 50 A 45 45 0 0 1 95 50" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" strokeLinecap="round" />
            {/* Colored arc */}
            <path d="M 5 50 A 45 45 0 0 1 95 50" fill="none" stroke="url(#fgGradient)" strokeWidth="8" strokeLinecap="round" />
            <defs>
              <linearGradient id="fgGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ff4d6a" />
                <stop offset="25%" stopColor="#ff8c42" />
                <stop offset="50%" stopColor="#ffc107" />
                <stop offset="75%" stopColor="#66bb6a" />
                <stop offset="100%" stopColor="#00c853" />
              </linearGradient>
            </defs>
            {/* Needle */}
            <line
              x1="50" y1="50"
              x2={50 + 35 * Math.cos((angle * Math.PI) / 180)}
              y2={50 + 35 * Math.sin((angle * Math.PI) / 180)}
              stroke="white" strokeWidth="2" strokeLinecap="round"
            />
            <circle cx="50" cy="50" r="3" fill="white" />
          </svg>
        </div>

        <div className="flex-1">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</span>
            <span className="text-xs font-semibold" style={{ color }}>{label}</span>
          </div>
          <p className="text-text-muted text-[10px] mt-1">
            {value <= 25 ? 'Extreme fear can signal buying opportunities.'
              : value <= 45 ? 'Fear in the market. Potential accumulation zone.'
              : value <= 55 ? 'Market is balanced between fear and greed.'
              : value <= 75 ? 'Greed rising. Be cautious with new entries.'
              : 'Extreme greed often precedes corrections.'}
          </p>
        </div>
      </div>

      {/* 7-day sparkline */}
      {history.length > 1 && (
        <div className="flex items-end gap-1 mt-3 h-8">
          {history.map((h, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
              <div
                className="w-full rounded-sm transition-all"
                style={{
                  height: `${Math.max((h.value / 100) * 28, 3)}px`,
                  backgroundColor: getColor(h.value),
                  opacity: i === history.length - 1 ? 1 : 0.5,
                }}
              />
              <span className="text-[7px] text-text-muted tabular-nums">{h.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
