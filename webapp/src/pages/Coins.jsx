import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice, formatPercent, formatMarketCap } from '../utils/format'
import { useTelegram } from '../hooks/useTelegram'

function MiniSparkline({ data, color }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 60
  const h = 24
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ')
  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  )
}

export default function Coins() {
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()
  const { t } = useTranslation('coins')
  const [coins, setCoins] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [predictions, setPredictions] = useState({})

  useEffect(() => {
    api.getTrackedCoins().then(data => {
      setCoins(data.coins || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!coins.length) return
    const fetchPredictions = async () => {
      const preds = {}
      for (const coin of coins.slice(0, 20)) {
        try {
          const data = await api.getCoinPrediction(coin.coin_id || coin.id)
          if (data) preds[coin.coin_id || coin.id] = data
        } catch {}
      }
      setPredictions(preds)
    }
    fetchPredictions()
  }, [coins])

  // Debounced search
  useEffect(() => {
    if (!search.trim()) {
      setSearchResults(null)
      return
    }

    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        // Detect if it's an address
        const isAddress = /^0x[a-fA-F0-9]{40}$/.test(search.trim()) || /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(search.trim())
        if (isAddress) {
          const result = await api.searchCoinByAddress(search.trim())
          setSearchResults({ type: 'address', data: result.error ? null : result, error: result.error })
        } else {
          const result = await api.searchCoins(search.trim())
          setSearchResults({ type: 'name', data: result.results || [] })
        }
      } catch (e) {
        setSearchResults({ type: 'error', error: e.message })
      }
      setSearching(false)
    }, 300)

    return () => clearTimeout(timer)
  }, [search])

  const handleCoinTap = (coinId) => {
    hapticFeedback?.selectionChanged()
    navigate(`/coins/${coinId}`)
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">{t('title')}</h1>

      {/* Tracked Coins Grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-bg-card rounded-xl p-3 border border-white/5 animate-pulse h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {coins.map(coin => {
            const changeColor = (coin.change_24h || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
            const sparkColor = (coin.change_24h || 0) >= 0 ? '#22c55e' : '#ef4444'
            return (
              <button
                key={coin.coin_id}
                onClick={() => handleCoinTap(coin.coin_id)}
                className="bg-bg-card rounded-xl p-3 border border-white/5 hover:bg-bg-hover transition-colors text-left slide-up"
              >
                <div className="flex items-center gap-2 mb-2">
                  {coin.image_url ? (
                    <img src={coin.image_url} alt={coin.symbol} className="w-6 h-6 rounded-full" />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center text-[10px] font-bold text-accent-blue">
                      {coin.symbol?.[0]}
                    </div>
                  )}
                  <span className="text-xs font-semibold text-text-primary">{coin.symbol}</span>
                </div>
                <p className="text-sm font-bold">{formatCoinPrice(coin.price_usd)}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className={`text-[10px] font-medium ${changeColor}`}>
                    {formatPercent(coin.change_24h)}
                  </span>
                  {predictions[coin.coin_id || coin.id]?.direction && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ml-1 ${
                      predictions[coin.coin_id || coin.id].direction === 'bullish'
                        ? 'bg-accent-green/20 text-accent-green'
                        : predictions[coin.coin_id || coin.id].direction === 'bearish'
                        ? 'bg-accent-red/20 text-accent-red'
                        : 'bg-white/10 text-text-muted'
                    }`}>
                      {predictions[coin.coin_id || coin.id].direction === 'bullish' ? '▲' : predictions[coin.coin_id || coin.id].direction === 'bearish' ? '▼' : '◄►'}
                    </span>
                  )}
                  <MiniSparkline data={coin.sparkline} color={sparkColor} />
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t('searchPlaceholder')}
          className="w-full bg-bg-card rounded-xl px-4 py-3 pl-10 text-sm text-text-primary border border-white/5 focus:border-accent-blue/50 focus:outline-none placeholder:text-text-muted"
        />
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2">
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Search Results */}
      {searching && (
        <div className="text-center text-text-muted text-xs py-4">{t('search')}...</div>
      )}

      {searchResults && !searching && (
        <div className="space-y-2">
          {searchResults.type === 'address' && searchResults.data && (
            <button
              onClick={() => {
                hapticFeedback?.selectionChanged()
                if (searchResults.data.id) navigate(`/coins/${searchResults.data.id}`)
                else navigate(`/coins/report/${search.trim()}`)
              }}
              className="w-full bg-bg-card rounded-xl p-4 border border-white/5 hover:bg-bg-hover transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                {searchResults.data.image ? (
                  <img src={searchResults.data.image} alt="" className="w-8 h-8 rounded-full" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-accent-blue/20" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-semibold">{searchResults.data.name}</p>
                  <p className="text-xs text-text-muted">{searchResults.data.symbol} · {searchResults.data.chain}</p>
                </div>
                {searchResults.data.price_usd && (
                  <p className="text-sm font-bold">{formatCoinPrice(searchResults.data.price_usd)}</p>
                )}
              </div>
            </button>
          )}

          {searchResults.type === 'address' && !searchResults.data && (
            <p className="text-text-muted text-xs text-center py-2">{searchResults.error || t('noResults')}</p>
          )}

          {searchResults.type === 'name' && searchResults.data?.map(coin => (
            <button
              key={coin.id}
              onClick={() => handleCoinTap(coin.id)}
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

          {searchResults.type === 'name' && searchResults.data?.length === 0 && (
            <p className="text-text-muted text-xs text-center py-2">{t('noResults')}</p>
          )}

          {searchResults.type === 'error' && (
            <p className="text-accent-red text-xs text-center py-2">{searchResults.error}</p>
          )}
        </div>
      )}

      {/* Market Cap Summary */}
      {!search && coins.length > 0 && (
        <div className="bg-bg-card rounded-xl p-4 border border-white/5">
          <h3 className="text-xs font-semibold text-text-muted mb-3">{t('report.overview')}</h3>
          <div className="space-y-2">
            {coins.map(coin => (
              <div key={coin.coin_id} className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">{coin.name}</span>
                <span className="text-text-muted">{formatMarketCap(coin.market_cap)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
