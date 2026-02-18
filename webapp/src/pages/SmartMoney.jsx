import { useState, useEffect, useCallback } from 'react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'

const TYPE_FILTERS = ['all', 'whale', 'institutional', 'arbitrage']
const DIRECTION_FILTERS = ['all', 'bullish', 'bearish', 'neutral']

const TYPE_ICONS = {
  whale: '🐋',
  institutional: '🏛️',
  arbitrage: '💱',
}

const IMPACT_COLORS = {
  bullish: 'text-accent-green bg-accent-green/10',
  bearish: 'text-accent-red bg-accent-red/10',
  neutral: 'text-text-muted bg-bg-secondary',
}

function ScoreGauge({ score, label }) {
  // Score from -100 to +100, mapped to 0-100% for position
  const pct = Math.max(0, Math.min(100, (score + 100) / 2))
  const color = score > 20 ? 'text-accent-green' : score < -20 ? 'text-accent-red' : 'text-accent-yellow'

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">Smart Money Score</h3>
        <span className={`text-xs font-bold ${color}`}>{label}</span>
      </div>
      <div className="relative h-4 bg-gradient-to-r from-accent-red via-accent-yellow to-accent-green rounded-full overflow-hidden mb-1">
        <div
          className="absolute top-0 w-3 h-4 bg-white rounded-full border-2 border-bg-primary transition-all"
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-text-muted">
        <span>-100</span>
        <span className={`font-bold text-xs ${color}`}>{score > 0 ? '+' : ''}{score}</span>
        <span>+100</span>
      </div>
    </div>
  )
}

function EventCard({ event }) {
  const icon = TYPE_ICONS[event.type] || '📊'
  const impactStyle = IMPACT_COLORS[event.impact] || IMPACT_COLORS.neutral
  const amount = event.amount_usd
    ? `$${(event.amount_usd / 1e6).toFixed(1)}M`
    : event.amount_btc
    ? `${event.amount_btc.toLocaleString()} BTC`
    : null

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
      <div className="flex items-start gap-2">
        <span className="text-lg">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-text-primary text-xs font-semibold truncate">{event.title}</span>
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${impactStyle}`}>
              {event.impact}
            </span>
          </div>
          <p className="text-text-muted text-[10px] truncate">{event.description}</p>
          <div className="flex items-center gap-2 mt-1">
            {amount && <span className="text-accent-blue text-[10px] font-medium">{amount}</span>}
            {event.entity_name && <span className="text-text-muted text-[10px]">{event.entity_name}</span>}
            <span className="text-text-muted text-[10px] ml-auto">
              {event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SmartMoney() {
  const { tg } = useTelegram()
  const [score, setScore] = useState(null)
  const [events, setEvents] = useState([])
  const [isPremium, setIsPremium] = useState(false)
  const [typeFilter, setTypeFilter] = useState('all')
  const [dirFilter, setDirFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  const initData = tg?.initData

  const fetchData = useCallback(() => {
    const headers = initData ? { 'X-Telegram-Init-Data': initData } : {}
    Promise.all([
      api.getSmartMoneyScore(),
      api.getSmartMoneyFeed(initData, 24, 50, typeFilter, dirFilter),
    ])
      .then(([scoreData, feedData]) => {
        setScore(scoreData)
        setEvents(feedData?.events || [])
        setIsPremium(feedData?.is_premium || false)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [initData, typeFilter, dirFilter])

  useEffect(() => { fetchData() }, [fetchData])

  // Auto-refresh every 60s
  useEffect(() => {
    const iv = setInterval(fetchData, 60000)
    return () => clearInterval(iv)
  }, [fetchData])

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Smart Money</h1>

      {/* Score Gauge */}
      {score && <ScoreGauge score={score.score} label={score.label} />}

      {/* Component sub-scores */}
      {score && (
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-bg-card rounded-xl p-3 border border-white/5">
            <p className="text-text-muted text-[10px]">Whale Score</p>
            <p className={`font-bold text-lg ${score.whale_score > 0 ? 'text-accent-green' : score.whale_score < 0 ? 'text-accent-red' : 'text-text-primary'}`}>
              {score.whale_score > 0 ? '+' : ''}{score.whale_score}
            </p>
          </div>
          <div className="bg-bg-card rounded-xl p-3 border border-white/5">
            <p className="text-text-muted text-[10px]">Institutional Score</p>
            <p className={`font-bold text-lg ${score.institutional_score > 0 ? 'text-accent-green' : score.institutional_score < 0 ? 'text-accent-red' : 'text-text-primary'}`}>
              {score.institutional_score > 0 ? '+' : ''}{score.institutional_score}
            </p>
          </div>
        </div>
      )}

      {/* Type filter pills */}
      <div className="space-y-2">
        <div className="flex gap-1.5 overflow-x-auto scrollbar-hide">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setTypeFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold whitespace-nowrap transition-colors ${
                typeFilter === f ? 'bg-accent-blue text-white' : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {f === 'all' ? 'All' : `${TYPE_ICONS[f] || ''} ${f.charAt(0).toUpperCase() + f.slice(1)}`}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5">
          {DIRECTION_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setDirFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold whitespace-nowrap transition-colors ${
                dirFilter === f ? 'bg-accent-blue text-white' : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Event feed */}
      <div className="space-y-2">
        {events.length > 0 ? events.map((event) => (
          <EventCard key={event.id} event={event} />
        )) : !loading && (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">No events found</p>
          </div>
        )}
      </div>

      {/* Premium gate */}
      {!isPremium && events.length >= 5 && (
        <div className="bg-gradient-to-r from-accent-blue/10 to-purple-500/10 rounded-2xl p-4 border border-accent-blue/20 text-center">
          <p className="text-text-primary text-sm font-semibold mb-1">Unlock Full Feed</p>
          <p className="text-text-muted text-xs mb-3">Free users see 5 events. Premium gets the full real-time feed.</p>
          <button
            onClick={() => window.location.hash = '/subscription'}
            className="px-4 py-2 rounded-xl bg-accent-blue text-white text-xs font-semibold"
          >
            Upgrade to Premium
          </button>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  )
}
