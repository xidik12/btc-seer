import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice, formatTimeAgo } from '../utils/format'

const TABS = ['listings', 'dex-trending', 'dex-to-cex']

function PerformanceBadge({ pct, label }) {
  if (pct == null) return null
  const color = pct >= 0 ? 'text-accent-green' : 'text-accent-red'
  return (
    <div className="flex items-center gap-1">
      <span className="text-text-muted text-[10px]">{label}:</span>
      <span className={`font-bold text-[10px] ${color}`}>
        {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
      </span>
    </div>
  )
}

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
        <div className="flex items-center gap-4 text-xs mb-1">
          <div>
            <span className="text-text-muted">Listed at: </span>
            <span className="font-bold">{formatCoinPrice(listing.price_at_listing)}</span>
          </div>
          <PerformanceBadge pct={change1h} label="1h" />
          <PerformanceBadge pct={change24h} label="24h" />
        </div>
      )}

      {/* Performance tracking bar */}
      {(change1h != null || change24h != null) && (
        <div className="flex gap-1 mt-1.5">
          {change1h != null && (
            <div className="flex-1 h-1 rounded-full overflow-hidden bg-white/5">
              <div
                className={`h-full rounded-full ${change1h >= 0 ? 'bg-accent-green' : 'bg-accent-red'}`}
                style={{ width: `${Math.min(100, Math.abs(change1h) * 2)}%` }}
              />
            </div>
          )}
          {change24h != null && (
            <div className="flex-1 h-1 rounded-full overflow-hidden bg-white/5">
              <div
                className={`h-full rounded-full ${change24h >= 0 ? 'bg-accent-green' : 'bg-accent-red'}`}
                style={{ width: `${Math.min(100, Math.abs(change24h) * 2)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {listing.was_on_dex_first && (
        <span className="text-[9px] px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded mt-1.5 inline-block">
          DEX first
        </span>
      )}

      {listing.announcement_url && (
        <a
          href={listing.announcement_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[9px] text-accent-blue hover:underline mt-1 inline-block"
          onClick={e => e.stopPropagation()}
        >
          View announcement
        </a>
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
            {t === 'listings' ? 'CEX Listings' : t === 'dex-trending' ? 'DEX Trending' : 'DEX \u2192 CEX'}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-text-muted text-sm">
            {tab === 'listings' ? 'No new CEX listings detected' : 'No tokens found'}
          </p>
          <div className="bg-bg-card rounded-xl p-4 border border-white/5 max-w-sm mx-auto text-left space-y-2">
            {tab === 'listings' ? (
              <>
                <p className="text-text-secondary text-xs leading-relaxed">
                  New Binance listings are rare events (typically 1-3 per week). The scanner checks every 30 seconds for new trading pairs and monitors announcements every 2 minutes.
                </p>
                <p className="text-text-muted text-[10px]">
                  When a new listing is detected, price performance is tracked at 1h and 24h intervals. Check back regularly or try the DEX Trending tab.
                </p>
              </>
            ) : tab === 'dex-trending' ? (
              <p className="text-text-secondary text-xs leading-relaxed">
                DEX trending tokens are scanned from DexScreener every 5 minutes. Tokens must have &gt;$10K volume and &gt;$5K liquidity.
              </p>
            ) : (
              <p className="text-text-secondary text-xs leading-relaxed">
                DEX-to-CEX migrations are checked every 30 minutes by cross-referencing DexScreener tokens against Binance listings.
              </p>
            )}
          </div>
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
