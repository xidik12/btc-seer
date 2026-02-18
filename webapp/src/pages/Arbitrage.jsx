import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice, formatTimeAgo } from '../utils/format'
import ShareButton from '../components/ShareButton'
import { arbitrageShareText } from '../utils/shareTemplates'

// Coin ID to symbol mapping for display
const COIN_SYMBOLS = {
  bitcoin: 'BTC', ethereum: 'ETH', ripple: 'XRP', solana: 'SOL',
  binancecoin: 'BNB', cardano: 'ADA', dogecoin: 'DOGE', 'avalanche-2': 'AVAX',
  polkadot: 'DOT', chainlink: 'LINK', 'matic-network': 'MATIC', 'shiba-inu': 'SHIB',
  uniswap: 'UNI', litecoin: 'LTC', cosmos: 'ATOM', near: 'NEAR',
  aptos: 'APT', arbitrum: 'ARB', optimism: 'OP', sui: 'SUI',
}

// Consistent exchange colors
const EXCHANGE_COLORS = {
  binance: '#F0B90B', coinbase: '#0052FF', kraken: '#5741D9',
  bybit: '#F7A600', okx: '#FFFFFF', kucoin: '#23AF91',
  gateio: '#2354E6', bitfinex: '#7BBA44', htx: '#2B6CB0',
  mexc: '#1972E2', bitget: '#00F0FF', bingx: '#2DC8A2',
  phemex: '#D3FF57', woo: '#004CFF', gemini: '#00DCFA',
  bitstamp: '#509E2F', whitebit: '#02C076', mercado: '#57BD68',
  lbank: '#1C6CF2',
}

const CONTINENT_LABELS = {
  all: 'All Regions',
  asia: 'Asia',
  north_america: 'N. America',
  europe: 'Europe',
  latin_america: 'LATAM',
}

const PROFIT_COLORS = {
  high: 'text-accent-green',
  marginal: 'text-accent-yellow',
  negative: 'text-accent-red',
}

function coinSymbol(coinId) {
  return COIN_SYMBOLS[coinId] || coinId?.toUpperCase()
}

function ProfitBadge({ pct }) {
  const level = pct > 0.3 ? 'high' : pct > 0 ? 'marginal' : 'negative'
  return (
    <span className={`text-xs font-bold ${PROFIT_COLORS[level]}`}>
      {pct > 0 ? '+' : ''}{pct?.toFixed(3)}%
    </span>
  )
}

function ExchangeDot({ exchange }) {
  const color = EXCHANGE_COLORS[exchange] || '#888'
  return (
    <span
      className="inline-block w-2 h-2 rounded-full mr-1 flex-shrink-0"
      style={{ backgroundColor: color }}
    />
  )
}

function RegionTag({ continent }) {
  if (!continent) return null
  const colors = {
    asia: 'bg-amber-500/15 text-amber-400',
    north_america: 'bg-blue-500/15 text-blue-400',
    europe: 'bg-purple-500/15 text-purple-400',
    latin_america: 'bg-green-500/15 text-green-400',
  }
  const labels = { asia: 'Asia', north_america: 'NA', europe: 'EU', latin_america: 'LATAM' }
  return (
    <span className={`text-[8px] px-1 py-0.5 rounded ${colors[continent] || 'bg-white/5 text-text-muted'}`}>
      {labels[continent] || continent}
    </span>
  )
}

