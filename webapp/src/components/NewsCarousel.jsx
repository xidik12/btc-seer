import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api.js'
import { formatTimeAgo } from '../utils/format.js'

const SOURCE_COLORS = {
  coindesk: '#1a6dff',
  cointelegraph: '#222',
  bitcoin_magazine: '#f7931a',
  cryptopanic: '#4a90d9',
  reddit: '#ff4500',
  binance: '#f0b90b',
  newsbtc: '#00c4b3',
  bitcoinist: '#f7931a',
  cryptoslate: '#2c3e50',
  utoday: '#5856d6',
  beincrypto: '#5e35b1',
  ambcrypto: '#1565c0',
  cryptonews: '#333',
  google_news: '#4285f4',
  cnbc: '#005e99',
  yahoo: '#7b1fa2',
  default: '#4a4a66',
}

function getSourceColor(source) {
  if (!source) return SOURCE_COLORS.default
  const key = source.toLowerCase()
  for (const [k, v] of Object.entries(SOURCE_COLORS)) {
    if (key.includes(k)) return v
  }
  return SOURCE_COLORS.default
}

function getSentimentLabel(score, t) {
  if (score == null) return null
  if (score > 0.3) return { text: t('common:direction.bullish'), cls: 'bg-accent-green/15 text-accent-green' }
  if (score < -0.3) return { text: t('common:direction.bearish'), cls: 'bg-accent-red/15 text-accent-red' }
  if (score > 0.1) return { text: t('news.positive', 'Positive'), cls: 'bg-accent-green/10 text-accent-green/80' }
  if (score < -0.1) return { text: t('news.negative', 'Negative'), cls: 'bg-accent-red/10 text-accent-red/80' }
  return null
}

function isNew(dateStr) {
  if (!dateStr) return false
  return (Date.now() - new Date(dateStr).getTime()) < 300_000 // 5 minutes
}

function NewsItem({ item, isLast, t }) {
  const handleClick = () => {
    if (item.url) window.open(item.url, '_blank', 'noopener,noreferrer')
  }

  const sentiment = getSentimentLabel(item.sentiment_score, t)
  const fresh = isNew(item.published_at || item.publishedAt || item.time)
  const srcColor = getSourceColor(item.source)

  return (
    <button
      onClick={handleClick}
      className={`w-full text-left px-3 py-2.5 flex items-start gap-2.5 hover:bg-bg-hover/50 transition-colors ${
        !isLast ? 'border-b border-text-muted/8' : ''
      } ${fresh ? 'bg-accent-blue/5' : ''}`}
    >
      {/* Source indicator bar */}
      <div className="mt-0.5 flex-shrink-0 flex flex-col items-center gap-1">
        <div
          className="w-1 h-8 rounded-full opacity-70"
          style={{ backgroundColor: srcColor }}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          {fresh && (
            <span className="text-[9px] font-bold text-accent-blue bg-accent-blue/15 px-1 py-px rounded animate-pulse">
              {t('news.new')}
            </span>
          )}
          {sentiment && (
            <span className={`text-[9px] font-medium px-1 py-px rounded ${sentiment.cls}`}>
              {sentiment.text}
            </span>
          )}
        </div>
        <p className="text-text-primary text-[13px] leading-snug line-clamp-2">
          {item.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          {item.source && (
            <span
              className="text-[10px] font-medium truncate max-w-[100px] opacity-80"
              style={{ color: srcColor }}
            >
              {item.source.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </span>
          )}
          <span className="text-text-muted text-[10px]">
            {formatTimeAgo(item.published_at || item.publishedAt || item.time)}
          </span>
        </div>
      </div>

      {/* Arrow */}
      {item.url && (
        <div className="mt-1.5 flex-shrink-0 text-text-muted/40">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M7 17l9.2-9.2M17 17V7H7" />
          </svg>
        </div>
      )}
    </button>
  )
}

export default function NewsCarousel() {
  const { t } = useTranslation('dashboard')
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const prevCountRef = useRef(0)

  const fetchNews = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getLatestNews(30)
      const items = Array.isArray(data) ? data : data?.items || data?.news || []
      setNews(items)
      setLastUpdate(new Date())

      // Flash effect when new items arrive
      if (prevCountRef.current > 0 && items.length > prevCountRef.current) {
        // New items detected
      }
      prevCountRef.current = items.length
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchNews()
    const interval = setInterval(fetchNews, 30_000) // Poll every 30 seconds
    return () => clearInterval(interval)
  }, [fetchNews])

  const displayedNews = news.slice(0, 15)

  // Count unique sources
  const sources = new Set(news.map((n) => n.source).filter(Boolean))

  return (
    <div className="bg-bg-card rounded-2xl overflow-hidden slide-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-text-primary font-semibold text-sm">{t('news.title')}</h3>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-green" />
          </span>
        </div>
        <div className="flex items-center gap-2">
          {sources.size > 0 && (
            <span className="text-text-muted text-[10px]">
              {sources.size} {t('news.sources')}
            </span>
          )}
          <span className="text-text-muted text-[10px]">
            {news.length} {t('news.articles', 'articles')}
          </span>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="px-4 pb-4 space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse flex items-start gap-2.5">
              <div className="w-1 h-8 rounded-full bg-bg-secondary" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 bg-bg-secondary rounded w-full" />
                <div className="h-3 bg-bg-secondary rounded w-2/3" />
                <div className="h-2 bg-bg-secondary rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="px-4 pb-4 flex flex-col items-center justify-center py-6 gap-2">
          <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('news.title') })}</p>
          <button onClick={fetchNews} className="text-accent-blue text-xs hover:underline">{t('common:app.retry')}</button>
        </div>
      ) : displayedNews.length === 0 ? (
        <div className="px-4 pb-4 py-6 text-center">
          <p className="text-text-secondary text-sm">{t('news.noNews')}</p>
          <p className="text-text-muted text-xs mt-1">{t('news.willAppear', 'News will appear here once collected')}</p>
        </div>
      ) : (
        <div className="max-h-[400px] overflow-y-auto scrollbar-thin">
          {displayedNews.map((item, index) => (
            <NewsItem
              key={item.id || `${item.source}-${index}`}
              item={item}
              isLast={index === displayedNews.length - 1}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  )
}
