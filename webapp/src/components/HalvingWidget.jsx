import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

// Next halving: block 1,050,000 — estimated April 23, 2028
// Current avg block time: ~10 minutes
const HALVING_BLOCK = 1_050_000
const CURRENT_BLOCK_ESTIMATE = 881_000 // approximate as of Feb 2026
const HALVING_DATE = new Date('2028-04-23T00:00:00Z')
const LAST_HALVING_DATE = new Date('2024-04-19T00:00:00Z')

function getTimeLeft() {
  const now = new Date()
  const diff = HALVING_DATE - now
  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, pct: 100 }

  const totalCycle = HALVING_DATE - LAST_HALVING_DATE
  const elapsed = now - LAST_HALVING_DATE
  const pct = Math.min((elapsed / totalCycle) * 100, 100)

  return {
    days: Math.floor(diff / 86400000),
    hours: Math.floor((diff % 86400000) / 3600000),
    minutes: Math.floor((diff % 3600000) / 60000),
    seconds: Math.floor((diff % 60000) / 1000),
    pct: Math.round(pct * 10) / 10,
  }
}

export default function HalvingWidget() {
  const { t } = useTranslation('dashboard')
  const [time, setTime] = useState(getTimeLeft)

  useEffect(() => {
    const interval = setInterval(() => setTime(getTimeLeft()), 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-text-primary font-semibold text-sm">{t('halving.title')}</h3>
        <span className="text-text-muted text-[10px]">{t('halving.block', { number: HALVING_BLOCK.toLocaleString() })}</span>
      </div>

      {/* Countdown */}
      <div className="flex gap-2 mb-3">
        {[
          { value: time.days, label: t('halving.days').toUpperCase().slice(0, 4) },
          { value: time.hours, label: t('halving.hours').toUpperCase().slice(0, 3) },
          { value: time.minutes, label: t('halving.minutes').toUpperCase().slice(0, 3) },
          { value: time.seconds, label: t('halving.seconds').toUpperCase().slice(0, 3) },
        ].map((item) => (
          <div key={item.label} className="flex-1 bg-bg-hover rounded-lg py-2 text-center">
            <div className="text-text-primary text-lg font-bold tabular-nums">{String(item.value).padStart(2, '0')}</div>
            <div className="text-text-muted text-[8px] font-semibold">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-[9px] text-text-muted mb-1">
          <span>Apr 2024 ({t('halving.last')})</span>
          <span>{time.pct}% {t('halving.cycleProgress').toLowerCase()}</span>
          <span>Apr 2028 ({t('halving.next')})</span>
        </div>
        <div className="h-2 bg-bg-hover rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent-blue to-accent-green rounded-full transition-all"
            style={{ width: `${time.pct}%` }}
          />
        </div>
      </div>

      <p className="text-text-muted text-[10px]">
        {t('halving.rewardDrop', { from: '3.125', to: '1.5625' })}. {t('halving.historicalNote')}
      </p>
    </div>
  )
}
