import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import { formatTimeAgo } from '../utils/format.js'

const SENTIMENT_STYLES = {
  positive: 'bg-accent-green',
  bullish: 'bg-accent-green',
  negative: 'bg-accent-red',
  bearish: 'bg-accent-red',
  neutral: 'bg-accent-yellow',
}

function getSentimentDotClass(sentiment) {
  const key = (sentiment || '').toLowerCase()
  return SENTIMENT_STYLES[key] || SENTIMENT_STYLES.neutral
}

function NewsItem({ item, isLast }) {
  const handleClick = () => {
    if (item.url) {
      window.open(item.url, '_blank', 'noopener,noreferrer')
    }
  }

  const sentimentDot = getSentimentDotClass(item.sentiment)

  return (
    <button
      onClick={handleClick}
      className={`w-full text-left px-3 py-2.5 flex items-start gap-3 hover:bg-bg-hover transition-colors ${
        !isLast ? 'border-b border-text-muted/10' : ''
      }`}
    >
      {/* Sentiment dot */}
      <div className="mt-1.5 flex-shrink-0">
        <div className={`w-2 h-2 rounded-full ${sentimentDot}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-text-primary text-sm leading-snug line-clamp-2">
          {item.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          {item.source && (
            <span className="text-text-secondary text-xs truncate max-w-[120px]">
              {item.source}
            </span>
          )}
          <span className="text-text-muted text-xs">
            {formatTimeAgo(item.published_at || item.publishedAt || item.time)}
          </span>
        </div>
      </div>

      {/* Arrow */}
      {item.url && (
        <div className="mt-1 flex-shrink-0 text-text-muted">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M7 17l9.2-9.2M17 17V7H7" />
          </svg>
        </div>
      )}
    </button>
  )
}

export default function NewsCarousel() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchNews = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getLatestNews(10)
      setNews(Array.isArray(data) ? data : data?.items || data?.news || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchNews()
    const interval = setInterval(fetchNews, 120_000)
    return () => clearInterval(interval)
  }, [fetchNews])

  const displayedNews = news.slice(0, 5)

  return (
    <div className="bg-bg-card rounded-2xl overflow-hidden slide-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <h3 className="text-text-primary font-semibold text-sm">
          Latest News
        </h3>
        {news.length > 0 && (
          <span className="text-text-muted text-xs">
            {news.length} articles
          </span>
        )}
      </div>

      {/* Content */}
      {loading ? (
        <div className="px-4 pb-4 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-bg-secondary mt-1.5" />
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
          <p className="text-accent-red text-sm">Failed to load news</p>
          <button
            onClick={fetchNews}
            className="text-accent-blue text-xs hover:underline"
          >
            Retry
          </button>
        </div>
      ) : displayedNews.length === 0 ? (
        <div className="px-4 pb-4 py-6 text-center">
          <p className="text-text-secondary text-sm">No recent news</p>
        </div>
      ) : (
        <div className="max-h-[280px] overflow-y-auto">
          {displayedNews.map((item, index) => (
            <NewsItem
              key={item.id || index}
              item={item}
              isLast={index === displayedNews.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}
