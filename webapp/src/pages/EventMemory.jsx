import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { formatTimeAgo, formatPercent } from '../utils/format'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', label: 'Liquidations' },
  { path: '/powerlaw', label: 'Power Law' },
  { path: '/elliott-wave', label: 'Elliott Wave' },
  { path: '/events', label: 'Events' },
  { path: '/tools', label: 'Tools' },
  { path: '/learn', label: 'Learn' },
]

const TIMEFRAMES = ['1h', '4h', '24h', '7d']

function getImpactColor(impact) {
  if (impact == null) return 'bg-bg-hover'
  const abs = Math.abs(impact)
  if (abs > 2) return impact > 0 ? 'bg-accent-green/60' : 'bg-accent-red/60'
  if (abs > 1) return impact > 0 ? 'bg-accent-green/40' : 'bg-accent-red/40'
  if (abs > 0.3) return impact > 0 ? 'bg-accent-green/20' : 'bg-accent-red/20'
  return 'bg-accent-yellow/15'
}

function getImpactText(impact) {
  if (impact == null) return '--'
  return `${impact > 0 ? '+' : ''}${impact.toFixed(2)}%`
}

function CategoryHeatmap({ stats }) {
  if (!stats?.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-1">CATEGORY IMPACT HEATMAP</h3>
      <p className="text-text-muted text-[9px] mb-3">Average BTC price change after events by category and timeframe</p>

      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-text-muted border-b border-white/5">
              <th className="text-left py-2 font-medium pr-2">Category</th>
              {TIMEFRAMES.map(tf => (
                <th key={tf} className="text-center py-2 font-medium px-1">{tf}</th>
              ))}
              <th className="text-center py-2 font-medium px-1">Count</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((cat) => (
              <tr key={cat.category} className="border-b border-white/5">
                <td className="py-2 pr-2 text-text-primary font-medium capitalize text-xs">
                  {cat.category?.replace(/_/g, ' ')}
                </td>
                {TIMEFRAMES.map(tf => {
                  const impact = cat[`avg_impact_${tf}`] ?? cat[`impact_${tf}`]
                  return (
                    <td key={tf} className="py-1 px-1">
                      <div className={`rounded px-1.5 py-1 text-center font-mono text-[10px] ${getImpactColor(impact)} text-text-primary`}>
                        {getImpactText(impact)}
                      </div>
                    </td>
                  )
                })}
                <td className="text-center text-text-muted py-2">{cat.count || '--'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function EventCard({ event }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="bg-bg-card rounded-xl border border-white/5 p-3 slide-up cursor-pointer hover:border-white/10 transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-2">
        <span className="text-base mt-0.5">
          {event.category === 'regulation' ? '&#x2696;&#xFE0F;' :
           event.category === 'etf' ? '&#x1F4C8;' :
           event.category === 'hack' ? '&#x1F6A8;' :
           event.category === 'adoption' ? '&#x1F680;' :
           event.category === 'macro' ? '&#x1F30D;' : '&#x1F4F0;'}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-text-primary leading-snug line-clamp-2">{event.title || event.summary}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[9px] text-accent-blue uppercase font-medium capitalize">
              {event.category?.replace(/_/g, ' ')}
            </span>
            <span className="text-[9px] text-text-muted">{formatTimeAgo(event.timestamp)}</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-2 border-t border-white/5">
          <div className="grid grid-cols-4 gap-1">
            {TIMEFRAMES.map(tf => {
              const impact = event[`change_pct_${tf}`] ?? event[`impact_${tf}`] ?? event[`price_change_${tf}`]
              return (
                <div key={tf} className={`rounded-lg p-2 text-center ${getImpactColor(impact)}`}>
                  <div className="text-[9px] text-text-muted">{tf}</div>
                  <div className="text-xs font-bold text-text-primary tabular-nums">
                    {getImpactText(impact)}
                  </div>
                </div>
              )
            })}
          </div>
          {event.description && (
            <p className="text-text-muted text-[10px] mt-2">{event.description}</p>
          )}
        </div>
      )}
    </div>
  )
}

function MemoryStats({ memory }) {
  if (!memory) return null

  const stats = [
    { label: 'Events Tracked', value: memory.total_events || '--' },
    { label: 'Categories', value: memory.categories || '--' },
    { label: 'Avg Events/Day', value: memory.avg_per_day?.toFixed(1) || '--' },
    { label: 'Most Impactful', value: memory.most_impactful_category?.replace(/_/g, ' ') || '--' },
  ]

  return (
    <div className="grid grid-cols-2 gap-2">
      {stats.map(s => (
        <div key={s.label} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{s.label}</div>
          <div className="text-text-primary text-sm font-bold capitalize">{s.value}</div>
        </div>
      ))}
    </div>
  )
}

export default function EventMemory() {
  const [events, setEvents] = useState([])
  const [categoryStats, setCategoryStats] = useState([])
  const [memory, setMemory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const [evts, cats, mem] = await Promise.all([
        api.getRecentEvents(48),
        api.getEventCategoryStats(),
        api.getEventMemory(),
      ])
      setEvents(evts?.events || evts || [])
      setCategoryStats(cats?.categories || cats || [])
      setMemory(mem)
    } catch (err) {
      setError(err.message || 'Failed to load events')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Event Memory</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-20 bg-bg-card rounded-2xl" />
          <div className="h-48 bg-bg-card rounded-2xl" />
          <div className="h-32 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Event Memory</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">Failed to load events</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchData} className="text-accent-blue text-xs hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Event Memory</h1>
        <span className="text-text-muted text-[10px]">Historical pattern analysis</span>
      </div>

      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
        <p className="text-text-muted text-[11px] leading-relaxed">
          The Event Memory system tracks market events and measures their actual price impact across
          multiple timeframes. When similar events happen again, you'll know the historical pattern.
        </p>
      </div>

      <MemoryStats memory={memory} />
      <CategoryHeatmap stats={categoryStats} />

      <div>
        <h3 className="text-text-secondary text-xs font-semibold mb-2">
          RECENT EVENTS ({Array.isArray(events) ? events.length : 0})
        </h3>
        {Array.isArray(events) && events.length > 0 ? (
          <div className="space-y-2">
            {events.map((e, i) => (
              <EventCard key={e.id || i} event={e} />
            ))}
          </div>
        ) : (
          <div className="text-center text-text-muted py-10 text-sm">
            No events tracked yet. Events will appear as they are detected.
          </div>
        )}
      </div>
    </div>
  )
}
