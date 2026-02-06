import { useState, useEffect, useCallback } from 'react'
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts'
import { api } from '../utils/api.js'
import {
  formatPrice,
  formatPercent,
  formatNumber,
  formatTime,
  formatTimeAgo,
  getDirectionColor,
  getActionColor,
  getActionBg,
} from '../utils/format.js'

const POLL_INTERVAL = 30_000

export default function PriceWidget() {
  const [price, setPrice] = useState(null)
  const [candles, setCandles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [priceData, candleData] = await Promise.all([
        api.getCurrentPrice(),
        api.getCandles(24),
      ])
      setPrice(priceData)
      setCandles(Array.isArray(candleData) ? candleData : candleData?.candles ?? [])
      setError(null)
    } catch (err) {
      setError(err.message)
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
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-6 w-32 bg-bg-hover rounded mb-2" />
        <div className="h-10 w-48 bg-bg-hover rounded mb-3" />
        <div className="h-16 w-full bg-bg-hover rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">Failed to load price data</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  const currentPrice = price?.price ?? 0
  const change24h = price?.change_24h ?? 0
  const changePercent24h = price?.change_percent_24h ?? 0
  const isPositive = changePercent24h >= 0
  const changeColor = isPositive ? 'text-accent-green' : 'text-accent-red'
  const sparklineColor = isPositive ? '#00d68f' : '#ff4d6a'
  const updatedAt = price?.updated_at ?? price?.timestamp

  const sparklineData = candles.map((c) => ({
    close: c.close ?? c.price ?? 0,
  }))

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-1">
        <span className="text-text-secondary text-xs font-medium uppercase tracking-wide">
          BTC / USD
        </span>
        {updatedAt && (
          <span className="text-text-muted text-xs">
            {formatTimeAgo(updatedAt)}
          </span>
        )}
      </div>

      <div className="flex items-end justify-between mb-3">
        <div>
          <p className="text-text-primary text-3xl font-bold leading-tight">
            {formatPrice(currentPrice)}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-sm font-semibold ${changeColor}`}>
              {formatPercent(changePercent24h)}
            </span>
            <span className={`text-xs ${changeColor}`}>
              {isPositive ? '+' : ''}
              {formatPrice(change24h)}
            </span>
            <span className="text-text-muted text-xs">24h</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              isPositive ? 'bg-accent-green' : 'bg-accent-red'
            } pulse-glow`}
          />
          <span className="text-text-muted text-[10px]">LIVE</span>
        </div>
      </div>

      {sparklineData.length > 1 && (
        <div className="h-16 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <YAxis domain={['dataMin', 'dataMax']} hide />
              <Line
                type="monotone"
                dataKey="close"
                stroke={sparklineColor}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
