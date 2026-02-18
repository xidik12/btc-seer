import { useState, useEffect, useCallback, memo } from 'react'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'
import { formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/whales', labelKey: 'common:link.whales' },
  { path: '/smart-money', labelKey: 'common:link.smartMoney' },
  { path: '/arbitrage', labelKey: 'common:link.arbitrage' },
  { path: '/events', labelKey: 'common:link.events' },
]

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

const SEVERITY_COLORS = {
  10: 'bg-accent-red text-white',
  9: 'bg-accent-red/80 text-white',
  8: 'bg-accent-orange/80 text-white',
  7: 'bg-accent-orange/60 text-white',
  6: 'bg-accent-yellow/80 text-bg-primary',
  5: 'bg-accent-yellow/60 text-bg-primary',
  4: 'bg-accent-blue/60 text-white',
  3: 'bg-accent-blue/40 text-white',
  2: 'bg-bg-secondary text-text-muted',
  1: 'bg-bg-secondary text-text-muted',
}

// ── Loading Skeleton ────────────────────────────────────────────────────────

function SmartMoneySkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20 animate-pulse">
      {/* Score gauge skeleton */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
        <div className="h-4 bg-bg-hover rounded-full mb-2" />
        <div className="h-3 w-16 bg-bg-hover rounded mx-auto" />
      </div>
      {/* Sub-scores skeleton */}
      <div className="grid grid-cols-2 gap-2">
        {[0, 1].map((i) => (
          <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5">
            <div className="h-2.5 w-20 bg-bg-hover rounded mb-2" />
            <div className="h-5 w-10 bg-bg-hover rounded" />
          </div>
        ))}
      </div>
      {/* Flow bars skeleton */}
      <div className="grid grid-cols-2 gap-2">
        {[0, 1].map((i) => (
          <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5">
            <div className="h-2.5 w-20 bg-bg-hover rounded mb-2" />
            <div className="h-3 bg-bg-hover rounded-full mb-1" />
            <div className="h-2 w-full bg-bg-hover rounded" />
          </div>
        ))}
      </div>
      {/* Event cards skeleton */}
      {[0, 1, 2].map((i) => (
        <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5">
          <div className="flex gap-2">
            <div className="w-6 h-6 bg-bg-hover rounded" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-3/4 bg-bg-hover rounded" />
              <div className="h-2.5 w-1/2 bg-bg-hover rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Score Gauge ─────────────────────────────────────────────────────────────

const ScoreGauge = memo(function ScoreGauge({ score, label, t }) {
  const pct = Math.max(0, Math.min(100, (score + 100) / 2))
  const color = score > 20 ? 'text-accent-green' : score < -20 ? 'text-accent-red' : 'text-accent-yellow'

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">{t('smartMoney.score')}</h3>
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
})

// ── Flow Bar ────────────────────────────────────────────────────────────────

function FlowBar({ label, bullish, bearish }) {
  const total = (bullish || 0) + (bearish || 0)
  if (!total) return null
  const bullPct = ((bullish || 0) / total * 100).toFixed(0)
  const bearPct = ((bearish || 0) / total * 100).toFixed(0)

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5">
      <p className="text-text-muted text-[10px] mb-2">{label}</p>
      <div className="flex rounded-full overflow-hidden h-3">
        {bullish > 0 && (
          <div className="bg-accent-green/70 transition-all" style={{ width: `${bullPct}%` }} />
        )}
        {bearish > 0 && (
          <div className="bg-accent-red/70 transition-all" style={{ width: `${bearPct}%` }} />
        )}
      </div>
      <div className="flex justify-between text-[9px] text-text-muted mt-1">
        <span className="text-accent-green">{bullPct}%</span>
        <span className="text-accent-red">{bearPct}%</span>
      </div>
    </div>
  )
}

// ── Refresh Timer ───────────────────────────────────────────────────────────

function RefreshTimer({ lastUpdate, t }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!lastUpdate) return
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - lastUpdate) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [lastUpdate])

  if (!lastUpdate) return null

  return (
    <span className="text-[9px] text-text-muted">
      {t('smartMoney.lastUpdate', { seconds: elapsed })}
    </span>
  )
}

// ── Event Card ──────────────────────────────────────────────────────────────

