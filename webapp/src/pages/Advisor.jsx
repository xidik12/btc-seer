import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { formatPrice, formatPercent, formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const ADVISOR_TABS = [
  { path: '/advisor', label: 'AI Advisor' },
  { path: '/mock-trading', label: 'Paper Trading' },
  { path: '/history', label: 'History' },
]

function PortfolioCard({ portfolio }) {
  if (!portfolio) return null

  const pnlColor = (portfolio.total_pnl || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
  const pnlBg = (portfolio.total_pnl || 0) >= 0 ? 'bg-accent-green/10 border-accent-green/20' : 'bg-accent-red/10 border-accent-red/20'

  return (
    <div className={`rounded-2xl p-4 border slide-up ${pnlBg}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-text-muted text-[10px] font-medium">PORTFOLIO VALUE</div>
          <div className="text-text-primary text-xl font-bold tabular-nums">
            {formatPrice(portfolio.balance || portfolio.total_value || 0)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[10px] font-medium">TOTAL P&L</div>
          <div className={`text-xl font-bold tabular-nums ${pnlColor}`}>
            {portfolio.total_pnl >= 0 ? '+' : ''}{formatPrice(portfolio.total_pnl || 0)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Win Rate</div>
          <div className="text-text-primary text-sm font-bold">
            {portfolio.win_rate != null ? `${portfolio.win_rate.toFixed(0)}%` : '--'}
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Total Trades</div>
          <div className="text-text-primary text-sm font-bold">
            {portfolio.total_trades || 0}
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">Active</div>
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

function TradeCard({ trade, onOpen, onClose, currentPrice }) {
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
          <span className="text-text-primary text-sm font-semibold">BTC/USDT</span>
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
          <div className="text-text-muted text-[9px]">Entry</div>
          <div className="font-mono tabular-nums">{formatPrice(trade.entry_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">Current</div>
          <div className="font-mono tabular-nums">{formatPrice(price)}</div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">P&L</div>
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
              Open Trade
            </button>
          )}
          {isActive && onClose && (
            <button
              onClick={(e) => { e.stopPropagation(); onClose(trade.id, price) }}
              className="text-[10px] px-3 py-1 rounded-lg bg-accent-red/15 text-accent-red font-medium hover:bg-accent-red/25 transition-colors"
            >
              Close
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
  const telegramId = user?.id

  const [portfolio, setPortfolio] = useState(null)
  const [activeTrades, setActiveTrades] = useState([])
  const [historyTrades, setHistoryTrades] = useState([])
  const [currentPrice, setCurrentPrice] = useState(0)
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
      const [p, trades, hist] = await Promise.all([
        api.getPortfolio(telegramId),
        api.getActiveTrades(telegramId),
        api.getTradeHistory(telegramId),
      ])
      setPortfolio(p)
      setActiveTrades(trades?.trades || trades || [])
      setHistoryTrades(hist?.results || hist?.trades || hist || [])
      if (trades?.current_price) setCurrentPrice(trades.current_price)
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
        <h1 className="text-lg font-bold">Trading Advisor</h1>
        <SubTabBar tabs={ADVISOR_TABS} />
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-accent-blue/10 flex items-center justify-center">
            <svg className="w-6 h-6 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm font-medium">Telegram Login Required</p>
          <p className="text-text-muted text-xs leading-relaxed">
            Open BTC Seer from the Telegram bot to access your personalized trading advisor with
            AI-generated trade plans, portfolio tracking, and performance history.
          </p>
          <button
            onClick={() => navigate('/mock-trading')}
            className="mt-2 text-xs px-4 py-2 rounded-lg bg-accent-blue/15 text-accent-blue font-medium hover:bg-accent-blue/25 transition-colors"
          >
            Try Paper Trading Instead
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Trading Advisor</h1>
        <SubTabBar tabs={ADVISOR_TABS} />
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
        <h1 className="text-lg font-bold">Trading Advisor</h1>
        <SubTabBar tabs={ADVISOR_TABS} />
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">Failed to load</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">Trading Advisor</h1>

      <SubTabBar tabs={ADVISOR_TABS} />

      <PortfolioCard portfolio={portfolio} />

      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {['active', 'history'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              tab === t ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t === 'active' ? `Active (${Array.isArray(activeTrades) ? activeTrades.length : 0})` : `History (${Array.isArray(historyTrades) ? historyTrades.length : 0})`}
          </button>
        ))}
      </div>

      {tab === 'active' ? (
        Array.isArray(activeTrades) && activeTrades.length > 0 ? (
          <div className="space-y-2">
            {activeTrades.map((t, i) => (
              <TradeCard key={t.id || i} trade={t} onOpen={handleOpen} onClose={handleClose} currentPrice={currentPrice} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">No active trades</p>
            <p className="text-text-muted text-xs mt-1">Trade suggestions will appear here when the AI identifies opportunities.</p>
          </div>
        )
      ) : (
        Array.isArray(historyTrades) && historyTrades.length > 0 ? (
          <div className="space-y-2">
            {historyTrades.map((t, i) => (
              <ClosedTradeRow key={t.id || i} trade={t} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">No trade history yet</p>
          </div>
        )
      )}

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        Trade suggestions are AI-generated. Always verify before executing. This is not financial advice.
      </p>
    </div>
  )
}
