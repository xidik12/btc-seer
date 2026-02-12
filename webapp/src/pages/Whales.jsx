import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatTimeAgo } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', labelKey: 'common:link.liquidations' },
  { path: '/powerlaw', labelKey: 'common:link.powerLaw' },
  { path: '/elliott-wave', labelKey: 'common:link.elliottWave' },
  { path: '/events', labelKey: 'common:link.events' },
  { path: '/whales', labelKey: 'common:link.whales' },
  { path: '/tools', labelKey: 'common:link.tools' },
]

const SEVERITY_COLORS = {
  10: 'bg-accent-red/80',
  9: 'bg-accent-red/60',
  8: 'bg-accent-orange/60',
  7: 'bg-accent-orange/40',
  6: 'bg-accent-yellow/40',
  5: 'bg-accent-yellow/20',
  4: 'bg-bg-hover',
}

function getSeverityColor(severity) {
  return SEVERITY_COLORS[severity] || 'bg-bg-hover'
}

function DirectionIcon({ direction }) {
  if (direction === 'exchange_in') {
    return (
      <div className="w-7 h-7 rounded-full bg-accent-red/20 flex items-center justify-center shrink-0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-accent-red">
          <path d="M12 5v14M5 12l7 7 7-7" />
        </svg>
      </div>
    )
  }
  if (direction === 'exchange_out') {
    return (
      <div className="w-7 h-7 rounded-full bg-accent-green/20 flex items-center justify-center shrink-0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-accent-green">
          <path d="M12 19V5M5 12l7-7 7 7" />
        </svg>
      </div>
    )
  }
  return (
    <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center shrink-0">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-text-muted">
        <path d="M5 12h14" />
      </svg>
    </div>
  )
}

function WhaleCard({ tx, t }) {
  const directionLabel = t(`market:whales.direction.${tx.direction}`, tx.direction?.replace(/_/g, ' '))

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
      <div className="flex items-start gap-3">
        <DirectionIcon direction={tx.direction} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-text-primary text-sm font-bold">
              {tx.amount_btc?.toLocaleString()} BTC
            </span>
            {tx.amount_usd && (
              <span className="text-text-muted text-xs">
                ${(tx.amount_usd / 1e6).toFixed(1)}M
              </span>
            )}
            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${getSeverityColor(tx.severity)}`}>
              S{tx.severity}
            </span>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-text-muted mb-1">
            <span className={
              tx.direction === 'exchange_in' ? 'text-accent-red' :
              tx.direction === 'exchange_out' ? 'text-accent-green' : ''
            }>
              {directionLabel}
            </span>
            <span>|</span>
            <span>{tx.from_entity} &rarr; {tx.to_entity}</span>
          </div>

          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-text-muted font-mono">
              {tx.tx_hash?.slice(0, 8)}...{tx.tx_hash?.slice(-6)}
            </span>
            <span className="text-text-muted">{formatTimeAgo(tx.timestamp)}</span>
            {tx.change_pct_1h != null && (
              <span className={tx.change_pct_1h >= 0 ? 'text-accent-green' : 'text-accent-red'}>
                1h: {tx.change_pct_1h > 0 ? '+' : ''}{tx.change_pct_1h.toFixed(2)}%
              </span>
            )}
            {tx.direction_was_predictive != null && (
              <span className={tx.direction_was_predictive ? 'text-accent-green' : 'text-accent-red'}>
                {tx.direction_was_predictive ? 'Correct' : 'Wrong'}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Whales() {
  const { t } = useTranslation(['market', 'common'])
  const [stats, setStats] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [statsData, txData] = await Promise.all([
        api.getWhaleStats(),
        api.getRecentWhales(24, 50, filter === 'all' ? undefined : filter),
      ])
      setStats(statsData)
      setTransactions(txData?.transactions || [])
    } catch (err) {
      console.error('Whale data error:', err)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 120_000) // 2 min
    return () => clearInterval(interval)
  }, [fetchData])

  const s24 = stats?.stats_24h || {}

  return (
    <div className="px-4 pt-2 pb-20">
      <SubTabBar tabs={MARKET_TABS} />

      <h1 className="text-lg font-bold mt-3 mb-3">{t('market:whales.title')}</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.count24h')}</p>
          <p className="text-text-primary text-lg font-bold">{s24.count ?? '--'}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.netFlow')}</p>
          <p className={`text-lg font-bold ${(s24.net_flow_btc || 0) > 0 ? 'text-accent-red' : (s24.net_flow_btc || 0) < 0 ? 'text-accent-green' : 'text-text-primary'}`}>
            {s24.net_flow_btc != null ? `${s24.net_flow_btc > 0 ? '+' : ''}${s24.net_flow_btc.toLocaleString()}` : '--'}
          </p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.avgSize')}</p>
          <p className="text-text-primary text-lg font-bold">
            {s24.avg_btc ? `${s24.avg_btc.toLocaleString()}` : '--'}
          </p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.accuracy')}</p>
          <p className="text-text-primary text-lg font-bold">
            {stats?.predictive_accuracy != null ? `${stats.predictive_accuracy}%` : '--'}
          </p>
        </div>
      </div>

      {/* Direction Breakdown Bar */}
      {s24.count > 0 && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 mb-3">
          <p className="text-text-muted text-[10px] mb-2">{t('market:whales.directionBreakdown')}</p>
          <div className="flex rounded-full overflow-hidden h-3">
            {s24.exchange_in > 0 && (
              <div
                className="bg-accent-red/70 transition-all"
                style={{ width: `${(s24.exchange_in / s24.count) * 100}%` }}
                title={t('market:whales.direction.exchange_in')}
              />
            )}
            {s24.exchange_out > 0 && (
              <div
                className="bg-accent-green/70 transition-all"
                style={{ width: `${(s24.exchange_out / s24.count) * 100}%` }}
                title={t('market:whales.direction.exchange_out')}
              />
            )}
            {(s24.unknown + s24.whale_to_whale) > 0 && (
              <div
                className="bg-white/20 transition-all"
                style={{ width: `${((s24.unknown + s24.whale_to_whale) / s24.count) * 100}%` }}
              />
            )}
          </div>
          <div className="flex justify-between text-[9px] text-text-muted mt-1">
            <span className="text-accent-red">{t('market:whales.direction.exchange_in')} ({s24.exchange_in})</span>
            <span className="text-accent-green">{t('market:whales.direction.exchange_out')} ({s24.exchange_out})</span>
            <span>{t('market:whales.direction.unknown')} ({(s24.unknown || 0) + (s24.whale_to_whale || 0)})</span>
          </div>
        </div>
      )}

      {/* Filter Buttons */}
      <div className="flex gap-2 mb-3">
        {['all', 'exchange_in', 'exchange_out'].map(f => (
          <button
            key={f}
            onClick={() => { setFilter(f); setLoading(true) }}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              filter === f
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {t(`market:whales.filter.${f}`)}
          </button>
        ))}
      </div>

      {/* Transaction List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : transactions.length === 0 ? (
        <div className="text-center text-text-muted text-sm py-12">
          {t('market:whales.noWhales')}
        </div>
      ) : (
        <div className="space-y-2">
          {transactions.map(tx => (
            <WhaleCard key={tx.tx_hash || tx.id} tx={tx} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
