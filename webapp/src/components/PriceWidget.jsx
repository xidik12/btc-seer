import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from 'recharts'
import CardShareButton from './CardShareButton'
import { api } from '../utils/api.js'
import {
  formatPrice,
  formatPercent,
  formatNumber,
  formatTimeAgo,
} from '../utils/format.js'

const POLL_INTERVAL = 120_000

const TIMEFRAMES = [
  { value: '1m', label: '1M', name: '1 Minute' },
  { value: '5m', label: '5M', name: '5 Minutes' },
  { value: '15m', label: '15M', name: '15 Minutes' },
  { value: '1h', label: '1H', name: '1 Hour' },
  { value: '4h', label: '4H', name: '4 Hours' },
  { value: '1d', label: '1D', name: '1 Day' },
  { value: '1w', label: '1W', name: '1 Week' },
  { value: '1mo', label: '1M', name: '1 Month' },
  { value: 'all', label: 'ALL', name: 'All Time' },
]

export default function PriceWidget() {
  const { t } = useTranslation('dashboard')
  const [selectedTimeframe, setSelectedTimeframe] = useState('1d')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const cardRef = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getPriceStats(selectedTimeframe)
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedTimeframe])

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
        <div className="h-8 w-full bg-bg-hover rounded mb-3" />
        <div className="h-32 w-full bg-bg-hover rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('priceWidget.title') })}</p>
        <button
          onClick={fetchData}
          className="text-accent-blue text-xs mt-1 underline"
        >
          {t('common:app.retry')}
        </button>
      </div>
    )
  }

  const currentPrice = stats?.current_price ?? 0
  const change = stats?.change ?? 0
  const changePercent = stats?.change_pct ?? 0
  const high = stats?.high ?? 0
  const low = stats?.low ?? 0
  const volume = stats?.volume ?? 0
  const isPositive = changePercent >= 0
  const changeColor = isPositive ? 'text-accent-green' : 'text-accent-red'
  const sparklineColor = isPositive ? '#00d68f' : '#ff4d6a'
  const updatedAt = stats?.timestamp
  const timeframeName = TIMEFRAMES.find(tf => tf.value === selectedTimeframe)?.name || '1 Day'

  const chartData = (stats?.candles ?? []).map((c) => ({
    timestamp: c.timestamp,
    close: c.close ?? 0,
  }))

  return (
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-text-secondary text-xs font-medium uppercase tracking-wide">
            {t('priceWidget.title')}
          </span>
          <div className="flex items-center gap-1">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isPositive ? 'bg-accent-green' : 'bg-accent-red'
              } pulse-glow`}
            />
            <span className="text-text-muted text-xs">{t('common:app.live')}</span>
          </div>
          <CardShareButton cardRef={cardRef} label="BTC Price" filename="btc-price.png" />
        </div>
        {updatedAt && (
          <span className="text-text-muted text-xs">
            {formatTimeAgo(updatedAt)}
          </span>
        )}
      </div>

      {/* Price & Change */}
      <div className="mb-4">
        <p className="text-text-primary text-3xl font-bold leading-tight mb-2 gold-glow">
          {formatPrice(currentPrice)}
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${changeColor}`}>
              {formatPercent(changePercent)}
            </span>
            <span className={`text-xs ${changeColor}`}>
              {isPositive ? '+' : ''}
              {formatPrice(change)}
            </span>
          </div>
          <span className="text-text-muted text-xs">{timeframeName}</span>
        </div>
      </div>

      {/* High / Low */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-bg-hover/50 rounded-lg px-3 py-2">
          <div className="text-text-muted text-xs uppercase tracking-wide mb-1">{t('common:price.high')}</div>
          <div className="text-text-primary text-sm font-semibold">{formatPrice(high)}</div>
        </div>
        <div className="bg-bg-hover/50 rounded-lg px-3 py-2">
          <div className="text-text-muted text-xs uppercase tracking-wide mb-1">{t('common:price.low')}</div>
          <div className="text-text-primary text-sm font-semibold">{formatPrice(low)}</div>
        </div>
      </div>

      {/* Timeframe Selector */}
      <div className="flex gap-1 mb-4 overflow-x-auto scrollbar-hide">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf.value}
            onClick={() => setSelectedTimeframe(tf.value)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
              selectedTimeframe === tf.value
                ? 'bg-accent-blue text-white'
                : 'bg-bg-hover text-text-secondary hover:bg-bg-hover/80 hover:text-text-primary'
            }`}
          >
            {tf.label}
          </button>
        ))}
      </div>

      {/* Chart */}
      {chartData.length > 1 && (
        <div className="h-32 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <YAxis domain={['dataMin', 'dataMax']} hide />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-bg-card border border-bg-hover rounded-lg px-3 py-2 shadow-lg">
                        <p className="text-text-primary text-sm font-semibold">
                          {formatPrice(payload[0].value)}
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke={sparklineColor}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Volume */}
      <div className="mt-3 pt-3 border-t border-bg-hover">
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-xs">{t('common:price.volume')}</span>
          <span className="text-text-primary text-xs font-semibold">
            {formatNumber(volume)} BTC
          </span>
        </div>
      </div>
    </div>
  )
}
