import { useState, useEffect, useRef } from 'react'

const AUTO_DISMISS_MS = 90_000
const POLL_INTERVAL_MS = 5_000

export default function WarmupBanner() {
  const [visible, setVisible] = useState(false)
  const pollRef = useRef(null)
  const dismissTimerRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    async function checkHealth() {
      try {
        const res = await fetch('/api/health')
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return

        if (data.data_ready === false) {
          setVisible(true)
        } else {
          // data is ready — dismiss and stop polling
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

    // Hard cap: auto-dismiss after 90 seconds regardless
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
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: '#1a1a24',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        padding: '6px 16px',
      }}
    >
      {/* Spinner */}
      <span
        style={{
          display: 'inline-block',
          width: '12px',
          height: '12px',
          border: '2px solid rgba(255,184,0,0.25)',
          borderTopColor: '#ffb800',
          borderRadius: '50%',
          animation: 'warmup-spin 0.7s linear infinite',
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: '12px',
          color: '#9090a8',
          letterSpacing: '0.01em',
        }}
      >
        Waking up&hellip; data loading
      </span>
      <style>{`
        @keyframes warmup-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
