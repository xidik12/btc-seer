import { useState, useEffect } from 'react'
import { api } from '../utils/api'

// Halving countdown (reused from HalvingWidget logic)
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

function formatBtc(n) {
  if (n == null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

function DonutRing({ percent }) {
  const r = 36
  const stroke = 6
  const circumference = 2 * Math.PI * r
  const offset = circumference - (percent / 100) * circumference

  return (
    <svg width="88" height="88" className="block">
      <circle
        cx="44" cy="44" r={r}
        fill="none" stroke="currentColor" strokeWidth={stroke}
        className="text-bg-hover"
      />
      <circle
        cx="44" cy="44" r={r}
        fill="none" strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-accent-green"
        style={{ transform: 'rotate(-90deg)', transformOrigin: 'center' }}
      />
      <text x="44" y="41" textAnchor="middle" className="fill-text-primary text-[11px] font-bold">
        {percent?.toFixed(1)}%
      </text>
      <text x="44" y="53" textAnchor="middle" className="fill-text-muted text-[8px]">
        mined
      </text>
    </svg>
  )
}

export default function SupplyWidget() {
  const [supply, setSupply] = useState(null)
  const [time, setTime] = useState(getTimeLeft)
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        const data = await api.getBtcSupply()
        if (mounted) setSupply(data)
      } catch {
        if (mounted) setError(true)
      }
    }
    load()
    const poll = setInterval(load, 5 * 60 * 1000) // every 5 min
    return () => { mounted = false; clearInterval(poll) }
  }, [])

  useEffect(() => {
    const tick = setInterval(() => setTime(getTimeLeft()), 1000)
    return () => clearInterval(tick)
  }, [])

  if (error && !supply) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm">Bitcoin Supply</h3>
        <p className="text-text-muted text-xs mt-2">Failed to load supply data</p>
      </div>
    )
  }

  const totalMined = supply?.total_mined ?? 19_800_000
  const remaining = supply?.remaining ?? 1_200_000
  const percentMined = supply?.percent_mined ?? 94.29
  const blockReward = supply?.block_reward ?? 3.125
  const btcPerDay = supply?.btc_mined_per_day ?? 450
  const schedule = supply?.supply_schedule ?? []

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-text-primary font-semibold text-sm">Bitcoin Supply</h3>
        <span className="text-text-muted text-[10px]">21M cap</span>
      </div>

      {/* Donut + Stats */}
      <div className="flex items-center gap-4">
        <DonutRing percent={percentMined} />
        <div className="flex-1 space-y-1.5">
          <div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider">Mined</div>
            <div className="text-text-primary text-sm font-bold">{formatBtc(totalMined)} BTC</div>
          </div>
          <div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider">Remaining</div>
            <div className="text-accent-orange text-sm font-bold">{formatBtc(remaining)} BTC</div>
          </div>
          <div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider">Daily Mining</div>
            <div className="text-text-secondary text-xs">~{btcPerDay} BTC/day ({blockReward} per block)</div>
          </div>
        </div>
      </div>

      {/* Halving Countdown */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">Next Halving</span>
          <span className="text-text-muted text-[10px]">Block {(supply?.next_halving_block ?? 1_050_000).toLocaleString()}</span>
        </div>
        <div className="flex gap-2 mb-2">
          {[
            { value: time.days, label: 'DAYS' },
            { value: time.hours, label: 'HRS' },
            { value: time.minutes, label: 'MIN' },
            { value: time.seconds, label: 'SEC' },
          ].map((t) => (
            <div key={t.label} className="flex-1 bg-bg-hover rounded-lg py-1.5 text-center">
              <div className="text-text-primary text-base font-bold tabular-nums">{String(t.value).padStart(2, '0')}</div>
              <div className="text-text-muted text-[7px] font-semibold">{t.label}</div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between text-[9px] text-text-muted mb-1">
          <span>Apr 2024</span>
          <span>{time.pct}% through cycle</span>
          <span>Apr 2028</span>
        </div>
        <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent-blue to-accent-green rounded-full transition-all"
            style={{ width: `${time.pct}%` }}
          />
        </div>
      </div>

      {/* Supply Milestones */}
      {schedule.length > 0 && (
        <div>
          <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-1.5">Supply Milestones</div>
          <div className="space-y-1">
            {schedule.map((s) => (
              <div key={s.year} className="flex items-center justify-between text-[10px]">
                <span className="text-text-secondary">{s.year}</span>
                <span className="text-text-muted">{s.reward} BTC/block</span>
                <span className="text-text-primary font-medium">{formatBtc(s.total_mined_approx)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-text-muted text-[10px]">
        Reward drops from {blockReward} to {blockReward / 2} BTC. Halvings historically precede bull runs within 12-18 months.
      </p>
    </div>
  )
}
