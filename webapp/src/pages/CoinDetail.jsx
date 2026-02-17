import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../utils/api'
import { formatCoinPrice, formatPercent, formatMarketCap, formatSupply, formatDate } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'

const CHART_PERIODS = [
  { labelKey: 'detail.timeframes.1d', days: 1 },
  { labelKey: 'detail.timeframes.7d', days: 7 },
  { labelKey: 'detail.timeframes.30d', days: 30 },
  { labelKey: 'detail.timeframes.90d', days: 90 },
]

export default function CoinDetail() {
  const { coinId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation('coins')
  const [detail, setDetail] = useState(null)
  const [chart, setChart] = useState([])
  const [period, setPeriod] = useState(7)
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)
  const [prediction, setPrediction] = useState(null)
  const [signal, setSignal] = useState(null)
  const [sentiment, setSentiment] = useState(null)

  useEffect(() => {
    setLoading(true)
    api.getCoinDetail(coinId).then(data => {
      if (!data.error) setDetail(data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [coinId])

  useEffect(() => {
    setChartLoading(true)
    api.getCoinChart(coinId, period).then(data => {
      setChart(data.prices || [])
      setChartLoading(false)
    }).catch(() => setChartLoading(false))
  }, [coinId, period])

  useEffect(() => {
    if (!coinId) return
    api.getCoinPrediction(coinId).then(setPrediction).catch(() => {})
    api.getCoinSignal(coinId).then(setSignal).catch(() => {})
    api.getCoinSentiment(coinId).then(setSentiment).catch(() => {})
  }, [coinId])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4 pb-20">
        <div className="h-8 bg-bg-card rounded animate-pulse" />
        <div className="h-48 bg-bg-card rounded-xl animate-pulse" />
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-16 bg-bg-card rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="px-4 pt-4 pb-20">
        <button onClick={() => navigate('/coins')} className="text-accent-blue text-sm mb-4">&larr; {t('title')}</button>
        <p className="text-text-muted text-center">{t('noResults')}</p>
      </div>
    )
  }

  const md = detail.market_data || {}
  const price = md.price_usd
  const change = md.change_24h
  const changeColor = (change || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
  const chartColor = (change || 0) >= 0 ? '#22c55e' : '#ef4444'

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      {/* Back + Header */}
      <button onClick={() => navigate('/coins')} className="text-accent-blue text-sm">&larr; {t('title')}</button>

      <div className="flex items-center gap-3">
        {detail.image ? (
          <img src={detail.image} alt={detail.symbol} className="w-10 h-10 rounded-full" />
        ) : (
          <div className="w-10 h-10 rounded-full bg-accent-blue/20 flex items-center justify-center font-bold text-accent-blue">
            {detail.symbol?.[0]}
          </div>
        )}
        <div>
          <h1 className="text-lg font-bold">{detail.name}</h1>
          <p className="text-xs text-text-muted">{detail.symbol}</p>
        </div>
        {md.market_cap_rank && (
          <span className="ml-auto text-[10px] text-text-muted bg-white/5 px-2 py-1 rounded-full">
            {t('detail.rankNumber', { rank: md.market_cap_rank })}
          </span>
        )}
      </div>

      {/* Price */}
      <div>
        <p className="text-2xl font-bold">{formatCoinPrice(price)}</p>
        <p className={`text-sm font-medium ${changeColor}`}>
          {formatPercent(change)} {t('detail.change24hLabel')}
        </p>
      </div>

      {/* Chart */}
      <ChartSection chart={chart} chartLoading={chartLoading} chartColor={chartColor} period={period} setPeriod={setPeriod} t={t} />

      {/* AI Prediction */}
      {prediction?.direction && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
          <h3 className="text-xs font-bold text-text-muted mb-2">AI Prediction</h3>
          <div className="flex items-center justify-between">
            <span className={`text-sm font-bold ${
              prediction.direction === 'bullish' ? 'text-accent-green' :
              prediction.direction === 'bearish' ? 'text-accent-red' : 'text-text-muted'
            }`}>
              {prediction.direction === 'bullish' ? '▲ Bullish' : prediction.direction === 'bearish' ? '▼ Bearish' : '◄► Neutral'}
            </span>
            <span className="text-xs text-text-muted">
              {prediction.confidence != null ? `${(prediction.confidence * 100).toFixed(0)}% conf` : ''}
            </span>
          </div>
          {prediction.predicted_change_pct != null && (
            <p className="text-[10px] text-text-muted mt-1">
              Expected: {prediction.predicted_change_pct > 0 ? '+' : ''}{prediction.predicted_change_pct.toFixed(2)}%
            </p>
          )}
        </div>
      )}

      {/* Trading Signal */}
      {signal?.action && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
          <h3 className="text-xs font-bold text-text-muted mb-2">Signal</h3>
          <div className="flex items-center justify-between">
            <span className={`text-sm font-bold uppercase ${
              signal.action.includes('buy') ? 'text-accent-green' :
              signal.action.includes('sell') ? 'text-accent-red' : 'text-text-muted'
            }`}>
              {signal.action.replace('_', ' ')}
            </span>
            {signal.risk_rating != null && (
              <span className="text-[10px] text-text-muted">Risk: {signal.risk_rating}/10</span>
            )}
          </div>
          {signal.entry_price && (
            <div className="flex gap-4 text-[10px] text-text-muted mt-1">
              <span>Entry: ${signal.entry_price.toLocaleString()}</span>
              {signal.target_price && <span>Target: ${signal.target_price.toLocaleString()}</span>}
              {signal.stop_loss && <span>SL: ${signal.stop_loss.toLocaleString()}</span>}
            </div>
          )}
        </div>
      )}

      {/* Sentiment */}
      {sentiment && (sentiment.news_sentiment_24h != null || sentiment.social_sentiment != null) && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
          <h3 className="text-xs font-bold text-text-muted mb-2">Sentiment</h3>
          <div className="flex gap-4">
            {sentiment.news_sentiment_24h != null && (
              <div>
                <p className="text-[10px] text-text-muted">News (24h)</p>
                <p className={`text-sm font-bold ${
                  sentiment.news_sentiment_24h > 0.1 ? 'text-accent-green' :
                  sentiment.news_sentiment_24h < -0.1 ? 'text-accent-red' : 'text-text-muted'
                }`}>
                  {sentiment.news_sentiment_24h > 0 ? '+' : ''}{(sentiment.news_sentiment_24h * 100).toFixed(0)}%
                </p>
              </div>
            )}
            {sentiment.social_sentiment != null && (
              <div>
                <p className="text-[10px] text-text-muted">Social</p>
                <p className={`text-sm font-bold ${
                  sentiment.social_sentiment > 0.1 ? 'text-accent-green' :
                  sentiment.social_sentiment < -0.1 ? 'text-accent-red' : 'text-text-muted'
                }`}>
                  {sentiment.social_sentiment > 0 ? '+' : ''}{(sentiment.social_sentiment * 100).toFixed(0)}%
                </p>
              </div>
            )}
            {sentiment.news_volume != null && (
              <div>
                <p className="text-[10px] text-text-muted">News Vol</p>
                <p className="text-sm font-bold text-text-primary">{sentiment.news_volume}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard label={t('detail.marketCap')} value={formatMarketCap(md.market_cap)} />
        <StatCard label={t('detail.volume24h')} value={formatMarketCap(md.volume_24h)} />
        <StatCard label={t('detail.circulatingSupply')} value={formatSupply(md.circulating_supply, detail.symbol)} />
        <StatCard label={t('detail.totalSupply')} value={formatSupply(md.total_supply, detail.symbol)} />
        <StatCard label={t('detail.allTimeHigh')} value={formatCoinPrice(md.ath)} sub={md.ath_date ? formatDate(md.ath_date) : null} />
        <StatCard label={t('detail.allTimeLow')} value={formatCoinPrice(md.atl)} sub={md.atl_date ? formatDate(md.atl_date) : null} />
        <StatCard label={t('detail.change7d')} value={formatPercent(md.change_7d)} color={md.change_7d >= 0 ? 'text-accent-green' : 'text-accent-red'} />
        <StatCard label={t('detail.change30d')} value={formatPercent(md.change_30d)} color={md.change_30d >= 0 ? 'text-accent-green' : 'text-accent-red'} />
      </div>

      {/* FDV */}
      {md.fully_diluted_valuation && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-[10px] text-text-muted mb-1">{t('detail.fdv')}</p>
          <p className="text-sm font-bold">{formatMarketCap(md.fully_diluted_valuation)}</p>
        </div>
      )}

      {/* Contract Addresses */}
      {detail.platforms && Object.keys(detail.platforms).length > 0 && (
        <div className="bg-bg-card rounded-xl p-4 border border-white/5">
          <h3 className="text-xs font-semibold text-text-muted mb-2">{t('detail.contracts')}</h3>
          <div className="space-y-2">
            {Object.entries(detail.platforms).filter(([, addr]) => addr).map(([chain, addr]) => (
              <div key={chain} className="flex items-center justify-between">
                <span className="text-xs text-text-secondary capitalize">{chain.replace(/-/g, ' ')}</span>
                <button
                  onClick={() => navigate(`/coins/report/${addr}`)}
                  className="text-[10px] text-accent-blue truncate max-w-[180px]"
                >
                  {addr.slice(0, 8)}...{addr.slice(-6)}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ChartSection({ chart, chartLoading, chartColor, period, setPeriod, t }) {
  const { data: visibleChart, bindGestures, isZoomed, resetZoom } = useChartZoom(chart)

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5">
      <div className="flex items-center gap-2 mb-3">
        {CHART_PERIODS.map(p => (
          <button
            key={p.days}
            onClick={() => setPeriod(p.days)}
            className={`px-3 py-1 rounded-full text-[10px] font-medium transition-colors ${
              period === p.days
                ? 'bg-accent-blue text-white'
                : 'bg-white/5 text-text-muted hover:text-text-secondary'
            }`}
          >
            {t(p.labelKey)}
          </button>
        ))}
        {isZoomed && (
          <button onClick={resetZoom} className="ml-auto text-[10px] text-accent-blue">{t('chart.reset', { ns: 'common' })}</button>
        )}
      </div>

      {chartLoading ? (
        <div className="h-40 flex items-center justify-center text-text-muted text-xs">{t('chart.loading', { ns: 'common' })}</div>
      ) : chart.length > 0 ? (
        <div {...bindGestures}>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={visibleChart}>
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" hide />
              <YAxis domain={['auto', 'auto']} hide />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                labelFormatter={v => new Date(v).toLocaleDateString()}
                formatter={v => [formatCoinPrice(v), t('detail.price')]}
              />
              <Area type="monotone" dataKey="price" stroke={chartColor} fill="url(#chartGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-40 flex items-center justify-center text-text-muted text-xs">{t('chart.noData', { ns: 'common' })}</div>
      )}
      <p className="text-text-muted text-[9px] text-center mt-1.5">{t('chart.pinchZoom', { ns: 'common' })}</p>
    </div>
  )
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5">
      <p className="text-[10px] text-text-muted mb-1">{label}</p>
      <p className={`text-sm font-bold ${color || ''}`}>{value}</p>
      {sub && <p className="text-[10px] text-text-muted mt-0.5">{sub}</p>}
    </div>
  )
}
