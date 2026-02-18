import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatTimeAgo, safeFixed } from '../utils/format'
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

const ENTITY_TYPE_STYLES = {
  exchange:     { bg: 'bg-accent-blue/20',   text: 'text-accent-blue',   border: 'border-accent-blue/30' },
  institution:  { bg: 'bg-purple-500/20',    text: 'text-purple-400',    border: 'border-purple-500/30' },
  government:   { bg: 'bg-accent-yellow/20', text: 'text-accent-yellow', border: 'border-accent-yellow/30' },
  individual:   { bg: 'bg-accent-orange/20', text: 'text-accent-orange', border: 'border-accent-orange/30' },
  mining_pool:  { bg: 'bg-teal-500/20',      text: 'text-teal-400',      border: 'border-teal-500/30' },
}

const FILTER_OPTIONS = [
  { key: 'all',          directionFilter: null,           entityTypeFilter: null },
  { key: 'exchange_in',  directionFilter: 'exchange_in',  entityTypeFilter: null },
  { key: 'exchange_out', directionFilter: 'exchange_out', entityTypeFilter: null },
  { key: 'institutions', directionFilter: null,           entityTypeFilter: 'institution' },
  { key: 'notable',      directionFilter: null,           entityTypeFilter: '__notable__' },
]

function getSeverityColor(severity) {
  return SEVERITY_COLORS[severity] || 'bg-bg-hover'
}

function truncateAddr(addr) {
  if (!addr || addr.length < 16) return addr || ''
  return `${addr.slice(0, 8)}...${addr.slice(-6)}`
}

