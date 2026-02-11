import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatTimeAgo } from '../utils/format'

const IMPACT_COLORS = {
  very_high: 'bg-accent-red/20 text-accent-red border-accent-red/30',
  high: 'bg-accent-yellow/20 text-accent-yellow border-accent-yellow/30',
  medium: 'bg-accent-blue/20 text-accent-blue border-accent-blue/30',
}

const DIRECTION_COLORS = {
  bullish: 'text-accent-green',
  bearish: 'text-accent-red',
  mixed: 'text-accent-yellow',
  neutral: 'text-text-secondary',
}

const DIRECTION_ARROWS = {
  bullish: '\u2191',
  bearish: '\u2193',
  mixed: '\u2195',
  neutral: '\u2022',
}

const CATEGORY_COLORS = {
  macro: '#3b82f6',
  regulation: '#a855f7',
  adoption: '#22c55e',
  institutional: '#06b6d4',
  halving: '#f59e0b',
  geopolitical: '#ef4444',
}

function EventCard({ event, t, isExpanded, onToggle }) {
  const impactKey = event.impact === 'very_high' ? 'impactVeryHigh'
    : event.impact === 'high' ? 'impactHigh' : 'impactMedium'

  return (
    <div className="bg-bg-card rounded-xl border border-white/5 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left p-3 hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-start gap-2.5">
          <div
            className="w-1 self-stretch rounded-full shrink-0"
            style={{ backgroundColor: CATEGORY_COLORS[event.category] || '#666' }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1 flex-wrap">
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${IMPACT_COLORS[event.impact] || IMPACT_COLORS.medium}`}>
                {t(`powerLaw.upcoming.${impactKey}`)}
              </span>
              <span className={`text-[10px] font-medium ${DIRECTION_COLORS[event.direction]}`}>
                {DIRECTION_ARROWS[event.direction]} {t(`powerLaw.upcoming.${event.direction}`)}
              </span>
            </div>
            <p className="text-sm text-text-primary font-medium leading-snug">
              {event.title}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-text-muted">{event.date}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-text-secondary">
                {t(`powerLaw.upcoming.${event.status}`)}
              </span>
            </div>
          </div>
          <svg
            className={`w-4 h-4 text-text-muted shrink-0 mt-1 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>
      {isExpanded && (
        <div className="px-3 pb-3 ml-3.5 border-t border-white/5 pt-2">
          <p className="text-xs text-text-secondary leading-relaxed mb-2">
            {event.description}
          </p>
          <div className="bg-white/5 rounded-lg p-2.5">
            <p className="text-[10px] text-accent-yellow font-medium mb-0.5">
              {t('powerLaw.upcoming.whyMatters')}
            </p>
            <p className="text-xs text-text-primary leading-relaxed">
              {event.why_matters}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function News() {
  const { t } = useTranslation('market')
  const [news, setNews] = useState([])
  const [sentiment, setSentiment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(true)
  const [expandedEvent, setExpandedEvent] = useState(null)
  const [showAllEvents, setShowAllEvents] = useState(false)

  const loadNews = async () => {
    setLoading(true)
    setError(null)
    try {
      const [newsData, sentData] = await Promise.all([
        api.getLatestNews(50),
        api.getNewsSentiment(24),
      ])
      setNews(newsData.news || [])
      setSentiment(sentData)
    } catch (err) {
      setError(err.message || t('news.noNews'))
      setNews([])
    }
    setLoading(false)
  }

  const loadEvents = async () => {
    setEventsLoading(true)
    try {
      const data = await api.getUpcomingEvents()
      setEvents(data.events || [])
    } catch {
      setEvents([])
    }
    setEventsLoading(false)
  }

  useEffect(() => {
    loadNews()
    loadEvents()
  }, [])

  const visibleEvents = showAllEvents ? events : events.slice(0, 3)

  function getSentimentDot(score) {
    const color = score == null ? '#5a5a70' : score > 0.1 ? '#00d68f' : score < -0.1 ? '#ff4d6a' : '#ffc107'
    return (
      <svg className="w-2.5 h-2.5" viewBox="0 0 10 10">
        <circle cx="5" cy="5" r="4.5" fill={color} />
      </svg>
    )
  }

  return (
    <div className="px-4 pt-4">
      <h1 className="text-lg font-bold mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        {t('news.title')}
      </h1>

      {sentiment && (
        <div className="bg-bg-card rounded-xl p-4 mb-4 border border-white/5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">{t('news.sentimentOverview')}</h3>
          <div className="flex justify-between text-sm">
            <span className="text-accent-green">
              {t('news.bullish')}: {sentiment.bullish_pct?.toFixed(0)}%
            </span>
            <span className="text-accent-yellow">
              {t('news.neutral')}: {(100 - (sentiment.bullish_pct || 0) - (sentiment.bearish_pct || 0)).toFixed(0)}%
            </span>
            <span className="text-accent-red">
              {t('news.bearish')}: {sentiment.bearish_pct?.toFixed(0)}%
            </span>
          </div>
          <div className="flex mt-2 rounded-full overflow-hidden h-2">
            <div
              className="bg-accent-green"
              style={{ width: `${sentiment.bullish_pct || 0}%` }}
            />
            <div
              className="bg-accent-yellow"
              style={{ width: `${100 - (sentiment.bullish_pct || 0) - (sentiment.bearish_pct || 0)}%` }}
            />
            <div
              className="bg-accent-red"
              style={{ width: `${sentiment.bearish_pct || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Upcoming Events Section */}
      {!eventsLoading && events.length > 0 && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-text-secondary mb-2 flex items-center gap-1.5">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {t('powerLaw.upcoming.title')}
          </h2>
          <div className="space-y-2">
            {visibleEvents.map((ev) => (
              <EventCard
                key={ev.id}
                event={ev}
                t={t}
                isExpanded={expandedEvent === ev.id}
                onToggle={() => setExpandedEvent(expandedEvent === ev.id ? null : ev.id)}
              />
            ))}
          </div>
          {events.length > 3 && (
            <button
              onClick={() => setShowAllEvents(!showAllEvents)}
              className="w-full mt-2 text-xs text-accent-blue hover:underline py-1"
            >
              {showAllEvents
                ? t('powerLaw.upcoming.showLess', 'Show less')
                : t('powerLaw.upcoming.showAll', 'Show all {{count}} events', { count: events.length })}
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 skeleton rounded-full shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 skeleton w-full" />
                  <div className="h-4 skeleton w-3/4" />
                  <div className="flex gap-2">
                    <div className="h-3 skeleton w-16" />
                    <div className="h-3 skeleton w-12" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{t('news.noNews')}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={loadNews} className="text-accent-blue text-xs hover:underline">{t('app.retry', { ns: 'common' })}</button>
        </div>
      ) : news.length === 0 ? (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <div className="flex justify-center mb-2">
            <svg className="w-8 h-8 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm font-medium">{t('news.noNews')}</p>
          <button onClick={loadNews} className="text-accent-blue text-xs mt-3 hover:underline">{t('app.retry', { ns: 'common' })}</button>
        </div>
      ) : (
        <div className="space-y-2">
          {news.map((n, i) => (
            <button
              key={i}
              onClick={() => n.url && window.open(n.url, '_blank')}
              className="w-full text-left bg-bg-card rounded-xl p-3 border border-white/5 hover:bg-bg-hover transition-colors slide-up"
            >
              <div className="flex items-start gap-2">
                <span className="mt-1 shrink-0">{getSentimentDot(n.sentiment_score)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary leading-snug line-clamp-2">
                    {n.title}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-accent-blue uppercase font-medium">
                      {n.source}
                    </span>
                    <span className="text-[10px] text-text-muted">
                      {formatTimeAgo(n.timestamp)}
                    </span>
                    {n.sentiment_score != null && (
                      <span className={`text-[10px] ${
                        n.sentiment_score > 0.1
                          ? 'text-accent-green'
                          : n.sentiment_score < -0.1
                          ? 'text-accent-red'
                          : 'text-text-muted'
                      }`}>
                        {n.sentiment_score > 0 ? '+' : ''}{n.sentiment_score?.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
