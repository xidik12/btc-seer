import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

const IMPORTANCE_COLORS = {
  high: 'bg-accent-red',
  medium: 'bg-accent-yellow',
  low: 'bg-text-muted',
}

function formatEventDate(dateStr) {
  const d = new Date(dateStr)
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const dateOnly = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })

  if (d.toDateString() === now.toDateString()) return `Today ${time}`
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow ${time}`
  return `${dateOnly} ${time}`
}

export default function EconomicCalendar() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchEvents = useCallback(async () => {
    try {
      const result = await api.getEconomicCalendar(14)
      setEvents(result?.events || [])
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-4 w-36 bg-bg-secondary rounded mb-3" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-bg-secondary rounded mb-2" />
        ))}
      </div>
    )
  }

  if (!events.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <h3 className="text-text-primary font-semibold text-sm mb-3">Economic Calendar</h3>

      <div className="space-y-1">
        {events.slice(0, 10).map((event, i) => {
          const impColor = IMPORTANCE_COLORS[event.importance] || IMPORTANCE_COLORS.low
          const isPast = new Date(event.event_date) < new Date()

          return (
            <div
              key={i}
              className={`flex items-center gap-3 py-2 border-b border-white/5 last:border-0 ${
                isPast ? 'opacity-50' : ''
              }`}
            >
              {/* Importance dots */}
              <div className="flex gap-0.5 shrink-0">
                {[1, 2, 3].map((dot) => (
                  <div
                    key={dot}
                    className={`w-1.5 h-1.5 rounded-full ${
                      (event.importance === 'high' && dot <= 3) ||
                      (event.importance === 'medium' && dot <= 2) ||
                      (event.importance === 'low' && dot <= 1)
                        ? impColor
                        : 'bg-bg-secondary'
                    }`}
                  />
                ))}
              </div>

              {/* Event info */}
              <div className="flex-1 min-w-0">
                <p className="text-text-primary text-xs font-medium truncate">{event.event_name}</p>
                <p className="text-text-muted text-[10px]">{formatEventDate(event.event_date)}</p>
              </div>

              {/* Country badge */}
              <span className="text-[9px] font-mono bg-bg-secondary rounded px-1.5 py-0.5 text-text-muted shrink-0">
                {event.country || 'US'}
              </span>

              {/* Values */}
              {(event.actual || event.forecast || event.previous) && (
                <div className="text-right shrink-0">
                  {event.actual && (
                    <p className="text-accent-green text-[10px] font-semibold">{event.actual}</p>
                  )}
                  {event.forecast && !event.actual && (
                    <p className="text-text-secondary text-[10px]">F: {event.forecast}</p>
                  )}
                  {event.previous && (
                    <p className="text-text-muted text-[10px]">P: {event.previous}</p>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {events.length > 10 && (
        <p className="text-text-muted text-[10px] text-center mt-2">
          +{events.length - 10} more events
        </p>
      )}
    </div>
  )
}
