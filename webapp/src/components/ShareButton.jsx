import { useState, useCallback } from 'react'

/**
 * Reusable share button with Copy + Telegram Share actions.
 * Props:
 *   text - The share text content
 *   botLink - Optional direct bot link (overrides default)
 *   compact - If true, render smaller inline button
 */
export default function ShareButton({ text, botLink, compact = false }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    if (!text) return
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }, [text])

  const handleTelegramShare = useCallback(() => {
    if (!text) return
    const url = `https://t.me/share/url?url=${encodeURIComponent(botLink || 'https://t.me/BTCSeerBot')}&text=${encodeURIComponent(text)}`
    window.open(url, '_blank')
  }, [text, botLink])

  if (compact) {
    return (
      <button
        onClick={handleTelegramShare}
        className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20 active:scale-95 transition-all"
        title="Share"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
          <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8" />
          <polyline points="16 6 12 2 8 6" />
          <line x1="12" y1="2" x2="12" y2="15" />
        </svg>
      </button>
    )
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={handleCopy}
        className="flex-1 py-2 rounded-xl bg-bg-secondary text-text-primary text-xs font-semibold active:scale-[0.98] transition-all"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
      <button
        onClick={handleTelegramShare}
        className="flex-1 py-2 rounded-xl bg-accent-blue text-white text-xs font-semibold active:scale-[0.98] transition-all flex items-center justify-center gap-1"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
          <path d="M22 2L11 13" />
          <path d="M22 2L15 22L11 13L2 9L22 2Z" />
        </svg>
        Share
      </button>
    </div>
  )
}
