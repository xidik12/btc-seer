import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api.js'
import { formatTimeAgo } from '../utils/format.js'

const CATEGORY_STYLES = {
  // Backend categories
  ceo: { label: 'CEO', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  investor: { label: 'Investor', bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  government: { label: 'Gov', bg: 'bg-red-500/10', text: 'text-red-400' },
  regulator: { label: 'Regulator', bg: 'bg-orange-500/10', text: 'text-orange-400' },
  analyst: { label: 'Analyst', bg: 'bg-cyan-500/10', text: 'text-cyan-400' },
  developer: { label: 'Dev', bg: 'bg-green-500/10', text: 'text-green-400' },
  economist: { label: 'Economist', bg: 'bg-purple-500/10', text: 'text-purple-400' },
  // Legacy/alternate categories
  billionaire: { label: 'Billionaire', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  exchange_ceo: { label: 'Exchange CEO', bg: 'bg-blue-500/10', text: 'text-blue-400' },
  founder: { label: 'Founder', bg: 'bg-purple-500/10', text: 'text-purple-400' },
  politician: { label: 'Politician', bg: 'bg-red-500/10', text: 'text-red-400' },
  vc: { label: 'VC', bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  media: { label: 'Media', bg: 'bg-pink-500/10', text: 'text-pink-400' },
}

function getCategoryStyle(cat) {
  return CATEGORY_STYLES[cat] || { label: cat || 'Unknown', bg: 'bg-gray-500/10', text: 'text-gray-400' }
}

function getSentimentColor(score) {
  if (score == null) return 'text-text-muted'
  if (score > 0.3) return 'text-accent-green'
  if (score < -0.3) return 'text-accent-red'
  if (score > 0.1) return 'text-accent-green/70'
  if (score < -0.1) return 'text-accent-red/70'
  return 'text-text-muted'
}

function getSentimentBg(score) {
  if (score == null) return ''
  if (score > 0.3) return 'border-l-2 border-accent-green/30'
  if (score < -0.3) return 'border-l-2 border-accent-red/30'
  return ''
}

function WeightDots({ weight }) {
  const filled = Math.min(Math.round(weight / 2), 5)
  return (
    <div className="flex gap-px" title={`Influence: ${weight}/10`}>
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className={`w-1 h-1 rounded-full ${
            i < filled ? 'bg-accent-yellow' : 'bg-text-muted/20'
          }`}
        />
      ))}
    </div>
  )
}

function TweetItem({ tweet, isLast }) {
  const catStyle = getCategoryStyle(tweet.category)
  const sentColor = getSentimentColor(tweet.sentiment_score)
  const sentBg = getSentimentBg(tweet.sentiment_score)

  const handleClick = () => {
    if (tweet.url) window.open(tweet.url, '_blank', 'noopener,noreferrer')
  }

  return (
    <button
      onClick={handleClick}
      className={`w-full text-left px-3 py-2.5 hover:bg-bg-hover/50 transition-colors ${sentBg} ${
        !isLast ? 'border-b border-text-muted/8' : ''
      }`}
    >
      {/* Top row: name + category + weight */}
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-text-primary text-xs font-semibold truncate">
          {tweet.influencer}
        </span>
        <span className="text-text-muted text-[10px] truncate">
          @{tweet.username}
        </span>
        <span className={`text-[9px] font-medium px-1 py-px rounded ${catStyle.bg} ${catStyle.text} flex-shrink-0`}>
          {catStyle.label}
        </span>
        <div className="ml-auto flex-shrink-0">
          <WeightDots weight={tweet.weight || 5} />
        </div>
      </div>

      {/* Tweet text */}
      <p className="text-text-secondary text-[12px] leading-relaxed line-clamp-3">
        {tweet.text}
      </p>

      {/* Bottom row: sentiment + time */}
      <div className="flex items-center gap-2 mt-1">
        {tweet.sentiment_score != null && (
          <span className={`text-[10px] font-medium ${sentColor}`}>
            {tweet.sentiment_score > 0 ? '+' : ''}{tweet.sentiment_score.toFixed(2)}
          </span>
        )}
        <span className="text-text-muted text-[10px]">
          {formatTimeAgo(tweet.published_at || tweet.timestamp)}
        </span>
      </div>
    </button>
  )
}

export default function InfluencerFeed() {
  const { t } = useTranslation('dashboard')
  const [tweets, setTweets] = useState([])
  const [sentiment, setSentiment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const [tweetsData, sentData] = await Promise.all([
        api.getInfluencerTweets(15),
        api.getInfluencerSentiment(24),
      ])
      setTweets(tweetsData?.tweets || [])
      setSentiment(sentData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60_000) // Poll every 60s
    return () => clearInterval(interval)
  }, [fetchData])

  const sentimentLabel = sentiment?.weighted_sentiment != null
    ? sentiment.weighted_sentiment > 0.1 ? t('common:direction.bullish') : sentiment.weighted_sentiment < -0.1 ? t('common:direction.bearish') : t('common:direction.neutral')
    : null

  const sentLabelColor = sentimentLabel === t('common:direction.bullish')
    ? 'text-accent-green'
    : sentimentLabel === t('common:direction.bearish')
    ? 'text-accent-red'
    : 'text-accent-yellow'

  return (
    <div className="bg-bg-card rounded-2xl overflow-hidden slide-up">
      {/* Header */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-text-primary font-semibold text-sm">{t('influencer.title')}</h3>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-400" />
            </span>
          </div>
          {sentiment && sentiment.count > 0 && (
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-semibold ${sentLabelColor}`}>
                {sentimentLabel}
              </span>
              <span className="text-text-muted text-[10px]">
                {sentiment.bullish_count}B / {sentiment.bearish_count}R
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="px-4 pb-4 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="h-3 bg-bg-secondary rounded w-24" />
                <div className="h-3 bg-bg-secondary rounded w-16" />
              </div>
              <div className="h-3 bg-bg-secondary rounded w-full" />
              <div className="h-3 bg-bg-secondary rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="px-4 pb-4 flex flex-col items-center justify-center py-6 gap-2">
          <p className="text-accent-red text-sm">{t('common:widget.failedToLoad', { name: t('influencer.title') })}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">{t('common:app.retry')}</button>
        </div>
      ) : tweets.length === 0 ? (
        <div className="px-4 pb-4 py-6 text-center">
          <p className="text-text-secondary text-sm">{t('influencer.noData')}</p>
          <p className="text-text-muted text-xs mt-1">{t('influencer.monitoring', { count: '25+' })}</p>
        </div>
      ) : (
        <div className="max-h-[350px] overflow-y-auto scrollbar-thin">
          {tweets.map((tweet, index) => (
            <TweetItem
              key={tweet.id || index}
              tweet={tweet}
              isLast={index === tweets.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}
