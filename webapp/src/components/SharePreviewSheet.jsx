import { useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { getBotUsernameSync } from '../utils/botConfig'

/**
 * Bottom sheet showing image preview + share actions (Telegram / Download / More).
 */
export default function SharePreviewSheet({ previewUrl, filename, onClose }) {
  const { t } = useTranslation('common')

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleTelegram = useCallback(() => {
    const bot = getBotUsernameSync() || 'BTC_Seer_Bot'
    const url = `https://t.me/share/url?url=${encodeURIComponent(`https://t.me/${bot}`)}&text=${encodeURIComponent('Check out this BTC Seer analysis!')}`
    const tg = window.Telegram?.WebApp
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(url)
    } else {
      window.open(url, '_blank')
    }
  }, [])

  const handleDownload = useCallback(() => {
    if (!previewUrl) return
    const a = document.createElement('a')
    a.href = previewUrl
    a.download = filename || 'btc-seer.png'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }, [previewUrl, filename])

  const handleNativeShare = useCallback(async () => {
    if (!previewUrl) return
    try {
      const res = await fetch(previewUrl)
      const blob = await res.blob()
      const file = new File([blob], filename || 'btc-seer.png', { type: 'image/png' })

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: 'BTC Seer',
          text: 'Check out this BTC Seer analysis!',
        })
      } else {
        // Fallback: copy link
        const bot = getBotUsernameSync() || 'BTC_Seer_Bot'
        await navigator.clipboard.writeText(`https://t.me/${bot}`)
      }
    } catch (err) {
      if (err.name !== 'AbortError') console.error('Share failed:', err)
    }
  }, [previewUrl, filename])

  if (!previewUrl) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-50" onClick={onClose} />

      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-bg-secondary rounded-t-2xl p-4 pb-8 slide-up max-h-[85vh] overflow-y-auto">
        {/* Handle */}
        <div className="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4" />

        {/* Preview Image */}
        <div className="rounded-xl overflow-hidden mb-4 border border-white/10">
          <img
            src={previewUrl}
            alt="Card preview"
            className="w-full h-auto"
          />
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-3 gap-2">
          {/* Telegram */}
          <button
            onClick={handleTelegram}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-[#2AABEE]/15 border border-[#2AABEE]/30 active:scale-95 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="#2AABEE" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
            <span className="text-[10px] font-semibold text-[#2AABEE]">Telegram</span>
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-accent-blue/10 border border-accent-blue/30 active:scale-95 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-accent-blue">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span className="text-[10px] font-semibold text-accent-blue">{t('share.download')}</span>
          </button>

          {/* More (native share) */}
          <button
            onClick={handleNativeShare}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-white/5 border border-white/10 active:scale-95 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-text-secondary">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
            <span className="text-[10px] font-semibold text-text-secondary">{t('share.more')}</span>
          </button>
        </div>
      </div>
    </>
  )
}
