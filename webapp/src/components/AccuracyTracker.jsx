import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Brush,
} from 'recharts'
import { api } from '../utils/api.js'
import { formatDate, formatPercent } from '../utils/format.js'

function TrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="bg-bg-card border border-text-muted/20 rounded-lg px-2.5 py-1.5 shadow-xl text-xs">
      <p className="text-text-secondary">{formatDate(d.date)}</p>
      <p className="text-text-primary font-medium">
        {d.accuracy?.toFixed(1)}%
      </p>
    </div>
  )
}

function ProgressBar({ label, value, total }) {
  const pct = total > 0 ? (value / total) * 100 : 0
  const barColor =
    pct >= 70 ? 'bg-accent-green' : pct >= 50 ? 'bg-accent-yellow' : 'bg-accent-red'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-text-secondary text-xs">{label}</span>
        <span className="text-text-primary text-xs font-medium">
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  )
}

export default function AccuracyTracker() {
  const { t } = useTranslation('dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAccuracy = useCallback(async () => {
    try {
      setError(null)
      const result = await api.getAccuracy(30)
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAccuracy()
    const interval = setInterval(fetchAccuracy, 300_000)
    return () => clearInterval(interval)
  }, [fetchAccuracy])

  // Normalize API data with safe defaults
  const overall = data?.overall ?? data?.accuracy ?? 0
  const totalPredictions = data?.total_predictions ?? data?.totalPredictions ?? data?.total ?? 0

  const byTimeframe = data?.by_timeframe ?? data?.byTimeframe ?? {}
  const timeframeEntries = [
    { label: '1h', data: byTimeframe['1h'] },
    { label: '4h', data: byTimeframe['4h'] },
    { label: '24h', data: byTimeframe['24h'] },
  ]

  const dailyTrend = data?.daily_trend ?? data?.dailyTrend ?? data?.trend ?? []

  const overallColor =
    overall >= 70
      ? 'text-accent-green'
      : overall >= 50
        ? 'text-accent-yellow'
        : 'text-accent-red'

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <h3 className="text-text-primary font-semibold text-sm mb-3">
        {t('accuracy.title')}
      </h3>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          <div className="flex flex-col items-center gap-1">
            <div className="h-10 w-24 bg-bg-secondary rounded" />
            <div className="h-3 w-32 bg-bg-secondary rounded" />
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-1">
                <div className="h-2 w-16 bg-bg-secondary rounded" />
                <div className="h-1.5 bg-bg-secondary rounded-full" />
              </div>
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('accuracy.title') })}</p>
          <button
            onClick={fetchAccuracy}
            className="text-accent-blue text-xs hover:underline"
          >
            {t('common:app.retry')}
          </button>
        </div>
      ) : (
        <>
          {/* Overall accuracy */}
          <div className="text-center mb-4">
            <p className={`text-4xl font-bold ${overallColor}`}>
              {overall.toFixed(1)}%
            </p>
            <p className="text-text-muted text-xs mt-1">
              {t('accuracy.basedOn', 'Based on {{count}} predictions', { count: totalPredictions.toLocaleString() })}
            </p>
          </div>

          {/* Timeframe breakdown */}
          <div className="space-y-2.5 mb-4">
            {timeframeEntries.map(({ label, data: tf }) => {
              const correct = tf?.correct ?? tf?.wins ?? 0
              const total = tf?.total ?? tf?.count ?? 0
              return (
                <ProgressBar
                  key={label}
                  label={label}
                  value={correct}
                  total={total}
                />
              )
            })}
          </div>

          {/* Daily accuracy trend */}
          {dailyTrend.length > 1 && (
            <div>
              <p className="text-text-secondary text-xs mb-2">
                {t('accuracy.trend30d')}
              </p>
              <div className="h-[120px] -mx-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={dailyTrend}
                    margin={{ top: 4, right: 8, left: 8, bottom: 0 }}
                  >
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#5a5a70', fontSize: 9 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(d) => formatDate(d)}
                      minTickGap={40}
                    />
                    <YAxis
                      domain={[0, 100]}
                      hide
                    />
                    <Tooltip content={<TrendTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="accuracy"
                      stroke="#4a9eff"
                      strokeWidth={1.5}
                      dot={false}
                      activeDot={{
                        r: 3,
                        fill: '#4a9eff',
                        stroke: '#0f0f14',
                        strokeWidth: 2,
                      }}
                    />
                    <Brush
                      dataKey="date"
                      height={16}
                      stroke="#4a9eff"
                      fill="#0f0f14"
                      tickFormatter={(d) => formatDate(d)}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
