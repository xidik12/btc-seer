import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'

const SENTIMENT_COLORS = {
  bullish: 'text-accent-green',
  bearish: 'text-accent-red',
  neutral: 'text-accent-yellow',
}

export default function Briefing() {
  const { t } = useTranslation('common')
  const [briefing, setBriefing] = useState(null)
  const [history, setHistory] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getLatestBriefing(),
      api.getBriefingHistory(14),
    ])
      .then(([latest, hist]) => {
        setBriefing(latest?.briefing)
        setHistory(hist?.briefings || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleDateSelect = (date) => {
    setSelectedDate(date)
    setLoading(true)
    api.getBriefingByDate(date)
      .then((res) => setBriefing(res?.briefing))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  if (loading && !briefing) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const sentColor = SENTIMENT_COLORS[briefing?.overall_sentiment] || 'text-text-muted'
  const change = briefing?.btc_24h_change
  const changeColor = change > 0 ? 'text-accent-green' : change < 0 ? 'text-accent-red' : 'text-text-muted'

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">{t('briefing.title')}</h1>

      {/* Date selector */}
      {history.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {history.map((h) => (
            <button
              key={h.date}
              onClick={() => handleDateSelect(h.date)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold whitespace-nowrap transition-colors ${
                (selectedDate || history[0]?.date) === h.date
                  ? 'bg-accent-blue text-white'
                  : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {h.date?.slice(5)}
            </button>
          ))}
        </div>
      )}

      {briefing ? (
        <>
          {/* Summary header */}
          <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-text-muted text-xs">{briefing.date}</span>
              <span className={`text-xs font-semibold ${sentColor}`}>
                {briefing.overall_sentiment?.charAt(0).toUpperCase() + briefing.overall_sentiment?.slice(1)}
              </span>
            </div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="text-text-primary font-bold text-2xl">
                ${briefing.btc_price?.toLocaleString() || '—'}
              </span>
              <span className={`text-sm font-medium ${changeColor}`}>
                {change > 0 ? '+' : ''}{change?.toFixed(2)}%
              </span>
            </div>
            {briefing.confidence && (
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-[10px]">{t('briefing.confidence')}</span>
                <div className="flex-1 h-1.5 bg-bg-primary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-accent-blue"
                    style={{ width: `${briefing.confidence}%` }}
                  />
                </div>
                <span className="text-text-muted text-[10px]">{Math.round(briefing.confidence)}%</span>
              </div>
            )}
          </div>

          {/* Data snapshot widgets */}
          {briefing.data_snapshot && (
            <div className="grid grid-cols-2 gap-2">
              {briefing.data_snapshot.fear_greed != null && (
                <div className="bg-bg-card rounded-xl p-3 border border-white/5">
                  <p className="text-text-muted text-[10px]">{t('briefing.fearGreed')}</p>
                  <p className="text-text-primary font-bold text-lg">{briefing.data_snapshot.fear_greed}</p>
                </div>
              )}
              {briefing.data_snapshot.whale_count != null && (
                <div className="bg-bg-card rounded-xl p-3 border border-white/5">
                  <p className="text-text-muted text-[10px]">{t('briefing.whaleTxs')}</p>
                  <p className="text-text-primary font-bold text-lg">{briefing.data_snapshot.whale_count}</p>
                </div>
              )}
              {briefing.data_snapshot.accuracy != null && (
                <div className="bg-bg-card rounded-xl p-3 border border-white/5">
                  <p className="text-text-muted text-[10px]">{t('briefing.aiAccuracy')}</p>
                  <p className="text-text-primary font-bold text-lg">{Math.round(briefing.data_snapshot.accuracy)}%</p>
                </div>
              )}
              {briefing.data_snapshot.arb_count != null && (
                <div className="bg-bg-card rounded-xl p-3 border border-white/5">
                  <p className="text-text-muted text-[10px]">{t('briefing.arbOpps')}</p>
                  <p className="text-text-primary font-bold text-lg">{briefing.data_snapshot.arb_count}</p>
                </div>
              )}
            </div>
          )}

          {/* Full content */}
          <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
            <div
              className="text-text-secondary text-xs leading-relaxed space-y-2 briefing-content"
              dangerouslySetInnerHTML={{ __html: briefing.summary_html }}
            />
          </div>
        </>
      ) : (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <p className="text-text-muted text-sm">{t('briefing.noBriefing')}</p>
          <p className="text-text-muted text-xs mt-1">{t('briefing.generatedAt')}</p>
        </div>
      )}
    </div>
  )
}
