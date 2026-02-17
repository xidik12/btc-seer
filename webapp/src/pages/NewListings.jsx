import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice, formatTimeAgo } from '../utils/format'

const TABS = ['listings', 'dex-trending', 'dex-to-cex']

function ListingCard({ listing }) {
  const change1h = listing.change_pct_1h
  const change24h = listing.change_pct_24h

  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-text-primary">{listing.symbol}</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-accent-blue/20 text-accent-blue rounded font-medium">
            {listing.exchange}
          </span>
          <span className="text-[10px] text-text-muted">{listing.listing_type}</span>
        </div>
        <span className="text-[10px] text-text-muted">{formatTimeAgo(listing.timestamp)}</span>
      </div>

      {listing.price_at_listing && (
        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-text-muted">Listed at: </span>
            <span className="font-bold">{formatCoinPrice(listing.price_at_listing)}</span>
          </div>
          {change1h != null && (
            <div>
              <span className="text-text-muted">1h: </span>
              <span className={`font-bold ${change1h >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {change1h > 0 ? '+' : ''}{change1h.toFixed(1)}%
              </span>
            </div>
          )}
          {change24h != null && (
            <div>
              <span className="text-text-muted">24h: </span>
              <span className={`font-bold ${change24h >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {change24h > 0 ? '+' : ''}{change24h.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      )}

      {listing.was_on_dex_first && (
        <span className="text-[9px] px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded mt-1 inline-block">
          DEX first
        </span>
      )}
    </div>
  )
}

function DexTokenCard({ token }) {
  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-text-primary">{token.symbol || '???'}</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-white/5 text-text-muted rounded capitalize">{token.chain}</span>
          {token.boosts > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 bg-accent-yellow/20 text-accent-yellow rounded">
              {token.boosts} boosts
            </span>
          )}
        </div>
        {token.is_on_cex && (
          <span className="text-[9px] px-1.5 py-0.5 bg-accent-green/20 text-accent-green rounded font-medium">
            ON CEX
          </span>
        )}
      </div>

      <p className="text-xs text-text-secondary mb-1">{token.name}</p>

      <div className="flex items-center gap-4 text-[10px] text-text-muted">
        {token.price_usd && <span>Price: {formatCoinPrice(token.price_usd)}</span>}
        {token.volume_24h && <span>Vol: ${(token.volume_24h / 1000).toFixed(1)}K</span>}
        {token.liquidity && <span>Liq: ${(token.liquidity / 1000).toFixed(1)}K</span>}
      </div>

      <p className="text-[9px] text-text-muted mt-1 font-mono truncate">{token.address}</p>
    </div>
  )
}

export default function NewListings() {
  const { t } = useTranslation('common')
  const [tab, setTab] = useState('listings')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const fetch = async () => {
      try {
        let result
        if (tab === 'listings') {
          result = await api.getNewListings()
          setData(result?.listings || [])
        } else if (tab === 'dex-trending') {
          result = await api.getDexTrending()
          setData(result?.tokens || [])
        } else {
          result = await api.getDexToCex()
          setData(result?.tokens || [])
        }
      } catch (err) {
        console.error('Listings fetch error:', err)
        setData([])
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [tab])

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">New Listings</h1>

      {/* Tab Bar */}
      <div className="flex gap-2">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              tab === t
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {t === 'listings' ? 'CEX Listings' : t === 'dex-trending' ? 'DEX Trending' : 'DEX → CEX'}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data.length === 0 ? (
        <div className="text-center text-text-muted text-sm py-12">
          No data yet. Scanning exchanges for new listings...
        </div>
      ) : (
        <div className="space-y-2">
          {tab === 'listings'
            ? data.map((item, i) => <ListingCard key={item.id || i} listing={item} />)
            : data.map((item, i) => <DexTokenCard key={item.id || i} token={item} />)
          }
        </div>
      )}
    </div>
  )
}
