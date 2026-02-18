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

function PortfolioSettingsCard({ portfolio, telegramId, initData, onSave, isNew, t }) {
  const [balance, setBalance] = useState(String(portfolio?.balance || 10))
  const [maxLeverage, setMaxLeverage] = useState(String(portfolio?.max_leverage || 20))
  const [maxOpenTrades, setMaxOpenTrades] = useState(String(portfolio?.max_open_trades || 3))
  const [riskPct, setRiskPct] = useState(String(portfolio?.max_risk_per_trade_pct || 10))
  const [saving, setSaving] = useState(false)
  const [collapsed, setCollapsed] = useState(!isNew)

  useEffect(() => {
    if (portfolio) {
      setBalance(String(portfolio.balance || portfolio.balance_usdt || 10))
      setMaxLeverage(String(portfolio.max_leverage || 20))
      setMaxOpenTrades(String(portfolio.max_open_trades || 3))
      setRiskPct(String(portfolio.max_risk_per_trade_pct || 10))
    }
  }, [portfolio])

  const handleSave = async () => {
    setSaving(true)
    try {
      const settings = {
        balance: Number(balance) || 1,
        max_leverage: Number(maxLeverage) || 1,
        max_open_trades: Number(maxOpenTrades) || 1,
        max_risk_per_trade_pct: Number(riskPct) || 1,
      }
      if (isNew) {
        await api.setupPortfolio(initData, telegramId, settings)
      } else {
        await api.updatePortfolio(initData, telegramId, settings)
      }
      onSave()
      if (!isNew) setCollapsed(true)
    } catch (err) {
      console.error('Portfolio save error:', err)
    } finally {
      setSaving(false)
    }
  }

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="w-full flex items-center justify-between bg-bg-card rounded-xl p-3 border border-white/5 hover:bg-bg-hover transition-colors slide-up"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
          </svg>
          <span className="text-text-secondary text-xs font-medium">{t('advisor.editPortfolio')}</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-text-muted">
          <span>${balance}</span>
          <span>{maxLeverage}x</span>
          <span>{riskPct}%</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </div>
      </button>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-accent-blue/20 slide-up">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-accent-blue/10 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <div className="text-text-primary text-sm font-bold">
            {isNew ? t('advisor.setUpPortfolio') : t('advisor.editPortfolio')}
          </div>
        </div>
        {!isNew && (
          <button onClick={() => setCollapsed(true)} className="text-text-muted text-[10px] hover:text-text-secondary">
            {t('btn.close', { ns: 'common' })}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('advisor.balance')}</label>
          <input type="number" value={balance} onChange={e => setBalance(e.target.value)} min={1}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50" />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('trade.leverage', { ns: 'common' })}</label>
          <input type="number" value={maxLeverage} onChange={e => setMaxLeverage(e.target.value)} min={1} max={125}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50" />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('portfolio.totalTrades')}</label>
          <input type="number" value={maxOpenTrades} onChange={e => setMaxOpenTrades(e.target.value)} min={1} max={20}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50" />
        </div>
        <div>
          <label className="text-text-muted text-[10px] block mb-1">{t('advisor.riskLevel')}</label>
          <input type="number" value={riskPct} onChange={e => setRiskPct(e.target.value)} min={1} max={100}
            className="w-full bg-bg-secondary border border-white/10 rounded-lg px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-accent-blue/50" />
        </div>
      </div>

      <button onClick={handleSave} disabled={saving}
        className="w-full py-2.5 rounded-xl bg-accent-blue text-white text-xs font-bold hover:bg-accent-blue/90 transition-colors disabled:opacity-50">
        {saving ? t('app.loading', { ns: 'common' }) : isNew ? t('advisor.setUpPortfolio') : t('btn.save', { ns: 'common' })}
      </button>
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

function AnalysisCard({ analysis, t }) {
  if (!analysis) return null

  const pred = analysis.prediction || {}
  const quant = analysis.quant || {}
  const ew = analysis.elliott_wave || {}
  const pl = analysis.power_law || {}
  const ind = analysis.indicators || {}

  const dirColor = pred.direction === 'bullish' ? 'text-accent-green' : pred.direction === 'bearish' ? 'text-accent-red' : 'text-text-muted'
  const quantColor = (quant.composite_score || 0) > 0 ? 'text-accent-green' : (quant.composite_score || 0) < 0 ? 'text-accent-red' : 'text-text-muted'

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up space-y-3">
      <div className="text-text-muted text-[10px] font-bold uppercase tracking-wide">{t('advisor.fullAnalysis')}</div>

      {/* ML Ensemble */}
      <div className="flex items-center justify-between">
        <span className="text-text-muted text-[10px]">{t('advisor.mlEnsemble')}</span>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold ${dirColor}`}>{(pred.direction || '').toUpperCase()}</span>
          <span className="text-text-muted text-[10px]">{pred.confidence?.toFixed(0)}%</span>
        </div>
      </div>

      {/* Quant Theory */}
      {quant.composite_score != null && (
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-[10px]">{t('advisor.quantTheory')}</span>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold ${quantColor}`}>{quant.action || 'N/A'}</span>
            <span className="text-text-muted text-[10px]">{quant.composite_score > 0 ? '+' : ''}{quant.composite_score?.toFixed(0)}/100</span>
          </div>
        </div>
      )}

      {/* Elliott Wave */}
      {ew.pattern && ew.pattern !== 'no_data' && ew.pattern !== 'insufficient_data' && (
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-[10px]">{t('advisor.elliottWave')}</span>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold ${ew.direction === 'bullish' ? 'text-accent-green' : ew.direction === 'bearish' ? 'text-accent-red' : 'text-text-muted'}`}>
              W{ew.current_wave} {ew.pattern}
            </span>
            <span className="text-text-muted text-[10px]">{(ew.confidence * 100)?.toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* Power Law */}
      {pl && pl.fair_value && (
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-[10px]">{t('advisor.powerLaw')}</span>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold ${pl.deviation_pct < 0 ? 'text-accent-green' : pl.deviation_pct > 30 ? 'text-accent-red' : 'text-text-muted'}`}>
              {pl.zone?.replace('_', ' ')}
            </span>
            <span className="text-text-muted text-[10px]">{pl.deviation_pct > 0 ? '+' : ''}{pl.deviation_pct?.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* Key Indicators */}
      <div className="pt-2 border-t border-white/5 grid grid-cols-3 gap-2">
        {ind.rsi != null && (
          <div className="text-center">
            <div className="text-text-muted text-[8px]">RSI</div>
            <div className={`text-[11px] font-bold ${ind.rsi > 70 ? 'text-accent-red' : ind.rsi < 30 ? 'text-accent-green' : 'text-text-primary'}`}>
              {ind.rsi?.toFixed(0)}
            </div>
          </div>
        )}
        {ind.fear_greed != null && (
          <div className="text-center">
            <div className="text-text-muted text-[8px]">F&G</div>
            <div className={`text-[11px] font-bold ${ind.fear_greed > 70 ? 'text-accent-red' : ind.fear_greed < 30 ? 'text-accent-green' : 'text-text-primary'}`}>
              {ind.fear_greed?.toFixed(0)}
            </div>
          </div>
        )}
        {ind.funding_rate != null && (
          <div className="text-center">
            <div className="text-text-muted text-[8px]">Funding</div>
            <div className={`text-[11px] font-bold ${ind.funding_rate > 0.0005 ? 'text-accent-red' : ind.funding_rate < -0.0001 ? 'text-accent-green' : 'text-text-primary'}`}>
              {(ind.funding_rate * 100)?.toFixed(3)}%
            </div>
          </div>
        )}
      </div>

      {/* Elliott Wave Summary */}
      {ew.summary && (
        <p className="text-text-muted text-[10px] leading-relaxed pt-1 border-t border-white/5">{ew.summary}</p>
      )}
    </div>
  )
}

function AIAccuracyCard({ feedback, t }) {
  if (!feedback || feedback.total_trades === 0) return null

  const winRate = feedback.total_trades > 0
    ? (feedback.winning_trades / feedback.total_trades * 100).toFixed(0)
    : 0

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="text-text-muted text-[10px] font-medium mb-2">{t('advisor.aiAccuracyLabel', { days: feedback.days })}</div>
      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('advisor.directionLabel')}</div>
          <div className={`text-sm font-bold ${feedback.direction_accuracy >= 55 ? 'text-accent-green' : 'text-accent-red'}`}>
            {feedback.direction_accuracy.toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('advisor.winRateLabel')}</div>
          <div className={`text-sm font-bold ${Number(winRate) >= 50 ? 'text-accent-green' : 'text-accent-red'}`}>
            {winRate}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('advisor.avgRRLabel')}</div>
          <div className={`text-sm font-bold ${feedback.avg_achieved_rr >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {feedback.avg_achieved_rr.toFixed(1)}
          </div>
        </div>
      </div>
      {feedback.confidence_calibration && Object.keys(feedback.confidence_calibration).length > 0 && (
        <div className="mt-3 pt-2 border-t border-white/5">
          <div className="text-text-muted text-[9px] mb-1">{t('advisor.confidenceCalibration')}</div>
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
            {isLong ? t('direction.long', { ns: 'common' }) : t('direction.short', { ns: 'common' })}
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
  const { t } = useTranslation('trading')
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
            {isLong ? t('direction.long', { ns: 'common' }) : t('direction.short', { ns: 'common' })}
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
  const { user, tg, initData } = useTelegram()
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

  // Suggestion state
  const [suggesting, setSuggesting] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [suggestError, setSuggestError] = useState(null)
  const [suggestReason, setSuggestReason] = useState(null)

  const fetchData = useCallback(async () => {
    if (!telegramId || !initData) {
      setLoading(false)
      return
    }
    try {
      setError(null)
      const [p, trades, hist, fb] = await Promise.all([
        api.getPortfolio(initData, telegramId),
        api.getActiveTrades(initData, telegramId),
        api.getTradeHistory(initData, telegramId),
        api.getFeedback(initData, 30).catch(() => null),
      ])

      if (!p || p.error) {
        setNeedsSetup(true)
        setPortfolio(null)
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
  }, [telegramId, initData])

  useEffect(() => { fetchData() }, [fetchData])

  const handleGetSuggestion = async () => {
    if (!telegramId) return
    setSuggesting(true)
    setSuggestError(null)
    setSuggestReason(null)
    setAnalysis(null)
    try {
      const result = await api.getSuggestion(initData, telegramId)
      if (result.analysis) setAnalysis(result.analysis)
      if (result.suggestion) {
        // New trade was created — refresh trades
        fetchData()
        setSuggestReason(null)
      } else {
        setSuggestReason(result.reason || t('advisor.noEntryDetected'))
      }
    } catch (err) {
      setSuggestError(err.message || 'Failed to get suggestion')
    } finally {
      setSuggesting(false)
    }
  }

  const handleOpen = async (tradeId) => {
    try {
      await api.openTrade(initData, tradeId)
      fetchData()
    } catch (err) {
      console.error('Open trade error:', err)
    }
  }

  const handleClose = async (tradeId, price) => {
    const exitPrice = price || currentPrice
    if (!exitPrice) return
    const doClose = async () => {
      try {
        await api.closeTrade(initData, tradeId, exitPrice, 'manual_close')
        fetchData()
      } catch (err) {
        console.error('Close trade error:', err)
      }
    }
    if (tg?.showConfirm) {
      tg.showConfirm(`Close trade #${tradeId} at $${exitPrice.toLocaleString()}?`, (ok) => { if (ok) doClose() })
    } else if (window.confirm(`Close trade #${tradeId} at $${exitPrice.toLocaleString()}?`)) {
      doClose()
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

      {/* Portfolio Stats (always visible when portfolio exists) */}
      {!needsSetup && <PortfolioCard portfolio={portfolio} t={t} />}

      {/* Portfolio Settings (always editable) */}
      <PortfolioSettingsCard
        portfolio={portfolio}
        telegramId={telegramId}
        initData={initData}
        onSave={fetchData}
        isNew={needsSetup}
        t={t}
      />

      {/* Get Suggestion Button (always visible when portfolio exists) */}
      {!needsSetup && (
        <button
          onClick={handleGetSuggestion}
          disabled={suggesting}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-accent-blue to-accent-purple text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {suggesting ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" strokeDasharray="50" strokeDashoffset="20" />
              </svg>
              {t('advisor.analyzing')}
            </>
          ) : (
            <>
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
              {t('advisor.getSuggestion')}
            </>
          )}
        </button>
      )}

      {/* Suggestion Result / Analysis */}
      {suggestError && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-xl p-3 text-center">
          <p className="text-accent-red text-xs">{suggestError}</p>
        </div>
      )}

      {suggestReason && (
        <div className="bg-accent-yellow/10 border border-accent-yellow/20 rounded-xl p-3 text-center">
          <p className="text-accent-yellow text-xs">{suggestReason}</p>
        </div>
      )}

      {analysis && <AnalysisCard analysis={analysis} t={t} />}

      <AIAccuracyCard feedback={feedback} t={t} />

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
