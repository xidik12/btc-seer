import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../utils/api'
import { formatCoinPrice, formatPercent } from '../utils/format'
import { useTelegram } from '../hooks/useTelegram'

function detectAddressChain(address) {
  if (/^0x[a-fA-F0-9]{40}$/.test(address)) return 'Ethereum / EVM'
  if (/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address)) return 'Solana'
  return null
}

export default function CoinSearch() {
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [addressResult, setAddressResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [detectedChain, setDetectedChain] = useState(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setAddressResult(null)
      setDetectedChain(null)
      return
    }

    const chain = detectAddressChain(query.trim())
    setDetectedChain(chain)

    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        if (chain) {
          const result = await api.searchCoinByAddress(query.trim())
          setAddressResult(result.error ? null : result)
          setResults([])
        } else {
          const result = await api.searchCoins(query.trim())
          setResults(result.results || [])
          setAddressResult(null)
        }
      } catch {
        setResults([])
        setAddressResult(null)
      }
      setLoading(false)
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  return (
    <div className="px-4 pt-4 pb-20">
      {/* Search Header */}
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate('/coins')} className="text-accent-blue text-sm shrink-0">&larr;</button>
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search coins or paste address..."
            className="w-full bg-bg-card rounded-xl px-4 py-3 pl-10 text-sm text-text-primary border border-white/5 focus:border-accent-blue/50 focus:outline-none placeholder:text-text-muted"
          />
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>
      </div>

      {/* Chain Detection Indicator */}
      {detectedChain && (
        <div className="mb-3 px-3 py-2 bg-accent-blue/10 border border-accent-blue/20 rounded-lg">
          <p className="text-xs text-accent-blue">
            {loading ? `Searching by address on ${detectedChain}...` : `Detected ${detectedChain} address`}
          </p>
        </div>
      )}

      {/* Loading */}
      {loading && !detectedChain && (
        <div className="text-center text-text-muted text-xs py-8">Searching...</div>
      )}

      {/* Address Result */}
      {addressResult && !loading && (
        <button
          onClick={() => {
            hapticFeedback?.selectionChanged()
            if (addressResult.id) navigate(`/coins/${addressResult.id}`)
            else navigate(`/coins/report/${query.trim()}`)
          }}
          className="w-full bg-bg-card rounded-xl p-4 border border-white/5 hover:bg-bg-hover transition-colors text-left mb-3"
        >
          <div className="flex items-center gap-3">
            {addressResult.image ? (
              <img src={addressResult.image} alt="" className="w-10 h-10 rounded-full" />
            ) : (
              <div className="w-10 h-10 rounded-full bg-accent-blue/20" />
            )}
            <div className="flex-1">
              <p className="text-sm font-bold">{addressResult.name}</p>
              <p className="text-xs text-text-muted">{addressResult.symbol} · {addressResult.chain}</p>
            </div>
            <div className="text-right">
              {addressResult.price_usd && <p className="text-sm font-bold">{formatCoinPrice(addressResult.price_usd)}</p>}
              {addressResult.change_24h != null && (
                <p className={`text-[10px] ${addressResult.change_24h >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {formatPercent(addressResult.change_24h)}
                </p>
              )}
            </div>
          </div>
        </button>
      )}

      {/* Name Search Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-2">
          {results.map(coin => (
            <button
              key={coin.id}
              onClick={() => { hapticFeedback?.selectionChanged(); navigate(`/coins/${coin.id}`) }}
              className="w-full bg-bg-card rounded-xl p-3 border border-white/5 hover:bg-bg-hover transition-colors text-left flex items-center gap-3"
            >
              {coin.large ? (
                <img src={coin.large} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-accent-blue/20" />
              )}
              <div className="flex-1">
                <p className="text-sm font-semibold">{coin.name}</p>
                <p className="text-xs text-text-muted">{coin.symbol}</p>
              </div>
              {coin.market_cap_rank && (
                <span className="text-[10px] text-text-muted bg-white/5 px-2 py-0.5 rounded-full">#{coin.market_cap_rank}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !detectedChain && query.trim() && results.length === 0 && !addressResult && (
        <p className="text-text-muted text-xs text-center py-8">No coins found for "{query}"</p>
      )}

      {!query.trim() && (
        <div className="text-center py-12">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="w-12 h-12 text-text-muted/30 mx-auto mb-3">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <p className="text-text-muted text-xs">Search by name, symbol, or contract address</p>
        </div>
      )}
    </div>
  )
}
