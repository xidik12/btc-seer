import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api.js'
import { formatNumber } from '../utils/format.js'

export default function OnChainWidget() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const res = await api.getOnchainData()
      setData(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 300_000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-3">On-Chain Metrics</h3>
        <div className="grid grid-cols-2 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-bg-secondary rounded-xl p-3 animate-pulse min-h-[70px]">
              <div className="h-2 w-12 bg-bg-card rounded mb-3" />
              <div className="h-4 w-16 bg-bg-card rounded" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 slide-up">
        <h3 className="text-text-primary font-semibold text-sm mb-2">On-Chain Metrics</h3>
        <div className="flex flex-col items-center py-4 gap-2">
          <p className="text-accent-red text-sm">Failed to load on-chain data</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  const metrics = [
    {
      label: 'Exchange Reserves',
      value: data?.exchange_reserve != null ? `${formatNumber(data.exchange_reserve)} BTC` : '--',
      change: data?.reserve_change_24h,
      desc: data?.reserve_change_24h < 0 ? 'Outflow (bullish)' : 'Inflow (bearish)',
    },
    {
      label: 'Large Transactions',
      value: data?.large_tx_count != null ? formatNumber(data.large_tx_count) : '--',
      desc: 'Txns > $100K (24h)',
    },
    {
      label: 'Active Addresses',
      value: data?.active_addresses != null ? formatNumber(data.active_addresses) : '--',
      desc: 'Unique senders (24h)',
    },
    {
      label: 'Hash Rate',
      value: data?.hash_rate != null ? `${formatNumber(data.hash_rate)} EH/s` : '--',
      desc: 'Network security',
    },
  ]

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-primary font-semibold text-sm">On-Chain Metrics</h3>
        <span className="text-text-muted text-[10px]">Whale watching</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {metrics.map((m) => (
          <div key={m.label} className="bg-bg-secondary rounded-xl p-3 min-h-[70px] flex flex-col justify-between">
            <span className="text-text-muted text-[10px]">{m.label}</span>
            <div>
              <p className="text-text-primary font-semibold text-sm">{m.value}</p>
              {m.change != null ? (
                <p className={`text-[10px] mt-0.5 ${m.change < 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {m.change > 0 ? '+' : ''}{m.change.toFixed(1)}% {m.desc}
                </p>
              ) : (
                <p className="text-text-muted text-[10px] mt-0.5">{m.desc}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
