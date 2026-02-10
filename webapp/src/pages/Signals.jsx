import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPrice, formatTime, formatDate, formatTimeAgo, getActionColor, getActionBg } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const TIMEFRAMES = ['1h', '4h', '24h']
const ANALYSIS_TABS = [
  { path: '/technical', labelKey: 'signals.tabs.technical' },
  { path: '/signals', labelKey: 'signals.tabs.signals' },
]

function LiveSignalCard({ signal, t }) {
  if (!signal) return null

  const isBuy = signal.action?.includes('buy')
  const borderColor = isBuy ? 'border-accent-green/30' : signal.action?.includes('sell') ? 'border-accent-red/30' : 'border-accent-yellow/30'
  const bgColor = isBuy ? 'bg-accent-green/5' : signal.action?.includes('sell') ? 'bg-accent-red/5' : 'bg-accent-yellow/5'

  return (
    <div className={`rounded-2xl p-4 border-2 ${borderColor} ${bgColor} slide-up`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-blue/15 text-accent-blue font-bold animate-pulse">
            {t('signals.liveSignal')}
          </span>
          <span className={`text-sm font-bold uppercase ${getActionColor(signal.action)}`}>
            {signal.action?.replace('_', ' ')}
          </span>
        </div>
        <span className="text-text-muted text-[10px]">{signal.timeframe?.toUpperCase()}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs mb-3">
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.entry')}</div>
          <div className="font-mono font-semibold text-sm">{formatPrice(signal.entry_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.target')}</div>
          <div className="font-mono font-semibold text-sm text-accent-green">{formatPrice(signal.target_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.stopLoss')}</div>
          <div className="font-mono font-semibold text-sm text-accent-red">{formatPrice(signal.stop_loss)}</div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-2">
        <div className="flex-1">
          <div className="flex items-center justify-between text-[9px] text-text-muted mb-0.5">
            <span>{t('signals.confidence')}</span>
            <span className="font-mono">{signal.confidence?.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                signal.confidence > 70 ? 'bg-accent-green' : signal.confidence > 50 ? 'bg-accent-yellow' : 'bg-accent-red'
              }`}
              style={{ width: `${signal.confidence || 0}%` }}
            />
          </div>
        </div>
        <div className="text-right">
          <div className="text-text-muted text-[9px]">{t('signals.risk')}</div>
          <div className="text-text-primary text-xs font-bold">{signal.risk_rating}/10</div>
        </div>
      </div>

      {signal.reasoning && (
        <p className="text-text-muted text-[10px] leading-relaxed mt-2 pt-2 border-t border-white/5">
          {signal.reasoning}
        </p>
      )}
    </div>
  )
}

function WinLossRecord({ signals }) {
  const evaluated = signals.filter(s => s.was_correct != null)
  if (!evaluated.length) return null

  const wins = evaluated.filter(s => s.was_correct).length
  const losses = evaluated.length - wins
  const winPct = (wins / evaluated.length) * 100

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-2">SIGNAL PERFORMANCE</h3>
      <div className="flex h-2.5 rounded-full overflow-hidden mb-2">
        <div className="bg-accent-green transition-all duration-500" style={{ width: `${winPct}%` }} />
        <div className="bg-accent-red transition-all duration-500" style={{ width: `${100 - winPct}%` }} />
      </div>
      <div className="flex justify-between text-[10px]">
        <span className="text-accent-green font-bold">{wins}W ({winPct.toFixed(0)}%)</span>
        <span className="text-text-muted">{evaluated.length} evaluated</span>
        <span className="text-accent-red font-bold">{losses}L ({(100 - winPct).toFixed(0)}%)</span>
      </div>
    </div>
  )
}

function SignalCard({ signal, t }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`p-3 rounded-xl border slide-up cursor-pointer hover:border-white/10 transition-colors ${getActionBg(signal.action)}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold uppercase ${getActionColor(signal.action)}`}>
            {signal.action?.replace('_', ' ')}
          </span>
          {signal.was_correct != null && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold ${
              signal.was_correct ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'
            }`}>
              {signal.was_correct ? t('signals.win') : t('signals.loss')}
            </span>
          )}
        </div>
        <span className="text-text-muted text-[10px]">{formatTimeAgo(signal.timestamp)}</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.entry')}</div>
          <div className="font-mono tabular-nums">{formatPrice(signal.entry_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.target')}</div>
          <div className="font-mono text-accent-green tabular-nums">{formatPrice(signal.target_price)}</div>
        </div>
        <div>
          <div className="text-text-muted text-[9px]">{t('signals.stopLoss')}</div>
          <div className="font-mono text-accent-red tabular-nums">{formatPrice(signal.stop_loss)}</div>
        </div>
      </div>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-white/5 space-y-1.5">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-text-muted">{t('signals.confidence')}: {signal.confidence?.toFixed(0)}%</span>
            <span className="text-text-muted">{t('signals.risk')}: {signal.risk_rating}/10</span>
          </div>
          <div className="text-text-muted text-[10px]">
            {formatDate(signal.timestamp)} {formatTime(signal.timestamp)}
          </div>
          {signal.reasoning && (
            <p className="text-text-muted text-[10px] leading-relaxed">{signal.reasoning}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function Signals() {
  const { t } = useTranslation('trading')
  const [currentSignal, setCurrentSignal] = useState(null)
  const [allSignals, setAllSignals] = useState({})
  const [timeframe, setTimeframe] = useState('1h')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const analysisTabs = useMemo(() => ANALYSIS_TABS.map(at => ({
    ...at,
    label: t(at.labelKey),
  })), [t])

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [current, ...histories] = await Promise.all([
          api.getCurrentSignals().catch(() => null),
          ...TIMEFRAMES.map(tf => api.getSignalHistory(tf, 14)),
        ])
        setCurrentSignal(current?.signal || current?.signals?.[0] || null)
        const tfMap = {}
        TIMEFRAMES.forEach((tf, i) => {
          tfMap[tf] = histories[i]?.signals || []
        })
        setAllSignals(tfMap)
      } catch (err) {
        setError(err.message || 'Failed to load signals')
      }
      setLoading(false)
    }
    load()
  }, [])

  const signals = allSignals[timeframe] || []

  const stats = useMemo(() => {
    const all = Object.values(allSignals).flat()
    const evaluated = all.filter(s => s.was_correct != null)
    const wins = evaluated.filter(s => s.was_correct).length
    return { total: all.length, evaluated: evaluated.length, wins, losses: evaluated.length - wins }
  }, [allSignals])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('signals.title')}</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-36 bg-bg-card rounded-2xl" />
          <div className="h-12 bg-bg-card rounded-2xl" />
          <div className="h-20 bg-bg-card rounded-xl" />
          <div className="h-20 bg-bg-card rounded-xl" />
          <div className="h-20 bg-bg-card rounded-xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('signals.title')}</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{t('signals.noSignals')}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={() => window.location.reload()} className="text-accent-blue text-xs hover:underline">{t('app.retry', { ns: 'common' })}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={analysisTabs} />
      <h1 className="text-lg font-bold">{t('signals.title')}</h1>

      {currentSignal && <LiveSignalCard signal={currentSignal} t={t} />}

      {stats.evaluated > 0 && (
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
            <div className="text-text-muted text-[9px]">{t('signals.title')}</div>
            <div className="text-text-primary text-sm font-bold">{stats.total}</div>
          </div>
          <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
            <div className="text-text-muted text-[9px]">{t('portfolio.winRate')}</div>
            <div className="text-accent-green text-sm font-bold">
              {stats.evaluated > 0 ? `${(stats.wins / stats.evaluated * 100).toFixed(0)}%` : '--'}
            </div>
          </div>
          <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
            <div className="text-text-muted text-[9px]">W / L</div>
            <div className="text-text-primary text-sm font-bold">{stats.wins} / {stats.losses}</div>
          </div>
        </div>
      )}

      <WinLossRecord signals={Object.values(allSignals).flat()} />

      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {TIMEFRAMES.map(tf => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              timeframe === tf ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tf.toUpperCase()}
            <span className="ml-1 opacity-60">{(allSignals[tf] || []).length}</span>
          </button>
        ))}
      </div>

      {signals.length === 0 ? (
        <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
          <p className="text-text-muted text-sm">{t('signals.noSignals')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {signals.map((s, i) => (
            <SignalCard key={s.id || i} signal={s} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
