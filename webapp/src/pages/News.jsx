import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { formatTimeAgo } from '../utils/format'

export default function News() {
  const [news, setNews] = useState([])
  const [sentiment, setSentiment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
      setError(err.message || 'Failed to load news')
      setNews([])
    }
    setLoading(false)
  }

  useEffect(() => { loadNews() }, [])

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
        News Feed
      </h1>

      {sentiment && (
        <div className="bg-bg-card rounded-xl p-4 mb-4 border border-white/5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">24h Sentiment Overview</h3>
          <div className="flex justify-between text-sm">
            <span className="text-accent-green">
              Bullish: {sentiment.bullish_pct?.toFixed(0)}%
            </span>
            <span className="text-accent-yellow">
              Neutral: {(100 - (sentiment.bullish_pct || 0) - (sentiment.bearish_pct || 0)).toFixed(0)}%
            </span>
            <span className="text-accent-red">
              Bearish: {sentiment.bearish_pct?.toFixed(0)}%
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
          <p className="text-accent-red text-sm mb-2">Failed to load news</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={loadNews} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      ) : news.length === 0 ? (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <div className="flex justify-center mb-2">
            <svg className="w-8 h-8 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm font-medium">No News Yet</p>
          <p className="text-text-muted text-xs mt-1">News articles will appear here as they are collected and analyzed for sentiment.</p>
          <button onClick={loadNews} className="text-accent-blue text-xs mt-3 hover:underline">Refresh</button>
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
