import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { formatPrice, formatPercent, formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const ADVISOR_TABS = [
  { path: '/advisor', labelKey: 'advisor.tabs.advisor' },
  { path: '/mock-trading', labelKey: 'advisor.tabs.paperTrading' },
  { path: '/history', labelKey: 'advisor.tabs.history' },
]

function PortfolioSetupCard({ telegramId, onSetup, t }) {
  const [balance, setBalance] = useState(10)
  const [maxLeverage, setMaxLeverage] = useState(20)
  const [maxOpenTrades, setMaxOpenTrades] = useState(3)
  const [riskPct, setRiskPct] = useState(10)
  const [saving, setSaving] = useState(false)

  const handleSetup = async () => {
    setSaving(true)
    try {
      await api.setupPortfolio(telegramId, {
        balance,
        max_leverage: maxLeverage,
        max_open_trades: maxOpenTrades,
        max_risk_per_trade_pct: riskPct,
      })
      onSetup()
    } catch (err) {
      console.error('Portfolio setup error:', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-accent-blue/20 slide-up">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-accent-blue/10 flex items-center justify-center">
          <svg className="w-4 h-4 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        </div>
        <div>
          <div className="text-text-primary text-sm font-bold">{t('advisor.setUpPortfolio')}</div>
          <div className="text-text-muted text-[10px]">{t('advisor.confidence')}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('advisor.balance')}</label>
          <input
            type="number"
            value={balance}
            onChange={e => setBalance(Number(e.target.value))}
            min={1}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50"
          />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('trade.leverage', { ns: 'common' })}</label>
          <input
            type="number"
            value={maxLeverage}
            onChange={e => setMaxLeverage(Number(e.target.value))}
            min={1}
            max={125}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50"
          />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('portfolio.totalTrades')}</label>
          <input
            type="number"
            value={maxOpenTrades}
            onChange={e => setMaxOpenTrades(Number(e.target.value))}
            min={1}
            max={20}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50"
          />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('advisor.riskLevel')}</label>
          <input
            type="number"
            value={riskPct}
            onChange={e => setRiskPct(Number(e.target.value))}
            min={1}
            max={100}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50"
          />
        </div>
      </div>

      <button
        onClick={handleSetup}
        disabled={saving}
        className="w-full py-2.5 rounded-xl bg-accent-blue text-white text-xs font-bold hover:bg-accent-blue/90 transition-colors disabled:opacity-50"
      >
        {saving ? t('app.loading', { ns: 'common' }) : t('advisor.getSuggestion')}
      </button>
    </div>
  )
}

