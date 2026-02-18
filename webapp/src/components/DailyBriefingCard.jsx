import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../utils/api'

const SENTIMENT_BADGES = {
  bullish: { label: 'Bullish', color: 'text-accent-green bg-accent-green/10 border-accent-green/20' },
  bearish: { label: 'Bearish', color: 'text-accent-red bg-accent-red/10 border-accent-red/20' },
  neutral: { label: 'Neutral', color: 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/20' },
}

export default function DailyBriefingCard() {
  const navigate = useNavigate()
  const [briefing, setBriefing] = useState(null)

  useEffect(() => {
    api.getLatestBriefing()
      .then((res) => setBriefing(res?.briefing))
      .catch(() => {})
  }, [])

  if (!briefing) return null

  const badge = SENTIMENT_BADGES[briefing.overall_sentiment] || SENTIMENT_BADGES.neutral
  const change = briefing.btc_24h_change
  const changeColor = change > 0 ? 'text-accent-green' : change < 0 ? 'text-accent-red' : 'text-text-muted'

  // Truncate summary for card display
  const truncated = (briefing.summary_text || '').replace(/<[^>]*>/g, '').slice(0, 200)

  return (
    <div
      onClick={() => navigate('/briefing')}
      className="bg-bg-card rounded-2xl p-4 border border-white/5 cursor-pointer hover:border-accent-blue/20 transition-colors slide-up"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-text-primary font-semibold text-sm">Daily Briefing</h3>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badge.color}`}>
          {badge.label}
        </span>
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-text-primary font-bold text-lg">
          ${briefing.btc_price?.toLocaleString() || '—'}
        </span>
        <span className={`text-xs font-medium ${changeColor}`}>
          {change > 0 ? '+' : ''}{change?.toFixed(2)}%
        </span>
      </div>

      <p className="text-text-muted text-xs leading-relaxed line-clamp-3 mb-2">
        {truncated}...
      </p>

      <span className="text-accent-blue text-[10px] font-medium">Read Full Briefing →</span>
    </div>
  )
}
