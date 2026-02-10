import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { formatPrice, formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const ADVISOR_TABS = [
  { path: '/advisor', label: 'AI Advisor' },
  { path: '/mock-trading', label: 'Paper Trading' },
  { path: '/history', label: 'History' },
]

function TradeForm({ currentPrice, onSubmit, submitting }) {
  const [direction, setDirection] = useState('LONG')
  const [entry, setEntry] = useState('')
  const [sl, setSl] = useState('')
  const [tp, setTp] = useState('')
  const [leverage, setLeverage] = useState('5')
  const [size, setSize] = useState('10')

  useEffect(() => {
    if (currentPrice && !entry) {
      setEntry(currentPrice.toFixed(0))
      // Default SL/TP based on direction
      const slPct = direction === 'LONG' ? 0.98 : 1.02
      const tpPct = direction === 'LONG' ? 1.04 : 0.96
      setSl((currentPrice * slPct).toFixed(0))
      setTp((currentPrice * tpPct).toFixed(0))
    }
  }, [currentPrice])

  const updateDefaults = (dir) => {
    setDirection(dir)
    const price = parseFloat(entry) || currentPrice || 0
    if (price) {
      const slPct = dir === 'LONG' ? 0.98 : 1.02
      const tpPct = dir === 'LONG' ? 1.04 : 0.96
      setSl((price * slPct).toFixed(0))
      setTp((price * tpPct).toFixed(0))
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      direction,
      entry_price: parseFloat(entry),
      stop_loss: parseFloat(sl),
      take_profit_1: parseFloat(tp),
      leverage: parseInt(leverage),
      position_size_usdt: parseFloat(size),
    })
  }

  const entryNum = parseFloat(entry) || 0
  const slNum = parseFloat(sl) || 0
  const tpNum = parseFloat(tp) || 0
  const lev = parseInt(leverage) || 1
  const sizeNum = parseFloat(size) || 0
  const riskPct = entryNum ? Math.abs(entryNum - slNum) / entryNum * 100 : 0
  const rewardPct = entryNum ? Math.abs(tpNum - entryNum) / entryNum * 100 : 0
  const rrRatio = riskPct > 0 ? (rewardPct / riskPct).toFixed(1) : '0'
  const riskUsdt = sizeNum * (riskPct / 100) * lev

  return (
    <form onSubmit={handleSubmit} className="bg-bg-card rounded-2xl border border-white/5 p-4 space-y-3">
      <div className="text-text-primary text-sm font-semibold mb-2">New Paper Trade</div>

      {/* Direction */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => updateDefaults('LONG')}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            direction === 'LONG' ? 'bg-accent-green text-white' : 'bg-bg-hover text-text-muted'
          }`}
        >
          LONG
        </button>
        <button
          type="button"
          onClick={() => updateDefaults('SHORT')}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            direction === 'SHORT' ? 'bg-accent-red text-white' : 'bg-bg-hover text-text-muted'
          }`}
        >
          SHORT
        </button>
      </div>

      {/* Price inputs */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-[9px] text-text-muted block mb-1">Entry Price</label>
          <input
            type="number"
            value={entry}
            onChange={(e) => setEntry(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
            required
          />
        </div>
        <div>
          <label className="text-[9px] text-text-muted block mb-1">Stop Loss</label>
          <input
            type="number"
            value={sl}
            onChange={(e) => setSl(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
            required
          />
        </div>
        <div>
          <label className="text-[9px] text-text-muted block mb-1">Take Profit</label>
          <input
            type="number"
            value={tp}
            onChange={(e) => setTp(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
            required
          />
        </div>
      </div>

      {/* Leverage & Size */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-text-muted block mb-1">Leverage ({leverage}x)</label>
          <input
            type="range"
            min="1"
            max="125"
            value={leverage}
            onChange={(e) => setLeverage(e.target.value)}
            className="w-full accent-accent-blue"
          />
        </div>
        <div>
          <label className="text-[9px] text-text-muted block mb-1">Size (USDT)</label>
          <input
            type="number"
            value={size}
            onChange={(e) => setSize(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
            required
          />
        </div>
      </div>

      {/* Risk metrics */}
      <div className="grid grid-cols-3 gap-2 text-center py-2 bg-bg-hover rounded-lg">
        <div>
          <div className="text-[9px] text-text-muted">Risk</div>
          <div className="text-xs font-bold text-accent-red">{riskPct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-[9px] text-text-muted">R:R</div>
          <div className={`text-xs font-bold ${parseFloat(rrRatio) >= 2 ? 'text-accent-green' : 'text-accent-yellow'}`}>{rrRatio}</div>
        </div>
        <div>
          <div className="text-[9px] text-text-muted">Risk $</div>
          <div className="text-xs font-bold text-accent-red">${riskUsdt.toFixed(2)}</div>
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className={`w-full py-2.5 rounded-lg text-xs font-bold transition-all ${
          direction === 'LONG'
            ? 'bg-accent-green text-white hover:bg-accent-green/80'
            : 'bg-accent-red text-white hover:bg-accent-red/80'
        } disabled:opacity-50`}
      >
        {submitting ? 'Opening...' : `Open ${direction} Paper Trade`}
      </button>
    </form>
  )
}

function MockTradeCard({ trade, currentPrice, onClose }) {
  const isLong = trade.direction === 'LONG'
  const price = trade.current_price || currentPrice || 0
  const pnlPct = trade.unrealized_pnl_pct || (trade.entry_price ? ((price - trade.entry_price) / trade.entry_price * 100 * (isLong ? 1 : -1) * (trade.leverage || 1)) : 0)

  return (
    <div className={`bg-bg-card rounded-xl border p-3 ${pnlPct >= 0 ? 'border-accent-green/20' : 'border-accent-red/20'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
            isLong ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'
          }`}>
            {trade.direction}
          </span>
          <span className="text-text-primary text-sm font-semibold">BTC/USDT</span>
          <span className="text-text-muted text-[9px]">{trade.leverage}x</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-yellow/15 text-accent-yellow">PAPER</span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div>
          <div className="text-text-muted text-[9px]">Entry</div>
          <div className="font-mono tabular-nums">{formatPrice(trade.entry_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">Current</div>
          <div className="font-mono tabular-nums">{formatPrice(price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">Size</div>
          <div className="font-mono tabular-nums">${trade.position_size_usdt}</div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">P&L</div>
          <div className={`font-bold tabular-nums ${pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
        <span className="text-text-muted text-[9px]">{formatTimeAgo(trade.timestamp)}</span>
        <button
          onClick={() => onClose(trade.id, price)}
          className="text-[10px] px-3 py-1 rounded-lg bg-accent-red/15 text-accent-red font-medium hover:bg-accent-red/25 transition-colors"
        >
          Close Trade
        </button>
      </div>
    </div>
  )
}

export default function MockTrading() {
  const { user } = useTelegram()
  const telegramId = user?.id || 0

  const [trades, setTrades] = useState([])
  const [history, setHistory] = useState([])
  const [currentPrice, setCurrentPrice] = useState(0)
  const [tab, setTab] = useState('trade')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const [mockTrades, mockHist, priceData] = await Promise.all([
        telegramId ? api.getMockTrades(telegramId) : { trades: [], current_price: 0 },
        telegramId ? api.getMockHistory(telegramId) : { results: [] },
        api.getCurrentPrice(),
      ])
      setTrades(mockTrades?.trades || [])
      setHistory(mockHist?.results || [])
      setCurrentPrice(mockTrades?.current_price || priceData?.price || priceData?.close || 0)
    } catch (err) {
      console.error('Mock trading data error:', err)
    } finally {
      setLoading(false)
    }
  }, [telegramId])

  useEffect(() => { fetchData() }, [fetchData])

  const handleSubmit = async (tradeData) => {
    if (!telegramId) {
      alert('Login via Telegram to save paper trades')
    }
    setSubmitting(true)
    try {
      await api.createMockTrade(telegramId || 0, tradeData)
      fetchData()
      setTab('active')
    } catch (err) {
      console.error('Create mock trade error:', err)
      alert('Failed to create trade: ' + (err.message || 'Unknown error'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleClose = async (tradeId, price) => {
    if (!window.confirm(`Close paper trade #${tradeId} at $${price?.toLocaleString()}?`)) return
    try {
      await api.closeTrade(tradeId, price, 'manual_close')
      fetchData()
    } catch (err) {
      console.error('Close mock trade error:', err)
    }
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">Paper Trading</h1>

      <SubTabBar tabs={ADVISOR_TABS} />

      {/* Current price banner */}
      {currentPrice > 0 && (
        <div className="bg-bg-card rounded-xl border border-white/5 p-3 flex items-center justify-between">
          <span className="text-text-muted text-xs">BTC/USDT</span>
          <span className="text-text-primary text-lg font-bold tabular-nums">{formatPrice(currentPrice)}</span>
        </div>
      )}

      {/* Inner tabs */}
      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {['trade', 'active', 'history'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              tab === t ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t === 'trade' ? 'New Trade' : t === 'active' ? `Active (${trades.length})` : `History (${history.length})`}
          </button>
        ))}
      </div>

      {tab === 'trade' && (
        <TradeForm currentPrice={currentPrice} onSubmit={handleSubmit} submitting={submitting} />
      )}

      {tab === 'active' && (
        loading ? (
          <div className="animate-pulse space-y-3">
            <div className="h-20 bg-bg-card rounded-2xl" />
          </div>
        ) : trades.length > 0 ? (
          <div className="space-y-2">
            {trades.map((t, i) => (
              <MockTradeCard key={t.id || i} trade={t} currentPrice={currentPrice} onClose={handleClose} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">No active paper trades</p>
            <p className="text-text-muted text-xs mt-1">Create one in the New Trade tab to practice.</p>
          </div>
        )
      )}

      {tab === 'history' && (
        history.length > 0 ? (
          <div className="space-y-2">
            {history.map((t, i) => {
              const won = t.was_winner
              const isLong = t.direction === 'LONG'
              return (
                <div key={t.id || i} className={`bg-bg-card rounded-xl border p-3 ${won ? 'border-accent-green/10' : 'border-accent-red/10'}`}>
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
                        {t.direction}
                      </span>
                      <span className="text-text-muted text-[9px]">{t.leverage}x</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-yellow/15 text-accent-yellow">PAPER</span>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-bold tabular-nums ${t.pnl_usdt >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                        {t.pnl_usdt >= 0 ? '+' : ''}{formatPrice(t.pnl_usdt)}
                      </span>
                      <span className={`text-[9px] ml-1 ${t.pnl_pct_leveraged >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                        ({t.pnl_pct_leveraged >= 0 ? '+' : ''}{t.pnl_pct_leveraged?.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[9px] text-text-muted">
                    <span>{formatPrice(t.entry_price)} &rarr; {formatPrice(t.exit_price)}</span>
                    <span>{formatTimeAgo(t.timestamp)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <p className="text-text-muted text-sm">No paper trade history</p>
          </div>
        )
      )}

      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        Paper trading uses virtual money. No real funds are at risk. Practice your strategies risk-free.
      </p>
    </div>
  )
}
