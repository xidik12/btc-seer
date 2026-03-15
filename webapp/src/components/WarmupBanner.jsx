import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

const AUTO_DISMISS_MS = 90_000
const POLL_INTERVAL_MS = 5_000

export default function WarmupBanner() {
  const [visible, setVisible] = useState(false)
  const pollRef = useRef(null)
  const dismissTimerRef = useRef(null)
  const { t } = useTranslation('common')

  useEffect(() => {
    let cancelled = false

    const API_BASE = import.meta.env.VITE_API_URL || '/api'
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`)
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return

        if (data.data_ready === false) {
          setVisible(true)
        } else {
          setVisible(false)
          clearInterval(pollRef.current)
          clearTimeout(dismissTimerRef.current)
        }
      } catch {
        // network error during warmup — ignore silently
      }
    }

    checkHealth()
    pollRef.current = setInterval(checkHealth, POLL_INTERVAL_MS)

    dismissTimerRef.current = setTimeout(() => {
      if (!cancelled) setVisible(false)
      clearInterval(pollRef.current)
    }, AUTO_DISMISS_MS)

    return () => {
      cancelled = true
      clearInterval(pollRef.current)
      clearTimeout(dismissTimerRef.current)
    }
  }, [])

  if (!visible) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-[1000] bg-bg-secondary border-b border-white/[0.06] flex items-center justify-center gap-2 px-4 py-1.5">
      <span className="inline-block w-3 h-3 border-2 border-accent-yellow/25 border-t-accent-yellow rounded-full animate-spin shrink-0" />
      <span className="text-xs text-text-muted tracking-wide">
        {t('warmup.loading', 'Waking up\u2026 data loading')}
      </span>
    </div>
  )
}