const EventCard = memo(function EventCard({ event, t }) {
  const icon = TYPE_ICONS[event.type] || '📊'
  const impactStyle = IMPACT_COLORS[event.impact] || IMPACT_COLORS.neutral
  const amount = event.amount_usd
    ? `$${(event.amount_usd / 1e6).toFixed(1)}M`
    : event.amount_btc
    ? `${event.amount_btc.toLocaleString()} BTC`
    : null

  const severity = event.severity
  const sevColor = severity ? (SEVERITY_COLORS[severity] || SEVERITY_COLORS[1]) : null

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
      <div className="flex items-start gap-2">
        <span className="text-lg">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-text-primary text-xs font-semibold truncate">{event.title}</span>
            {severity != null && (
              <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${sevColor}`}>
                {t('smartMoney.severity', { level: severity })}
              </span>
            )}
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${impactStyle}`}>
              {event.impact}
            </span>
          </div>
          <p className="text-text-muted text-[10px] truncate">{event.description}</p>
          <div className="flex items-center gap-2 mt-1">
            {amount && <span className="text-accent-blue text-[10px] font-medium">{amount}</span>}
            {event.entity_name && <span className="text-text-muted text-[10px]">{event.entity_name}</span>}
            <span className="text-text-muted text-[10px] ml-auto">
              {event.timestamp ? formatTimeAgo(event.timestamp) : ''}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
})

// ── Main Component ──────────────────────────────────────────────────────────

export default function SmartMoney() {
  const { t } = useTranslation('common')
  const { tg } = useTelegram()
  const [score, setScore] = useState(null)
  const [events, setEvents] = useState([])
  const [isPremium, setIsPremium] = useState(false)
  const [typeFilter, setTypeFilter] = useState('all')
  const [dirFilter, setDirFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  const initData = tg?.initData

  const tabs = MARKET_TABS.map((tab) => ({ ...tab, label: t(tab.labelKey) }))

  const fetchData = useCallback(() => {
    setError(null)
    Promise.all([
      api.getSmartMoneyScore(),
      api.getSmartMoneyFeed(initData, 24, 50, typeFilter, dirFilter),
    ])
      .then(([scoreData, feedData]) => {
        setScore(scoreData)
        setEvents(feedData?.events || [])
        setIsPremium(feedData?.is_premium || false)
        setLastUpdate(Date.now())
      })
      .catch((err) => {
        setError(err.message || t('app.error'))
      })
      .finally(() => setLoading(false))
  }, [initData, typeFilter, dirFilter, t])

  useEffect(() => { fetchData() }, [fetchData])

  // Auto-refresh every 60s
  useEffect(() => {
    const iv = setInterval(fetchData, 60000)
    return () => clearInterval(iv)
  }, [fetchData])

  const typeFilterKeys = { all: 'smartMoney.all', whale: 'smartMoney.whale', institutional: 'smartMoney.institutional', arbitrage: 'smartMoney.arbitrage' }
  const dirFilterKeys = { all: 'smartMoney.all', bullish: 'smartMoney.bullish', bearish: 'smartMoney.bearish', neutral: 'smartMoney.neutral' }

  if (loading && !score && !events.length) {
    return (
      <div className="px-4 pt-4 pb-20">
        <SubTabBar tabs={tabs} />
        <SmartMoneySkeleton />
      </div>
    )
  }

  if (error && !score) {
    return (
      <div className="px-4 pt-4 pb-20">
        <SubTabBar tabs={tabs} />
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center mt-4">
          <p className="text-accent-red text-sm mb-3">{error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 rounded-xl bg-accent-blue text-white text-xs font-semibold"
          >
            {t('app.retry')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <SubTabBar tabs={tabs} />

      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">{t('smartMoney.title')}</h1>
        <RefreshTimer lastUpdate={lastUpdate} t={t} />
      </div>

      {/* Score Gauge */}
      {score && <ScoreGauge score={score.score} label={score.label} t={t} />}

      {/* Component sub-scores + flow bars */}
      {score && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-bg-card rounded-xl p-3 border border-white/5">
              <p className="text-text-muted text-[10px]">{t('smartMoney.whaleScore')}</p>
              <p className={`font-bold text-lg ${score.whale_score > 0 ? 'text-accent-green' : score.whale_score < 0 ? 'text-accent-red' : 'text-text-primary'}`}>
                {score.whale_score > 0 ? '+' : ''}{score.whale_score}
              </p>
            </div>
            <div className="bg-bg-card rounded-xl p-3 border border-white/5">
              <p className="text-text-muted text-[10px]">{t('smartMoney.instScore')}</p>
              <p className={`font-bold text-lg ${score.institutional_score > 0 ? 'text-accent-green' : score.institutional_score < 0 ? 'text-accent-red' : 'text-text-primary'}`}>
                {score.institutional_score > 0 ? '+' : ''}{score.institutional_score}
              </p>
            </div>
          </div>

          {/* Flow Bars */}
          <div className="grid grid-cols-2 gap-2">
            <FlowBar
              label={t('smartMoney.whaleFlow')}
              bullish={score.whale_bullish_usd}
              bearish={score.whale_bearish_usd}
            />
            <FlowBar
              label={t('smartMoney.instFlow')}
              bullish={score.institutional_buy_btc}
              bearish={score.institutional_sell_btc}
            />
          </div>
        </>
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
              {f !== 'all' && `${TYPE_ICONS[f] || ''} `}{t(typeFilterKeys[f])}
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
              {t(dirFilterKeys[f])}
            </button>
          ))}
        </div>
      </div>

      {/* Event feed */}
      <div className="space-y-2">
        {events.length > 0 ? events.map((event) => (
          <EventCard key={event.id} event={event} t={t} />
        )) : !loading && (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">{t('smartMoney.noEvents')}</p>
          </div>
        )}
      </div>

      {/* Premium gate */}
      {!isPremium && events.length >= 5 && (
        <div className="bg-gradient-to-r from-accent-blue/10 to-purple-500/10 rounded-2xl p-4 border border-accent-blue/20 text-center">
          <p className="text-text-primary text-sm font-semibold mb-1">{t('smartMoney.unlockFeed')}</p>
          <p className="text-text-muted text-xs mb-3">{t('smartMoney.premiumDesc')}</p>
          <button
            onClick={() => window.location.hash = '/subscription'}
            className="px-4 py-2 rounded-xl bg-accent-blue text-white text-xs font-semibold"
          >
            {t('smartMoney.upgradePremium')}
          </button>
        </div>
      )}
    </div>
  )
}