function ArbitrageCard({ opp, onExpand, isExpanded }) {
  const profitLevel = opp.net_profit_pct > 0.3 ? 'border-accent-green/20' : opp.net_profit_pct > 0 ? 'border-accent-yellow/20' : 'border-accent-red/20'
  const dollarProfit = opp.buy_price > 0 ? ((opp.sell_price - opp.buy_price) / opp.buy_price * 1000).toFixed(2) : '0.00'

  return (
    <div
      className={`bg-bg-card rounded-xl p-3 border ${profitLevel} slide-up cursor-pointer`}
      onClick={() => onExpand(opp.coin_id)}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-text-primary">{coinSymbol(opp.coin_id)}</span>
        <div className="flex items-center gap-2">
          <ShareButton compact text={arbitrageShareText(opp)} />
          <span className="text-[10px] text-text-muted">${dollarProfit}/1K</span>
          <ProfitBadge pct={opp.net_profit_pct} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[10px] mb-2">
        <div className="bg-accent-green/10 rounded-lg p-2">
          <p className="text-text-muted flex items-center gap-1">
            <ExchangeDot exchange={opp.buy_exchange} />Buy @ {opp.buy_exchange}
            <RegionTag continent={opp.buy_continent} />
          </p>
          <p className="text-accent-green font-bold text-xs">{formatCoinPrice(opp.buy_price)}</p>
        </div>
        <div className="bg-accent-red/10 rounded-lg p-2">
          <p className="text-text-muted flex items-center gap-1">
            <ExchangeDot exchange={opp.sell_exchange} />Sell @ {opp.sell_exchange}
            <RegionTag continent={opp.sell_continent} />
          </p>
          <p className="text-accent-red font-bold text-xs">{formatCoinPrice(opp.sell_price)}</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] text-text-muted">
        <span>Spread: {opp.spread_pct?.toFixed(3)}%</span>
        <span>Fees: ~{opp.estimated_fees_pct?.toFixed(2)}%</span>
        <span>{formatTimeAgo(opp.timestamp)}</span>
      </div>

      {/* Expanded: Exchange Price Grid */}
      {isExpanded && opp.exchange_prices && (
        <div className="mt-3 pt-3 border-t border-white/5">
          <h4 className="text-[10px] font-semibold text-text-muted mb-2">All Exchange Prices</h4>
          <div className="space-y-1">
            {Object.entries(opp.exchange_prices)
              .filter(([, data]) => data?.bid || data?.ask)
              .sort(([, a], [, b]) => (a.ask || a.bid || 0) - (b.ask || b.bid || 0))
              .map(([exchange, data]) => (
                <div key={exchange} className="flex items-center justify-between text-[10px]">
                  <span className="text-text-secondary flex items-center capitalize">
                    <ExchangeDot exchange={exchange} />{exchange}
                  </span>
                  <div className="flex gap-3">
                    {data.bid && <span className="text-accent-green font-mono">{formatCoinPrice(data.bid)}</span>}
                    {data.ask && <span className="text-accent-red font-mono">{formatCoinPrice(data.ask)}</span>}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ProfitCalculator() {
  const [coinId, setCoinId] = useState('bitcoin')
  const [amount, setAmount] = useState(1000)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const calculate = async () => {
    setLoading(true)
    try {
      const data = await api.calculateArbitrage(coinId, amount)
      setResult(data?.best_opportunity)
    } catch (err) {
      console.error('Calculate error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] text-text-muted block mb-1">Coin</label>
          <select
            value={coinId}
            onChange={e => setCoinId(e.target.value)}
            className="w-full bg-bg-card border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
          >
            {Object.entries(COIN_SYMBOLS).map(([id, sym]) => (
              <option key={id} value={id}>{sym}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-text-muted block mb-1">Amount (USD)</label>
          <input
            type="number"
            value={amount}
            onChange={e => setAmount(Number(e.target.value))}
            min={10}
            max={1000000}
            className="w-full bg-bg-card border border-white/10 rounded-lg px-2 py-1.5 text-xs text-text-primary"
          />
        </div>
      </div>

      <button
        onClick={calculate}
        disabled={loading}
        className="w-full bg-accent-blue/20 border border-accent-blue text-accent-blue text-xs py-2 rounded-lg font-medium"
      >
        {loading ? 'Calculating...' : 'Calculate Profit'}
      </button>

      {result && (
        <div className={`bg-bg-card rounded-xl p-3 border ${result.is_profitable ? 'border-accent-green/20' : 'border-accent-red/20'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-text-muted">Net Profit</span>
            <span className={`text-sm font-bold ${result.is_profitable ? 'text-accent-green' : 'text-accent-red'}`}>
              ${result.net_profit_usd?.toFixed(2)} ({result.net_profit_pct?.toFixed(3)}%)
            </span>
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between">
              <span className="text-text-muted flex items-center"><ExchangeDot exchange={result.buy_exchange} />Buy @ {result.buy_exchange}</span>
              <span className="text-text-primary">{formatCoinPrice(result.buy_price)} (fee: ${result.buy_fee_usd})</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted flex items-center"><ExchangeDot exchange={result.sell_exchange} />Sell @ {result.sell_exchange}</span>
              <span className="text-text-primary">{formatCoinPrice(result.sell_price)} (fee: ${result.sell_fee_usd})</span>
            </div>
            <div className="flex justify-between border-t border-white/5 pt-1">
              <span className="text-text-muted">Coins traded</span>
              <span className="text-text-primary font-mono">{result.coins_bought?.toFixed(6)}</span>
            </div>
          </div>
        </div>
      )}

      {result === null && !loading && (
        <p className="text-[10px] text-text-muted text-center">
          Enter an amount and click Calculate to see exact profit after real exchange fees.
        </p>
      )}
    </div>
  )
}

function RefreshTimer({ lastUpdate }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!lastUpdate) return
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - lastUpdate) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [lastUpdate])

  return (
    <span className="text-[9px] text-text-muted">
      Updated {elapsed}s ago
    </span>
  )
}

export default function Arbitrage() {
  const { t } = useTranslation('common')
  const [opportunities, setOpportunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [regionFilter, setRegionFilter] = useState('all')
  const [expandedCoin, setExpandedCoin] = useState(null)
  const [tab, setTab] = useState('scanner')
  const [lastUpdate, setLastUpdate] = useState(null)
  const [exchangeCount, setExchangeCount] = useState(0)

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getArbitrageOpportunities()
      setOpportunities(data?.opportunities || [])
      setExchangeCount(data?.exchanges_count || 0)
      setLastUpdate(Date.now())
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

  // Apply profit filter
  let filtered = filter === 'all'
    ? opportunities
    : filter === 'actionable'
    ? opportunities.filter(o => o.is_actionable)
    : opportunities.filter(o => o.net_profit_pct > 0)

  // Apply region filter
  if (regionFilter !== 'all') {
    filtered = filtered.filter(o =>
      o.buy_continent === regionFilter || o.sell_continent === regionFilter
    )
  }

  // Sort profitable tab by dollar profit
  const sorted = filter === 'profitable'
    ? [...filtered].sort((a, b) => {
        const profitA = a.buy_price > 0 ? (a.sell_price - a.buy_price) / a.buy_price : 0
        const profitB = b.buy_price > 0 ? (b.sell_price - b.buy_price) / b.buy_price : 0
        return profitB - profitA
      })
    : filtered

  const totalActionable = opportunities.filter(o => o.is_actionable).length

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Arbitrage Scanner</h1>
        <RefreshTimer lastUpdate={lastUpdate} />
      </div>

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
          <p className="text-text-muted text-[10px]">Exchanges</p>
          <p className="text-accent-blue text-lg font-bold">{exchangeCount || '--'}</p>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-2">
        {['scanner', 'calculator'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors capitalize ${
              tab === t
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {t === 'scanner' ? 'Live Scanner' : 'Profit Calculator'}
          </button>
        ))}
      </div>

      {tab === 'calculator' ? (
        <ProfitCalculator />
      ) : (
        <>
          {/* Profit Filters */}
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

          {/* Region Filters */}
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {Object.entries(CONTINENT_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setRegionFilter(key)}
                className={`text-[10px] px-2.5 py-1 rounded-lg border transition-colors whitespace-nowrap ${
                  regionFilter === key
                    ? 'bg-accent-purple/20 border-accent-purple text-accent-purple'
                    : 'bg-bg-card border-white/5 text-text-muted'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Opportunities List */}
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
            </div>
          ) : sorted.length === 0 ? (
            <div className="text-center text-text-muted text-sm py-12">
              {regionFilter !== 'all'
                ? `No opportunities for ${CONTINENT_LABELS[regionFilter]}. Try "All Regions".`
                : `No arbitrage opportunities found. Scanning ${exchangeCount || 19} exchanges every 30 seconds...`}
            </div>
          ) : (
            <div className="space-y-2">
              {sorted.map((opp, i) => (
                <ArbitrageCard
                  key={opp.id || i}
                  opp={opp}
                  isExpanded={expandedCoin === opp.coin_id}
                  onExpand={(id) => setExpandedCoin(expandedCoin === id ? null : id)}
                />
              ))}
            </div>
          )}
        </>
      )}

      <p className="text-text-muted text-[9px] text-center leading-relaxed">
        Prices across {exchangeCount || 19} exchanges worldwide with per-exchange fee rates. Tap a card to see all prices. Filter by region to find cross-border opportunities.
      </p>
    </div>
  )
}
