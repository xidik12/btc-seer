import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { useTutorial } from '../hooks/useTutorial'
import { formatPrice, formatPercent, formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'
import TutorialOverlay from '../components/tutorial/TutorialOverlay'

const ADVISOR_TABS = [
  { path: '/advisor', label: 'AI Advisor' },
  { path: '/mock-trading', label: 'Paper Trading' },
  { path: '/history', label: 'History' },
]

const LEVERAGE_PRESETS = [1, 2, 5, 10, 20, 50, 75, 125]
const BALANCE = 10000 // Virtual starting balance

// ─── Liquidation price calculator ──────────────────────────
function calcLiquidation(entry, leverage, direction, fee = 0.0006) {
  if (!entry || !leverage || leverage <= 0) return 0
  if (direction === 'LONG') {
    return entry * (1 - 1 / leverage + fee)
  }
  return entry * (1 + 1 / leverage - fee)
}

// ─── TP Progress bar (reused from Advisor) ─────────────────
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

// ─── Order Form ────────────────────────────────────────────
function OrderForm({ currentPrice, onSubmit, submitting }) {
  const [direction, setDirection] = useState('LONG')
  const [orderType, setOrderType] = useState('market')
  const [positionMode, setPositionMode] = useState('one-way')
  const [marginMode, setMarginMode] = useState('isolated')
  const [entry, setEntry] = useState('')
  const [leverage, setLeverage] = useState(5)
  const [size, setSize] = useState('10')
  const [sl, setSl] = useState('')
  const [tp1, setTp1] = useState('')
  const [tp2, setTp2] = useState('')
  const [tp3, setTp3] = useState('')

  // Auto-fill entry price and defaults
  useEffect(() => {
    if (currentPrice) {
      if (orderType === 'market' || !entry) {
        setEntry(currentPrice.toFixed(0))
      }
      if (!sl) {
        const slPct = direction === 'LONG' ? 0.98 : 1.02
        setSl((currentPrice * slPct).toFixed(0))
      }
      if (!tp1) {
        const mult = direction === 'LONG' ? [1.02, 1.04, 1.06] : [0.98, 0.96, 0.94]
        setTp1((currentPrice * mult[0]).toFixed(0))
        setTp2((currentPrice * mult[1]).toFixed(0))
        setTp3((currentPrice * mult[2]).toFixed(0))
      }
    }
  }, [currentPrice])

  const updateDirection = (dir) => {
    setDirection(dir)
    const price = parseFloat(entry) || currentPrice || 0
    if (price) {
      const slPct = dir === 'LONG' ? 0.98 : 1.02
      const mult = dir === 'LONG' ? [1.02, 1.04, 1.06] : [0.98, 0.96, 0.94]
      setSl((price * slPct).toFixed(0))
      setTp1((price * mult[0]).toFixed(0))
      setTp2((price * mult[1]).toFixed(0))
      setTp3((price * mult[2]).toFixed(0))
    }
  }

  const entryNum = parseFloat(entry) || 0
  const slNum = parseFloat(sl) || 0
  const tp1Num = parseFloat(tp1) || 0
  const tp2Num = parseFloat(tp2) || 0
  const tp3Num = parseFloat(tp3) || 0
  const sizeNum = parseFloat(size) || 0
  const notional = sizeNum * leverage

  const riskPct = entryNum ? Math.abs(entryNum - slNum) / entryNum * 100 : 0
  const rewardPct = entryNum && tp3Num ? Math.abs(tp3Num - entryNum) / entryNum * 100 : 0
  const rrRatio = riskPct > 0 ? (rewardPct / riskPct).toFixed(1) : '0'
  const riskUsdt = sizeNum * (riskPct / 100) * leverage
  const maxGain = sizeNum * (rewardPct / 100) * leverage
  const liqPrice = calcLiquidation(entryNum, leverage, direction)

  const slDistPct = entryNum ? (Math.abs(entryNum - slNum) / entryNum * 100).toFixed(2) : '0'
  const tp1RR = riskPct > 0 ? (Math.abs(tp1Num - entryNum) / entryNum * 100 / riskPct).toFixed(1) : '0'
  const tp2RR = riskPct > 0 ? (Math.abs(tp2Num - entryNum) / entryNum * 100 / riskPct).toFixed(1) : '0'
  const tp3RR = riskPct > 0 ? (Math.abs(tp3Num - entryNum) / entryNum * 100 / riskPct).toFixed(1) : '0'

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      direction,
      entry_price: entryNum,
      stop_loss: slNum,
      take_profit_1: tp1Num,
      take_profit_2: tp2Num || undefined,
      take_profit_3: tp3Num || undefined,
      leverage,
      position_size_usdt: sizeNum,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Mode Selectors */}
      <div className="flex gap-2" data-tutorial="position-mode">
        <div className="flex-1">
          <label className="text-[9px] text-text-muted block mb-1">Position Mode</label>
          <div className="flex bg-bg-hover rounded-lg p-0.5">
            {['one-way', 'hedge'].map(m => (
              <button
                key={m}
                type="button"
                onClick={() => setPositionMode(m)}
                className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
                  positionMode === m ? 'bg-accent-blue text-white' : 'text-text-muted'
                }`}
              >
                {m === 'one-way' ? 'One-Way' : 'Hedge'}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1" data-tutorial="margin-mode">
          <label className="text-[9px] text-text-muted block mb-1">Margin Mode</label>
          <div className="flex bg-bg-hover rounded-lg p-0.5">
            {['cross', 'isolated'].map(m => (
              <button
                key={m}
                type="button"
                onClick={() => setMarginMode(m)}
                className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
                  marginMode === m ? 'bg-accent-blue text-white' : 'text-text-muted'
                }`}
              >
                {m === 'cross' ? 'Cross' : 'Isolated'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Order Type Tabs */}
      <div data-tutorial="order-type">
        <div className="flex bg-bg-hover rounded-lg p-0.5">
          {['market', 'limit'].map(t => (
            <button
              key={t}
              type="button"
              onClick={() => {
                setOrderType(t)
                if (t === 'market' && currentPrice) setEntry(currentPrice.toFixed(0))
              }}
              className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
                orderType === t ? 'bg-accent-blue text-white' : 'text-text-muted'
              }`}
            >
              {t === 'market' ? 'Market' : 'Limit'}
            </button>
          ))}
        </div>
      </div>

      {/* Direction */}
      <div className="flex gap-2" data-tutorial="direction">
        <button
          type="button"
          onClick={() => updateDirection('LONG')}
          className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all ${
            direction === 'LONG' ? 'bg-accent-green text-white shadow-lg shadow-accent-green/20' : 'bg-bg-hover text-text-muted hover:text-accent-green'
          }`}
        >
          LONG
        </button>
        <button
          type="button"
          onClick={() => updateDirection('SHORT')}
          className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all ${
            direction === 'SHORT' ? 'bg-accent-red text-white shadow-lg shadow-accent-red/20' : 'bg-bg-hover text-text-muted hover:text-accent-red'
          }`}
        >
          SHORT
        </button>
      </div>

      {/* Entry Price */}
      <div data-tutorial="entry-price">
        <label className="text-[9px] text-text-muted block mb-1">
          Entry Price {orderType === 'market' ? '(Market)' : '(Limit)'}
        </label>
        <input
          type="number"
          value={entry}
          onChange={(e) => setEntry(e.target.value)}
          readOnly={orderType === 'market'}
          className={`w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums ${
            orderType === 'market' ? 'opacity-60 cursor-not-allowed' : ''
          }`}
          required
        />
      </div>

      {/* Leverage */}
      <div data-tutorial="leverage">
        <label className="text-[9px] text-text-muted block mb-1">
          Leverage <span className="text-accent-green font-bold">{leverage}x</span>
          <span className="float-right">Margin: ${(sizeNum).toFixed(2)}</span>
        </label>
        <div className="flex flex-wrap gap-1 mb-2">
          {LEVERAGE_PRESETS.map(lev => (
            <button
              key={lev}
              type="button"
              onClick={() => setLeverage(lev)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all ${
                leverage === lev ? 'bg-accent-green text-white' : 'bg-bg-hover text-text-muted hover:text-text-secondary'
              }`}
            >
              {lev}x
            </button>
          ))}
        </div>
        <input
          type="range"
          min="1"
          max="125"
          value={leverage}
          onChange={(e) => setLeverage(parseInt(e.target.value))}
          className="w-full accent-accent-green h-1"
        />
      </div>

      {/* Position Size */}
      <div data-tutorial="size">
        <label className="text-[9px] text-text-muted block mb-1">
          Size (USDT)
          <span className="float-right text-accent-green">Notional: ${notional.toLocaleString()}</span>
        </label>
        <input
          type="number"
          value={size}
          onChange={(e) => setSize(e.target.value)}
          className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums"
          required
        />
        <div className="flex gap-1 mt-1">
          {[25, 50, 75, 100].map(pct => (
            <button
              key={pct}
              type="button"
              onClick={() => setSize((BALANCE * pct / 100).toFixed(0))}
              className="flex-1 py-1 rounded-md text-[10px] font-semibold bg-bg-hover text-text-muted hover:text-text-secondary transition-colors"
            >
              {pct}%
            </button>
          ))}
        </div>
      </div>

      {/* Stop Loss */}
      <div data-tutorial="stop-loss">
        <label className="text-[9px] text-text-muted block mb-1">
          Stop Loss
          <span className="float-right text-accent-red">-{slDistPct}% | Risk: ${riskUsdt.toFixed(2)}</span>
        </label>
        <input
          type="number"
          value={sl}
          onChange={(e) => setSl(e.target.value)}
          className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums"
          required
        />
      </div>

      {/* Take Profit Matrix */}
      <div className="space-y-2">
        <div data-tutorial="tp1">
          <label className="text-[9px] text-text-muted block mb-1">
            TP1 — Close 40%
            <span className="float-right text-accent-green">R:R {tp1RR}</span>
          </label>
          <input
            type="number"
            value={tp1}
            onChange={(e) => setTp1(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums"
          />
        </div>
        <div data-tutorial="tp2">
          <label className="text-[9px] text-text-muted block mb-1">
            TP2 — Close 40%
            <span className="float-right text-accent-green">R:R {tp2RR}</span>
          </label>
          <input
            type="number"
            value={tp2}
            onChange={(e) => setTp2(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums"
          />
        </div>
        <div data-tutorial="tp3">
          <label className="text-[9px] text-text-muted block mb-1">
            TP3 — Close 20%
            <span className="float-right text-accent-green">R:R {tp3RR}</span>
          </label>
          <input
            type="number"
            value={tp3}
            onChange={(e) => setTp3(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary font-mono tabular-nums"
          />
        </div>
      </div>

      {/* Order Preview */}
      <div data-tutorial="preview" className="bg-bg-hover/60 border border-white/5 rounded-xl p-3">
        <div className="text-[10px] text-text-muted font-semibold mb-2">ORDER PREVIEW</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
          <div className="flex justify-between">
            <span className="text-text-muted">Direction</span>
            <span className={direction === 'LONG' ? 'text-accent-green font-bold' : 'text-accent-red font-bold'}>
              {direction}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Leverage</span>
            <span className="text-text-primary font-semibold">{leverage}x</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Entry</span>
            <span className="text-text-primary font-mono tabular-nums">{formatPrice(entryNum)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Notional</span>
            <span className="text-text-primary font-mono tabular-nums">${notional.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Margin</span>
            <span className="text-text-primary font-mono tabular-nums">${sizeNum.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Liq. Price</span>
            <span className="text-accent-red font-mono tabular-nums">{formatPrice(liqPrice)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Max Loss</span>
            <span className="text-accent-red font-bold">-${riskUsdt.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Max Gain</span>
            <span className="text-accent-green font-bold">+${maxGain.toFixed(2)}</span>
          </div>
          <div className="col-span-2 flex justify-between border-t border-white/5 pt-1.5 mt-1">
            <span className="text-text-muted">R:R Ratio</span>
            <span className={`font-bold ${parseFloat(rrRatio) >= 2 ? 'text-accent-green' : 'text-accent-yellow'}`}>
              {rrRatio}
            </span>
          </div>
        </div>
      </div>

      {/* Submit */}
      <button
        data-tutorial="submit"
        type="submit"
        disabled={submitting || !entryNum || !slNum}
        className={`w-full py-3.5 rounded-xl text-sm font-bold transition-all ${
          direction === 'LONG'
            ? 'bg-accent-green text-white shadow-lg shadow-accent-green/20 hover:bg-accent-green/90'
            : 'bg-accent-red text-white shadow-lg shadow-accent-red/20 hover:bg-accent-red/90'
        } disabled:opacity-40 disabled:shadow-none`}
      >
        {submitting ? 'Opening...' : `Open ${direction}`}
      </button>
    </form>
  )
}

// ─── Active Position Card ──────────────────────────────────
function PositionCard({ trade, currentPrice, onClose }) {
  const isLong = trade.direction === 'LONG'
  const price = trade.current_price || currentPrice || 0
  const pnlPct = trade.unrealized_pnl_pct || (trade.entry_price ? ((price - trade.entry_price) / trade.entry_price * 100 * (isLong ? 1 : -1) * (trade.leverage || 1)) : 0)
  const pnlUsdt = (trade.position_size_usdt || 0) * (pnlPct / 100)
  const liqPrice = calcLiquidation(trade.entry_price, trade.leverage, trade.direction)
  const targets = [trade.take_profit_1, trade.take_profit_2, trade.take_profit_3].filter(Boolean)

  return (
    <div className={`bg-bg-card rounded-xl border p-3 ${pnlPct >= 0 ? 'border-accent-green/20' : 'border-accent-red/20'}`}>
      {/* Header */}
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
        <div className={`text-sm font-bold tabular-nums ${pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
          {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
        </div>
      </div>

      {/* Price Grid */}
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
          <div className="text-text-muted text-[9px]">Liq. Price</div>
          <div className="font-mono tabular-nums text-accent-red">{formatPrice(liqPrice)}</div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">PnL</div>
          <div className={`font-bold tabular-nums ${pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {pnlUsdt >= 0 ? '+' : ''}${Math.abs(pnlUsdt).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Margin & Size */}
      <div className="flex items-center justify-between mt-2 text-[9px] text-text-muted">
        <span>Margin: ${trade.position_size_usdt}</span>
        <span>Notional: ${((trade.position_size_usdt || 0) * (trade.leverage || 1)).toLocaleString()}</span>
        <span>{formatTimeAgo(trade.timestamp)}</span>
      </div>

      {/* TP Progress */}
      {targets.length > 0 && (
        <TPProgress
          currentPrice={price}
          entry={trade.entry_price}
          targets={targets}
          stopLoss={trade.stop_loss}
        />
      )}

      {/* Close button */}
      <div className="flex justify-end mt-2 pt-2 border-t border-white/5">
        <button
          onClick={() => onClose(trade.id, price)}
          className="text-[10px] px-4 py-1.5 rounded-lg bg-accent-red/15 text-accent-red font-semibold hover:bg-accent-red/25 transition-colors"
        >
          Close Position
        </button>
      </div>
    </div>
  )
}

// ─── History Row ───────────────────────────────────────────
function HistoryRow({ trade }) {
  const won = trade.was_winner
  const isLong = trade.direction === 'LONG'

  return (
    <div className={`bg-bg-card rounded-xl border p-3 ${won ? 'border-accent-green/10' : 'border-accent-red/10'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-5 h-5 rounded-full flex items-center justify-center ${
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
            {trade.direction}
          </span>
          <span className="text-text-muted text-[9px]">{trade.leverage}x</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-yellow/15 text-accent-yellow">PAPER</span>
        </div>
        <div className="text-right">
          <span className={`text-xs font-bold tabular-nums ${trade.pnl_usdt >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {trade.pnl_usdt >= 0 ? '+' : ''}{formatPrice(trade.pnl_usdt)}
          </span>
          <span className={`text-[9px] ml-1 ${trade.pnl_pct_leveraged >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            ({trade.pnl_pct_leveraged >= 0 ? '+' : ''}{trade.pnl_pct_leveraged?.toFixed(1)}%)
          </span>
        </div>
      </div>
      <div className="flex items-center justify-between mt-1 text-[9px] text-text-muted">
        <span>{formatPrice(trade.entry_price)} &rarr; {formatPrice(trade.exit_price)}</span>
        <div className="flex items-center gap-2">
          {trade.close_reason && (
            <span className="px-1.5 py-0.5 rounded bg-bg-hover text-text-muted">{trade.close_reason}</span>
          )}
          <span>{formatTimeAgo(trade.timestamp)}</span>
        </div>
      </div>
    </div>
  )
}

// ─── Portfolio Summary ─────────────────────────────────────
function PortfolioSummary({ trades, history }) {
  const totalPnl = useMemo(() => {
    return (history || []).reduce((sum, t) => sum + (t.pnl_usdt || 0), 0)
  }, [history])

  const winRate = useMemo(() => {
    if (!history?.length) return 0
    const wins = history.filter(t => t.was_winner).length
    return (wins / history.length * 100)
  }, [history])

  const balance = BALANCE + totalPnl
  const progressPct = Math.min(100, Math.max(0, (balance / 10000) * 100))

  return (
    <div className="bg-bg-card rounded-xl border border-white/5 p-3">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-text-muted text-[9px]">BALANCE</div>
          <div className="text-text-primary text-lg font-bold tabular-nums">${balance.toFixed(2)}</div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">TOTAL P&L</div>
          <div className={`text-lg font-bold tabular-nums ${totalPnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center mb-3">
        <div>
          <div className="text-text-muted text-[9px]">Win Rate</div>
          <div className="text-text-primary text-sm font-bold">{winRate.toFixed(0)}%</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">Total Trades</div>
          <div className="text-text-primary text-sm font-bold">{(history || []).length}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">Active</div>
          <div className="text-text-primary text-sm font-bold">{(trades || []).length}</div>
        </div>
      </div>
      {/* Progress bar: $10 → $10,000 journey */}
      <div>
        <div className="flex justify-between text-[9px] text-text-muted mb-1">
          <span>$10</span>
          <span>$10,000 Goal</span>
        </div>
        <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-green rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════
export default function MockTrading() {
  const { user } = useTelegram()
  const telegramId = user?.id || 0
  const tutorial = useTutorial()

  const [trades, setTrades] = useState([])
  const [history, setHistory] = useState([])
  const [currentPrice, setCurrentPrice] = useState(0)
  const [priceChange, setPriceChange] = useState(0)
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
      setPriceChange(priceData?.change_24h || priceData?.change_pct || 0)
    } catch (err) {
      console.error('Mock trading data error:', err)
    } finally {
      setLoading(false)
    }
  }, [telegramId])

  useEffect(() => { fetchData() }, [fetchData])

  // Auto-refresh price every 15s
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const priceData = await api.getCurrentPrice()
        setCurrentPrice(priceData?.price || priceData?.close || 0)
        setPriceChange(priceData?.change_24h || priceData?.change_pct || 0)
      } catch {}
    }, 15000)
    return () => clearInterval(interval)
  }, [])

  const handleSubmit = async (tradeData) => {
    if (!telegramId) {
      alert('Login via Telegram to save paper trades')
      return
    }
    setSubmitting(true)
    try {
      await api.createMockTrade(telegramId, tradeData)
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
    if (!window.confirm(`Close position at ${formatPrice(price)}?`)) return
    try {
      await api.closeTrade(tradeId, price, 'manual_close')
      fetchData()
    } catch (err) {
      console.error('Close mock trade error:', err)
    }
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      {/* Tutorial Overlay */}
      <TutorialOverlay tutorial={tutorial} />

      {/* Header */}
      <div className="flex items-center justify-between" data-tutorial="header">
        <div>
          <h1 className="text-lg font-bold text-text-primary">Paper Trading</h1>
          <div className="text-text-muted text-[10px]">Practice risk-free</div>
        </div>
        <div className="flex items-center gap-2">
          {tutorial.completed && (
            <button
              onClick={tutorial.restart}
              className="text-[9px] px-2 py-1 rounded-md bg-bg-hover text-text-muted hover:text-text-secondary transition-colors"
            >
              ? Tutorial
            </button>
          )}
        </div>
      </div>

      <SubTabBar tabs={ADVISOR_TABS} />

      {/* Price Banner */}
      {currentPrice > 0 && (
        <div className="bg-bg-card rounded-xl border border-white/5 p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-text-muted text-xs">BTC/USDT</span>
            {priceChange !== 0 && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                priceChange >= 0 ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'
              }`}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
              </span>
            )}
          </div>
          <span className={`text-xl font-bold tabular-nums ${
            priceChange >= 0 ? 'text-accent-green' : 'text-accent-red'
          }`}>
            {formatPrice(currentPrice)}
          </span>
        </div>
      )}

      {/* Inner Tabs */}
      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {[
          { key: 'trade', label: 'New Trade' },
          { key: 'active', label: `Active (${trades.length})` },
          { key: 'history', label: `History (${history.length})` },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            data-tutorial={t.key === 'history' ? 'history-tab' : undefined}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              tab === t.key ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── New Trade Tab ─── */}
      {tab === 'trade' && (
        <OrderForm currentPrice={currentPrice} onSubmit={handleSubmit} submitting={submitting} />
      )}

      {/* ─── Active Positions Tab ─── */}
      {tab === 'active' && (
        <div data-tutorial="positions">
          {loading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-24 bg-bg-card rounded-2xl" />
            </div>
          ) : trades.length > 0 ? (
            <div className="space-y-2">
              {trades.map((t, i) => (
                <PositionCard key={t.id || i} trade={t} currentPrice={currentPrice} onClose={handleClose} />
              ))}
            </div>
          ) : (
            <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
              <div className="text-2xl mb-2">📊</div>
              <p className="text-text-muted text-sm">No active positions</p>
              <p className="text-text-muted text-xs mt-1">Open a trade to start practicing.</p>
            </div>
          )}
        </div>
      )}

      {/* ─── History Tab ─── */}
      {tab === 'history' && (
        history.length > 0 ? (
          <div className="space-y-2">
            {history.map((t, i) => (
              <HistoryRow key={t.id || i} trade={t} />
            ))}
          </div>
        ) : (
          <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
            <div className="text-2xl mb-2">📈</div>
            <p className="text-text-muted text-sm">No trade history</p>
            <p className="text-text-muted text-xs mt-1">Completed trades will appear here.</p>
          </div>
        )
      )}

      {/* Portfolio Summary */}
      <div data-tutorial="portfolio">
        <PortfolioSummary trades={trades} history={history} />
      </div>

      {/* Disclaimer */}
      <p className="text-text-muted text-[10px] text-center pb-4 leading-relaxed">
        Paper trading uses virtual money. No real funds at risk. Practice your strategies risk-free.
      </p>
    </div>
  )
}