function AIAccuracyCard({ feedback }) {
  if (!feedback || feedback.total_trades === 0) return null

  const winRate = feedback.total_trades > 0
    ? (feedback.winning_trades / feedback.total_trades * 100).toFixed(0)
    : 0

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="text-text-muted text-[10px] font-medium mb-2">AI ACCURACY (Last {feedback.days}d)</div>
      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Direction</div>
          <div className={`text-sm font-bold ${feedback.direction_accuracy >= 55 ? 'text-accent-green' : 'text-accent-red'}`}>
            {feedback.direction_accuracy.toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Win Rate</div>
          <div className={`text-sm font-bold ${Number(winRate) >= 50 ? 'text-accent-green' : 'text-accent-red'}`}>
            {winRate}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Avg R:R</div>
          <div className={`text-sm font-bold ${feedback.avg_achieved_rr >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {feedback.avg_achieved_rr.toFixed(1)}
          </div>
        </div>
      </div>
      {feedback.confidence_calibration && Object.keys(feedback.confidence_calibration).length > 0 && (
        <div className="mt-3 pt-2 border-t border-white/5">
          <div className="text-text-muted text-[9px] mb-1">{t('advisor.confidence')} Calibration</div>
          <div className="flex gap-1">
            {Object.entries(feedback.confidence_calibration).map(([bucket, data]) => (
              <div key={bucket} className="flex-1 text-center">
                <div className="text-text-muted text-[8px]">{bucket}%</div>
                <div className={`text-[10px] font-bold ${data.win_rate >= 50 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {data.win_rate}%
                </div>
                <div className="text-text-muted text-[8px]">n={data.total}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PortfolioCard({ portfolio, t }) {
  if (!portfolio) return null

  const pnlColor = (portfolio.total_pnl || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
  const pnlBg = (portfolio.total_pnl || 0) >= 0 ? 'bg-accent-green/10 border-accent-green/20' : 'bg-accent-red/10 border-accent-red/20'

  return (
    <div className={`rounded-2xl p-4 border slide-up ${pnlBg}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">{t('advisor.portfolio')}</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {formatPrice(portfolio.balance || portfolio.total_value || 0)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">{t('portfolio.totalPnl')}</div>
          <div className={`text-xl font-bold tabular-nums ${pnlColor}`}>
            {portfolio.total_pnl >= 0 ? '+' : ''}{formatPrice(portfolio.total_pnl || 0)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('portfolio.winRate')}</div>
          <div className="text-text-primary text-sm font-bold">
            {portfolio.win_rate != null ? `${portfolio.win_rate.toFixed(0)}%` : '--'}
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('portfolio.totalTrades')}</div>
          <div className="text-text-primary text-sm font-bold">
            {portfolio.total_trades || 0}
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('portfolio.active')}</div>
          <div className="text-text-primary text-sm font-bold">
            {portfolio.active_trades || 0}
          </div>
        </div>
      </div>
    </div>
  )
}

function TPProgress({ currentPrice, entry, targets, stopLoss }) {
  if (!entry || !targets?.length) return null

  const isLong = targets[0] > entry
  const range = isLong
    ? (targets[targets.length - 1] - stopLoss)
    : (stopLoss - targets[targets.length - 1])
  const progress = isLong
    ? ((currentPrice - stopLoss) / range) * 100
    : ((stopLoss - currentPrice) / range) * 100

  return (
    <div className="mt-2">
      <div className="flex justify-between text-[9px] text-text-muted mb-0.5">
        <span>SL {formatPrice(stopLoss)}</span>
        {targets.map((tp, i) => (
          <span key={i} className={currentPrice >= tp === isLong ? 'text-accent-green font-bold' : ''}>
            TP{i + 1} {formatPrice(tp)}
          </span>
        ))}
      </div>
      <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            progress > 80 ? 'bg-accent-green' : progress > 40 ? 'bg-accent-yellow' : 'bg-accent-red'
          }`}
          style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
        />
      </div>
    </div>
  )
}

function TradeCard({ trade, onOpen, onClose, currentPrice, t }) {
  const isActive = trade.status === 'active' || trade.status === 'open' || trade.status === 'opened'
  const isPending = trade.status === 'pending' || trade.status === 'suggested'
  const isLong = trade.direction === 'LONG' || trade.direction === 'long' || trade.action?.includes('buy')
  const price = trade.current_price || currentPrice || 0
  const pnl = trade.unrealized_pnl || trade.pnl || 0
  const pnlPct = trade.unrealized_pnl_pct || trade.pnl_pct || (trade.entry_price ? ((price - trade.entry_price) / trade.entry_price * 100 * (isLong ? 1 : -1) * (trade.leverage || 1)) : 0)

  return (
    <div className={`bg-bg-card rounded-xl border p-3 slide-up ${
      isActive
        ? pnlPct >= 0 ? 'border-accent-green/20' : 'border-accent-red/20'
        : 'border-white/5'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
            isLong
              ? 'bg-accent-green/15 text-accent-green'
              : 'bg-accent-red/15 text-accent-red'
          }`}>
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          <span className="text-text-primary text-sm font-semibold">{t('trade.btcUsdt', { ns: 'common' })}</span>
          {trade.leverage && <span className="text-text-muted text-[9px]">{trade.leverage}x</span>}
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${
          isActive ? 'bg-accent-blue/15 text-accent-blue' :
          isPending ? 'bg-accent-yellow/15 text-accent-yellow' :
          'bg-bg-hover text-text-muted'
        }`}>
          {trade.status?.toUpperCase() || 'PENDING'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs mb-2">
        <div>
          <div className="text-text-muted text-[9px]">{t('trade.entry', { ns: 'common' })}</div>
          <div className="font-mono tabular-nums">{formatPrice(trade.entry_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">{t('trade.current', { ns: 'common' })}</div>
          <div className="font-mono tabular-nums">{formatPrice(price)}</div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">{t('trade.pnl', { ns: 'common' })}</div>
          <div className={`font-bold tabular-nums ${pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
      </div>

      <TPProgress
        currentPrice={price}
        entry={trade.entry_price}
        targets={trade.targets || [trade.take_profit_1, trade.take_profit_2, trade.take_profit_3].filter(Boolean)}
        stopLoss={trade.stop_loss}
      />

      {trade.reasoning && (
        <p className="text-text-muted text-[10px] mt-2 leading-relaxed">{trade.reasoning}</p>
      )}

      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
        <span className="text-text-muted text-[9px]">{formatTimeAgo(trade.created_at || trade.timestamp)}</span>
        <div className="flex gap-2">
          {isPending && onOpen && (
            <button
              onClick={(e) => { e.stopPropagation(); onOpen(trade.id) }}
              className="text-[10px] px-3 py-1 rounded-lg bg-accent-green/15 text-accent-green font-medium hover:bg-accent-green/25 transition-colors"
            >
              {t('advisor.executeTrade')}
            </button>
          )}
          {isActive && onClose && (
            <button
              onClick={(e) => { e.stopPropagation(); onClose(trade.id, price) }}
              className="text-[10px] px-3 py-1 rounded-lg bg-accent-red/15 text-accent-red font-medium hover:bg-accent-red/25 transition-colors"
            >
              {t('btn.close', { ns: 'common' })}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ClosedTradeRow({ trade }) {
  const isLong = trade.direction === 'LONG' || trade.direction === 'long' || trade.action?.includes('buy')
  const pnl = trade.pnl_usdt || trade.pnl || trade.realized_pnl || 0
  const won = trade.was_winner || pnl > 0

  return (
    <div className={`bg-bg-card rounded-xl border p-3 ${won ? 'border-accent-green/10' : 'border-accent-red/10'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-[9px] w-5 h-5 rounded-full flex items-center justify-center ${
            won ? 'bg-accent-green/20 text-accent-green' : 'bg-accent-red/20 text-accent-red'
          }`}>
            {won ? (
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            )}
          </span>
          <span className={`text-[10px] font-bold ${isLong ? 'text-accent-green' : 'text-accent-red'}`}>
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          {trade.leverage && <span className="text-text-muted text-[9px]">{trade.leverage}x</span>}
        </div>
        <div className="text-right">
          <span className={`text-xs font-bold tabular-nums ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {pnl >= 0 ? '+' : ''}{formatPrice(pnl)}
          </span>
          {trade.pnl_pct_leveraged != null && (
            <span className={`text-[9px] ml-1 ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
              ({trade.pnl_pct_leveraged >= 0 ? '+' : ''}{trade.pnl_pct_leveraged.toFixed(1)}%)
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-1 text-[9px] text-text-muted">
        <span>{formatPrice(trade.entry_price)} &rarr; {formatPrice(trade.exit_price || trade.close_price)}</span>
        <span>{trade.close_reason || ''} {formatTimeAgo(trade.closed_at || trade.timestamp)}</span>
      </div>
    </div>
  )
}

export default function Advisor() {
  const { user } = useTelegram()
  const navigate = useNavigate()
  const { t } = useTranslation('trading')
  const telegramId = user?.id

  const advisorTabs = useMemo(() => ADVISOR_TABS.map(at => ({
    ...at,
    label: t(at.labelKey),
  })), [t])

  const [portfolio, setPortfolio] = useState(null)
  const [activeTrades, setActiveTrades] = useState([])
  const [historyTrades, setHistoryTrades] = useState([])
  const [currentPrice, setCurrentPrice] = useState(0)
  const [feedback, setFeedback] = useState(null)
  const [needsSetup, setNeedsSetup] = useState(false)
  const [tab, setTab] = useState('active')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    if (!telegramId) {
      setLoading(false)
      return
    }
    try {
      setError(null)
      const [p, trades, hist, fb] = await Promise.all([
        api.getPortfolio(telegramId),
        api.getActiveTrades(telegramId),
        api.getTradeHistory(telegramId),
        api.getFeedback(30).catch(() => null),
      ])

      if (!p || p.error) {
        setNeedsSetup(true)
        setPortfolio(null)
      } else if (p.total_trades === 0 && p.total_pnl === 0) {
        // Portfolio exists with defaults but was never used — show setup
        setNeedsSetup(true)
        setPortfolio(p)
      } else {
        setNeedsSetup(false)
        setPortfolio(p)
      }

      setActiveTrades(trades?.trades || trades || [])
      setHistoryTrades(hist?.results || hist?.trades || hist || [])
      if (trades?.current_price) setCurrentPrice(trades.current_price)
      if (fb) setFeedback(fb)
    } catch (err) {
      setError(err.message || 'Failed to load advisor data')
    } finally {
      setLoading(false)
    }
  }, [telegramId])

  useEffect(() => { fetchData() }, [fetchData])

  const handleOpen = async (tradeId) => {
    try {
      await api.openTrade(tradeId)
      fetchData()
    } catch (err) {
      console.error('Open trade error:', err)
    }
  }

  const handleClose = async (tradeId, price) => {
    const exitPrice = price || currentPrice
    if (!exitPrice) return
    if (!window.confirm(`Close trade #${tradeId} at $${exitPrice.toLocaleString()}?`)) return
    try {
      await api.closeTrade(tradeId, exitPrice, 'manual_close')
      fetchData()
    } catch (err) {
      console.error('Close trade error:', err)
    }
  }

  if (!telegramId) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('advisor.title')}</h1>
        <SubTabBar tabs={advisorTabs} />
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-accent-blue/10 flex items-center justify-center">
            <svg className="w-6 h-6 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm font-medium">{t('loginRequired')}</p>
          <button
            onClick={() => navigate('/mock-trading')}
            className="mt-2 text-xs px-4 py-2 rounded-lg bg-accent-blue/15 text-accent-blue font-medium hover:bg-accent-blue/25 transition-colors"
          >
            {t('advisor.tabs.paperTrading')}
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('advisor.title')}</h1>
        <SubTabBar tabs={advisorTabs} />
        <div className="animate-pulse space-y-3">
          <div className="h-32 bg-bg-card rounded-2xl" />
          <div className="h-20 bg-bg-card rounded-2xl" />
          <div className="h-20 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('advisor.title')}</h1>
        <SubTabBar tabs={advisorTabs} />
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{t('app.error', { ns: 'common' })}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">{t('app.retry', { ns: 'common' })}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">{t('advisor.title')}</h1>

      <SubTabBar tabs={advisorTabs} />

      {needsSetup ? (
        <PortfolioSetupCard telegramId={telegramId} onSetup={fetchData} t={t} />
      ) : (
        <PortfolioCard portfolio={portfolio} t={t} />
      )}

      <AIAccuracyCard feedback={feedback} />

      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {['active', 'history'].map(tb => (
          <button
            key={tb}
            onClick={() => setTab(tb)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              tab === tb ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tb === 'active' ? `${t('advisor.activeTrades')} (${Array.isArray(activeTrades) ? activeTrades.length : 0})` : `${t('advisor.closedTrades')} (${Array.isArray(historyTrades) ? historyTrades.length : 0})`}
          </button>
        ))}
      </div>

      {tab === 'active' ? (
        Array.isArray(activeTrades) && activeTrades.length > 0 ? (
          <div className="space-y-2">
            {activeTrades.map((tr, i) => (
              <TradeCard key={tr.id || i} trade={tr} onOpen={handleOpen} onClose={handleClose} currentPrice={currentPrice} t={t} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">{t('advisor.noActiveTrades')}</p>
          </div>
        )
      ) : (
        Array.isArray(historyTrades) && historyTrades.length > 0 ? (
          <div className="space-y-2">
            {historyTrades.map((tr, i) => (
              <ClosedTradeRow key={tr.id || i} trade={tr} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">{t('advisor.noClosedTrades')}</p>
          </div>
        )
      )}

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        {t('app.disclaimer', { ns: 'common' })}
      </p>
    </div>
  )
}
