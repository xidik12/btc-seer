import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice, formatTimeAgo } from '../utils/format'

const PROFIT_COLORS = {
  high: 'text-accent-green',
  marginal: 'text-accent-yellow',
  negative: 'text-accent-red',
}

function ProfitBadge({ pct }) {
  const level = pct > 0.3 ? 'high' : pct > 0 ? 'marginal' : 'negative'
  return (
    <span className={`text-xs font-bold ${PROFIT_COLORS[level]}`}>
      {pct > 0 ? '+' : ''}{pct?.toFixed(3)}%
    </span>
  )
}

function ArbitrageCard({ opp }) {
  const profitLevel = opp.net_profit_pct > 0.3 ? 'border-accent-green/20' : opp.net_profit_pct > 0 ? 'border-accent-yellow/20' : 'border-accent-red/20'

  return (
    <div className={`bg-bg-card rounded-xl p-3 border ${profitLevel} slide-up`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-text-primary">{opp.coin_id?.toUpperCase()}</span>
        <ProfitBadge pct={opp.net_profit_pct} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-[10px] mb-2">
        <div className="bg-accent-green/10 rounded-lg p-2">
          <p className="text-text-muted">Buy @ {opp.buy_exchange}</p>
          <p className="text-accent-green font-bold text-xs">{formatCoinPrice(opp.buy_price)}</p>
        </div>
        <div className="bg-accent-red/10 rounded-lg p-2">
          <p className="text-text-muted">Sell @ {opp.sell_exchange}</p>
          <p className="text-accent-red font-bold text-xs">{formatCoinPrice(opp.sell_price)}</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] text-text-muted">
        <span>Spread: {opp.spread_pct?.toFixed(3)}%</span>
        <span>Fees: ~{opp.estimated_fees_pct?.toFixed(2)}%</span>
        <span>{formatTimeAgo(opp.timestamp)}</span>
      </div>
    </div>
  )
}

function ExchangePriceGrid({ prices }) {
  if (!prices || !Object.keys(prices).length) return null

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5">
      <h3 className="text-xs font-semibold text-text-muted mb-2">Exchange Prices</h3>
      <div className="space-y-1">
        {Object.entries(prices).sort(([, a], [, b]) => a - b).map(([exchange, price]) => (
          <div key={exchange} className="flex items-center justify-between text-xs">
            <span className="text-text-secondary capitalize">{exchange}</span>
            <span className="text-text-primary font-mono">{formatCoinPrice(price)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Arbitrage() {
  const { t } = useTranslation('common')
  const [opportunities, setOpportunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getArbitrageOpportunities()
      setOpportunities(data?.opportunities || [])
    } catch (err) {
      console.error('Arbitrage fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30_000)
    return () => clearInterval(interval)
  }, [fetchData])

  const filtered = filter === 'all'
    ? opportunities
    : filter === 'actionable'
    ? opportunities.filter(o => o.is_actionable)
    : opportunities.filter(o => o.net_profit_pct > 0)

  const totalActionable = opportunities.filter(o => o.is_actionable).length

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Arbitrage Scanner</h1>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Opportunities</p>
          <p className="text-text-primary text-lg font-bold">{opportunities.length}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Actionable</p>
          <p className="text-accent-green text-lg font-bold">{totalActionable}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Best Spread</p>
          <p className="text-accent-yellow text-lg font-bold">
            {opportunities.length > 0
              ? `${Math.max(...opportunities.map(o => o.net_profit_pct || 0)).toFixed(2)}%`
              : '--'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'actionable', 'profitable'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors capitalize ${
              filter === f
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Opportunities List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-text-muted text-sm py-12">
          No arbitrage opportunities found. Scanning every 30 seconds...
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((opp, i) => (
            <ArbitrageCard key={opp.id || i} opp={opp} />
          ))}
        </div>
      )}

      <p className="text-text-muted text-[9px] text-center">
        Prices across 10 exchanges. Fees estimated at 0.1% per side. Net profit = spread - fees.
      </p>
    </div>
  )
}
