import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api.js'
import CardShareButton from './CardShareButton'

function getColor(value) {
  if (value <= 20) return '#ff4d6a'
  if (value <= 40) return '#ff8c42'
  if (value <= 60) return '#ffb800'
  if (value <= 80) return '#7dd87d'
  return '#00d68f'
}

function getLabel(value, t) {
  if (value <= 20) return t('fearGreed.extremeFear')
  if (value <= 40) return t('fearGreed.fear')
  if (value <= 60) return t('fearGreed.neutral')
  if (value <= 80) return t('fearGreed.greed')
  return t('fearGreed.extremeGreed')
}

function getTextClass(value) {
  if (value <= 20) return 'text-accent-red'
  if (value <= 40) return 'text-accent-orange'
  if (value <= 60) return 'text-accent-yellow'
  if (value <= 80) return 'text-accent-green'
  return 'text-accent-green'
}

function GaugeArc({ value, size = 160 }) {
  const ratio = Math.max(0, Math.min(1, value / 100))
  const strokeWidth = 10
  const radius = (size - strokeWidth) / 2
  const cx = size / 2
  const cy = size / 2

  const startAngle = Math.PI
  const endAngle = 0

  const bgStartX = cx + radius * Math.cos(startAngle)
  const bgStartY = cy - radius * Math.sin(startAngle)
  const bgEndX = cx + radius * Math.cos(endAngle)
  const bgEndY = cy - radius * Math.sin(endAngle)
  const bgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 0 1 ${bgEndX} ${bgEndY}`

  const fillAngle = Math.PI - ratio * Math.PI
  const fillEndX = cx + radius * Math.cos(fillAngle)
  const fillEndY = cy - radius * Math.sin(fillAngle)
  const largeArc = ratio > 0.5 ? 1 : 0
  const fgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 ${largeArc} 1 ${fillEndX} ${fillEndY}`

  const needleLength = radius - 8
  const needleX = cx + needleLength * Math.cos(fillAngle)
  const needleY = cy - needleLength * Math.sin(fillAngle)

  const color = getColor(value)

  return (
    <svg
      width={size}
      height={size / 2 + 16}
      viewBox={`0 0 ${size} ${size / 2 + 16}`}
      className="mx-auto"
    >
      <defs>
        <linearGradient id="fg-gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ff4d6a" />
          <stop offset="25%" stopColor="#ff8c42" />
          <stop offset="50%" stopColor="#ffb800" />
          <stop offset="75%" stopColor="#7dd87d" />
          <stop offset="100%" stopColor="#00d68f" />
        </linearGradient>
      </defs>

      <path d={bgPath} fill="none" stroke="#1a1a24" strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d={bgPath} fill="none" stroke="url(#fg-gauge-gradient)" strokeWidth={strokeWidth} strokeLinecap="round" opacity={0.15} />

      {ratio > 0.005 && (
        <path d={fgPath} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" className="transition-all duration-700" />
      )}

      <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="#ffffff" strokeWidth={2} strokeLinecap="round" className="transition-all duration-700" />
      <circle cx={cx} cy={cy} r={3.5} fill="#ffffff" />

      <text x={strokeWidth / 2 + 2} y={cy + 14} fill="#5a5a70" fontSize="10" textAnchor="start">0</text>
      <text x={size - strokeWidth / 2 - 2} y={cy + 14} fill="#5a5a70" fontSize="10" textAnchor="end">100</text>
    </svg>
  )
}

export default function FearGreedWidget() {
  const { t } = useTranslation('dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const cardRef = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getFearGreed(7)
      setData(res)
      setError(null)
    } catch (err) {
      setError(err.message)
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
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 animate-pulse">
        <div className="h-5 w-36 bg-bg-hover rounded mb-4" />
        <div className="h-20 w-36 bg-bg-hover rounded mx-auto mb-3" />
        <div className="h-6 w-24 bg-bg-hover rounded mx-auto" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/20">
        <h3 className="text-text-primary text-sm font-semibold mb-2">{t('fearGreed.title')}</h3>
        <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('fearGreed.title') })}</p>
        <button onClick={fetchData} className="text-accent-blue text-xs mt-1 underline">{t('common:app.retry')}</button>
      </div>
    )
  }

  const current = data?.current
  if (!current) return null

  const value = Math.max(0, Math.min(100, Math.round(current.value)))
  const label = current.label || getLabel(value, t)
  const color = getColor(value)
  const textClass = getTextClass(value)
  const history = (data?.history || []).slice(0, 7).reverse()

  return (
    <div ref={cardRef} className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-text-primary text-sm font-semibold">{t('fearGreed.title')}</h3>
        <CardShareButton cardRef={cardRef} label="Fear & Greed" filename="fear-greed.png" />
      </div>

      <GaugeArc value={value} />

      <div className="text-center -mt-1">
        <p className={`text-3xl font-bold tabular-nums ${textClass}`}>{value}</p>
        <p className={`text-sm font-medium mt-0.5 ${textClass}`}>{label}</p>
      </div>

      <p className="text-text-muted text-xs mt-2 text-center">
        {value <= 25 ? t('fearGreed.tipExtremeFear')
          : value <= 45 ? t('fearGreed.tipFear')
          : value <= 55 ? t('fearGreed.tipNeutral')
          : value <= 75 ? t('fearGreed.tipGreed')
          : t('fearGreed.tipExtremeGreed')}
      </p>

      {history.length > 1 && (
        <div className="mt-3">
          <p className="text-text-muted text-xs font-medium mb-1.5">{t('fearGreed.last7Days')}</p>
          <div className="flex items-end gap-1 h-8">
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
        </div>
      )}
    </div>
  )
}