function EntityBadge({ entityName, entityType, t }) {
  if (!entityName || !entityType) return null
  const style = ENTITY_TYPE_STYLES[entityType] || ENTITY_TYPE_STYLES.exchange
  const typeLabel = t(`market:whales.entityType.${entityType}`, entityType)

  return (
    <span className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-md border ${style.bg} ${style.text} ${style.border} font-medium`}>
      <EntityIcon type={entityType} />
      {entityName}
      <span className="opacity-60">({typeLabel})</span>
    </span>
  )
}

function EntityIcon({ type }) {
  const cls = "w-2.5 h-2.5 shrink-0"
  switch (type) {
    case 'exchange':
      return (
        <svg viewBox="0 0 16 16" fill="currentColor" className={cls}>
          <path d="M8 1L1 5v6l7 4 7-4V5L8 1zm0 2.18L12.93 6 8 8.82 3.07 6 8 3.18z"/>
        </svg>
      )
    case 'institution':
      return (
        <svg viewBox="0 0 16 16" fill="currentColor" className={cls}>
          <path d="M8 1L1 4v1h14V4L8 1zM2 6v6h2V6H2zm4 0v6h2V6H6zm4 0v6h2V6h-2zm4 0v6h1V6h-1zM1 13v2h14v-2H1z"/>
        </svg>
      )
    case 'government':
      return (
        <svg viewBox="0 0 16 16" fill="currentColor" className={cls}>
          <path d="M8 0L6.5 3H2l3.5 3L4 10l4-2.5L12 10 10.5 6 14 3H9.5L8 0z"/>
        </svg>
      )
    case 'individual':
      return (
        <svg viewBox="0 0 16 16" fill="currentColor" className={cls}>
          <circle cx="8" cy="4" r="3"/><path d="M2 14c0-3.31 2.69-6 6-6s6 2.69 6 6H2z"/>
        </svg>
      )
    case 'mining_pool':
      return (
        <svg viewBox="0 0 16 16" fill="currentColor" className={cls}>
          <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 2a2 2 0 110 4 2 2 0 010-4zM4 10l2-1h4l2 1v2H4v-2z"/>
        </svg>
      )
    default:
      return null
  }
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

function AddressChip({ address, onClick }) {
  if (!address) return <span className="text-text-muted font-mono text-[9px]">--</span>
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(address) }}
      className="text-[9px] font-mono text-accent-blue hover:text-accent-blue/80 hover:underline transition-colors cursor-pointer"
      title={address}
    >
      {truncateAddr(address)}
    </button>
  )
}

function AddressDetailPanel({ address, onClose, t }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!address) return
    setLoading(true)
    api.getAddressTransactions(address, 20)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [address])

  if (!address) return null

  const copyAddress = () => {
    navigator.clipboard.writeText(address).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="bg-bg-card rounded-xl border border-accent-blue/20 p-3 mb-3 slide-up">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-text-primary">{t('market:whales.addressDetail.title')}</h3>
        <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xs px-2 py-1">
          &times;
        </button>
      </div>

      {/* Full address with copy */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] font-mono text-text-primary break-all flex-1">{address}</span>
        <button
          onClick={copyAddress}
          className="text-[9px] px-2 py-1 bg-white/5 rounded border border-white/10 text-text-muted hover:text-text-primary shrink-0"
        >
          {copied ? t('market:whales.addressDetail.copied') : t('market:whales.addressDetail.copy')}
        </button>
      </div>

      {/* Entity label */}
      {data?.label ? (
        <div className="mb-2">
          <EntityBadge entityName={data.label.name} entityType={data.label.type} t={t} />
        </div>
      ) : (
        !loading && (
          <span className="text-[9px] text-text-muted mb-2 inline-block px-1.5 py-0.5 bg-white/5 rounded">
            {t('market:whales.addressDetail.unknown')}
          </span>
        )
      )}

      {/* Mempool link */}
      <a
        href={`https://mempool.space/address/${address}`}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] text-accent-blue hover:underline block mb-2"
      >
        {t('market:whales.addressDetail.viewOnMempool')}
      </a>

      {/* Transaction list */}
      {loading ? (
        <div className="flex justify-center py-4">
          <div className="w-4 h-4 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data?.transactions?.length > 0 ? (
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          <p className="text-[9px] text-text-muted">{t('market:whales.addressDetail.txCount', { count: data.transaction_count })}</p>
          {data.transactions.map(tx => (
            <div key={tx.tx_hash} className="flex items-center gap-2 text-[9px] py-1 border-t border-white/5">
              <span className={tx.role === 'sender' ? 'text-accent-red' : 'text-accent-green'}>
                {tx.role === 'sender' ? 'OUT' : 'IN'}
              </span>
              <span className="text-text-primary font-bold">{tx.amount_btc?.toLocaleString()} BTC</span>
              <span className="text-text-muted">{formatTimeAgo(tx.timestamp)}</span>
              <span className="text-text-muted font-mono">{tx.tx_hash?.slice(0, 8)}...</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[9px] text-text-muted py-2">{t('market:whales.addressDetail.noTxs')}</p>
      )}
    </div>
  )
}

function WhaleCard({ tx, t, onAddressClick }) {
  const directionLabel = t(`market:whales.direction.${tx.direction}`, tx.direction?.replace(/_/g, ' '))
  const isNotable = tx.entity_type && tx.entity_type !== 'exchange'

  return (
    <div className={`bg-bg-card rounded-xl p-3 border slide-up ${isNotable ? 'border-purple-500/20' : 'border-white/5'}`}>
      <div className="flex items-start gap-3">
        <DirectionIcon direction={tx.direction} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-text-primary text-sm font-bold">
              {tx.amount_btc?.toLocaleString()} BTC
            </span>
            {tx.amount_usd && (
              <span className="text-text-muted text-xs">
                ${safeFixed(tx.amount_usd / 1e6, 1)}M
              </span>
            )}
            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${getSeverityColor(tx.severity)}`}>
              S{tx.severity}
            </span>
          </div>

          {/* Entity badge */}
          {tx.entity_name && (
            <div className="mb-1">
              <EntityBadge entityName={tx.entity_name} entityType={tx.entity_type} t={t} />
            </div>
          )}

          {/* Address flow: from → to (clickable) */}
          {(tx.from_address || tx.to_address) && (
            <div className="flex items-center gap-1 mb-1 text-[9px]">
              <AddressChip address={tx.from_address} onClick={onAddressClick} />
              <span className="text-text-muted">&rarr;</span>
              <AddressChip address={tx.to_address} onClick={onAddressClick} />
            </div>
          )}

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
                1h: {tx.change_pct_1h > 0 ? '+' : ''}{safeFixed(tx.change_pct_1h, 2)}%
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

function InstitutionalTab({ t }) {
  const [holdings, setHoldings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getInstitutionalHoldings()
      .then(data => setHoldings(data?.holdings || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (holdings.length === 0) {
    return (
      <div className="text-center text-text-muted text-sm py-12">
        No institutional holdings data yet. Data updates every 6 hours.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {holdings.map((h, i) => (
        <div key={h.ticker || i} className="bg-bg-card rounded-xl p-3 border border-purple-500/10 slide-up">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="text-text-primary text-sm font-bold">{h.company_name}</span>
              {h.ticker && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 font-mono">
                  {h.ticker}
                </span>
              )}
            </div>
            {h.country && <span className="text-text-muted text-[9px]">{h.country}</span>}
          </div>
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-text-primary font-bold">{h.total_btc?.toLocaleString()} BTC</span>
            {h.change_btc != null && h.change_btc !== 0 && (
              <span className={h.change_btc > 0 ? 'text-accent-green font-bold' : 'text-accent-red font-bold'}>
                {h.change_btc > 0 ? '+' : ''}{h.change_btc.toLocaleString()} BTC
              </span>
            )}
            {h.current_value_usd && (
              <span className="text-text-muted">
                ${(h.current_value_usd / 1e9).toFixed(2)}B
              </span>
            )}
          </div>
          {h.snapshot_date && (
            <div className="text-text-muted text-[9px] mt-1">
              Updated: {new Date(h.snapshot_date).toLocaleDateString()}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Whales() {
  const { t } = useTranslation(['market', 'common'])
  const [stats, setStats] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [filter, setFilter] = useState('all')
  const [chainFilter, setChainFilter] = useState('all')
  const [mainTab, setMainTab] = useState('transactions')
  const [loading, setLoading] = useState(true)
  const [selectedAddress, setSelectedAddress] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const activeFilter = FILTER_OPTIONS.find(f => f.key === filter)
      const direction = activeFilter?.directionFilter || undefined
      // For 'notable', we fetch all and filter client-side; for specific entity type, pass to API
      const entityType = activeFilter?.entityTypeFilter === '__notable__' ? undefined : activeFilter?.entityTypeFilter || undefined

      const [statsData, txData] = await Promise.all([
        api.getWhaleStats(),
        api.getRecentWhales(168, 100, direction, entityType),
      ])
      setStats(statsData)

      let txList = txData?.transactions || []

      // Client-side filter for 'notable' (non-exchange entities)
      if (activeFilter?.entityTypeFilter === '__notable__') {
        txList = txList.filter(tx =>
          tx.entity_type && tx.entity_type !== 'exchange' && tx.entity_type !== 'unknown'
        )
      }

      setTransactions(txList)
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

  const handleAddressClick = useCallback((address) => {
    setSelectedAddress(prev => prev === address ? null : address)
  }, [])

  // Use 7d stats if 24h has no data, show the richer view
  const s24 = stats?.stats_24h || {}
  const s7d = stats?.stats_7d || {}
  const s = s24.count > 0 ? s24 : s7d
  const periodLabel = s24.count > 0 ? '24h' : '7d'

  const filteredTransactions = transactions.filter(tx =>
    chainFilter === 'all' || tx.chain === chainFilter || (!tx.chain && chainFilter === 'bitcoin')
  )

  return (
    <div className="px-4 pt-2 pb-20">
      <SubTabBar tabs={MARKET_TABS} />

      <h1 className="text-lg font-bold mt-3 mb-3">{t('market:whales.title')}</h1>

      {/* Main Tab: Transactions | Institutional */}
      <div className="flex gap-2 mb-3">
        {['transactions', 'institutional'].map(tab => (
          <button
            key={tab}
            onClick={() => setMainTab(tab)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              mainTab === tab
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {tab === 'transactions' ? 'Transactions' : 'Institutional'}
          </button>
        ))}
      </div>

      {mainTab === 'institutional' ? (
        <InstitutionalTab t={t} />
      ) : (
      <>
      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.count24h')} ({periodLabel})</p>
          <p className="text-text-primary text-lg font-bold">{s.count ?? '--'}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.netFlow')}</p>
          <p className={`text-lg font-bold ${(s.net_flow_btc || 0) > 0 ? 'text-accent-red' : (s.net_flow_btc || 0) < 0 ? 'text-accent-green' : 'text-text-primary'}`}>
            {s.net_flow_btc != null ? `${s.net_flow_btc > 0 ? '+' : ''}${s.net_flow_btc.toLocaleString()}` : '--'}
          </p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.avgSize')}</p>
          <p className="text-text-primary text-lg font-bold">
            {s.avg_btc ? `${s.avg_btc.toLocaleString()}` : '--'}
          </p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5">
          <p className="text-text-muted text-[10px]">{t('market:whales.stats.mostActive')}</p>
          <p className="text-text-primary text-sm font-bold truncate">
            {s.most_active_entity || '--'}
          </p>
        </div>
      </div>

      {/* Direction Breakdown Bar */}
      {s.count > 0 && (
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 mb-3">
          <p className="text-text-muted text-[10px] mb-2">{t('market:whales.directionBreakdown')}</p>
          <div className="flex rounded-full overflow-hidden h-3">
            {s.exchange_in > 0 && (
              <div
                className="bg-accent-red/70 transition-all"
                style={{ width: `${(s.exchange_in / s.count) * 100}%` }}
                title={t('market:whales.direction.exchange_in')}
              />
            )}
            {s.exchange_out > 0 && (
              <div
                className="bg-accent-green/70 transition-all"
                style={{ width: `${(s.exchange_out / s.count) * 100}%` }}
                title={t('market:whales.direction.exchange_out')}
              />
            )}
            {(s.unknown + s.whale_to_whale) > 0 && (
              <div
                className="bg-white/20 transition-all"
                style={{ width: `${((s.unknown + s.whale_to_whale) / s.count) * 100}%` }}
              />
            )}
          </div>
          <div className="flex justify-between text-[9px] text-text-muted mt-1">
            <span className="text-accent-red">{t('market:whales.direction.exchange_in')} ({s.exchange_in})</span>
            <span className="text-accent-green">{t('market:whales.direction.exchange_out')} ({s.exchange_out})</span>
            <span>{t('market:whales.direction.unknown')} ({(s.unknown || 0) + (s.whale_to_whale || 0)})</span>
          </div>
        </div>
      )}

      {/* Chain Filter */}
      <div className="flex gap-2 mb-3">
        {['all', 'bitcoin', 'ethereum', 'solana'].map(c => (
          <button
            key={c}
            onClick={() => setChainFilter(c)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              chainFilter === c
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {c === 'all' ? 'All' : c === 'bitcoin' ? 'BTC' : c === 'ethereum' ? 'ETH' : 'SOL'}
          </button>
        ))}
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
        {FILTER_OPTIONS.map(f => (
          <button
            key={f.key}
            onClick={() => { setFilter(f.key); setLoading(true) }}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors whitespace-nowrap ${
              filter === f.key
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {t(`market:whales.filter.${f.key}`)}
          </button>
        ))}
      </div>

      {/* Address Detail Panel */}
      {selectedAddress && (
        <AddressDetailPanel
          address={selectedAddress}
          onClose={() => setSelectedAddress(null)}
          t={t}
        />
      )}

      {/* Transaction List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredTransactions.length === 0 ? (
        <div className="text-center text-text-muted text-sm py-12">
          {t('market:whales.noWhales')}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredTransactions.map(tx => (
            <WhaleCard key={tx.tx_hash || tx.id} tx={tx} t={t} onAddressClick={handleAddressClick} />
          ))}
        </div>
      )}
      </>
      )}
    </div>
  )
}
