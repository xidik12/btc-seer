import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { getBotUsernameSync } from '../utils/botConfig'
import { api } from '../utils/api'

const isTelegramWebView = !!window.Telegram?.WebApp

/** Convert a data URL to a Blob (works everywhere, no fetch needed) */
function dataUrlToBlob(dataUrl) {
  const [header, b64] = dataUrl.split(',')
  const mime = header.match(/:(.*?);/)[1]
  const bin = atob(b64)
  const u8 = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i)
  return new Blob([u8], { type: mime })
}

/** Trigger a file download via <a download> — for regular browsers */
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'btc-seer.png'
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/** Get Telegram initData string */
function getInitData() {
  return window.Telegram?.WebApp?.initData || ''
}

/**
 * Bottom sheet showing image preview + share actions (Share / Download / Copy Link).
 */
export default function SharePreviewSheet({ previewUrl, filename, onClose }) {
  const { t } = useTranslation('common')
  const [loading, setLoading] = useState(null) // 'share' | 'download' | null
  const [toast, setToast] = useState(null) // { type: 'success' | 'error', text: string }

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 2500)
    return () => clearTimeout(timer)
  }, [toast])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Lock body scroll when sheet is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  // ── Share Image (Upload + Telegram share dialog, or Web Share API elsewhere) ──
  const handleShareImage = useCallback(async () => {
    if (!previewUrl || loading) return

    if (isTelegramWebView) {
      setLoading('share')
      try {
        // Upload image and get share ID for the OG-tagged view page
        const { id: shareId } = await api.uploadShareImage(getInitData(), previewUrl)
        const viewUrl = `${window.location.origin}/api/share/view/${shareId}`

        // Open Telegram's native share dialog — rich card preview + bot link
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(viewUrl)}`

        window.Telegram.WebApp.openTelegramLink(shareUrl)
        onClose()
      } catch (err) {
        console.error('Share failed:', err)
        setToast({ type: 'error', text: t('share.sendFailed', 'Failed to share image') })
      } finally {
        setLoading(null)
      }
      return
    }

    // Regular browser — Web Share API
    try {
      const blob = dataUrlToBlob(previewUrl)
      const file = new File([blob], filename || 'btc-seer.png', { type: 'image/png' })

      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: 'BTC Seer' })
        return
      }

      if (navigator.share) {
        const bot = getBotUsernameSync() || 'BTC_Seer_Bot'
        await navigator.share({ title: 'BTC Seer', url: `https://t.me/${bot}` })
        return
      }

      // Last resort: download
      triggerDownload(blob, filename)
    } catch (err) {
      if (err.name !== 'AbortError') console.error('Share failed:', err)
    }
  }, [previewUrl, filename, loading, onClose, t])

  // ── Download (upload to backend + HTTPS URL in TG, blob download elsewhere) ──
  const handleDownload = useCallback(async () => {
    if (!previewUrl || loading) return

    if (isTelegramWebView) {
      setLoading('download')
      try {
        const { url: relativePath } = await api.uploadShareImage(getInitData(), previewUrl)
        // Build full HTTPS URL from current origin
        const fullUrl = `${window.location.origin}${relativePath}`
        const fname = filename || 'btc-seer.png'

        // Try Telegram WebApp.downloadFile (Bot API 7.10+)
        if (window.Telegram.WebApp.downloadFile) {
          try {
            window.Telegram.WebApp.downloadFile({ url: fullUrl, file_name: fname })
            setToast({ type: 'success', text: t('share.downloading', 'Downloading...') })
            return
          } catch (_) {
            // Fall through to openLink
          }
        }

        // Fallback: open HTTPS URL in external browser (user can save from there)
        window.Telegram.WebApp.openLink(fullUrl)
      } catch (err) {
        console.error('Upload for download failed:', err)
        setToast({ type: 'error', text: t('share.downloadFailed', 'Download failed') })
      } finally {
        setLoading(null)
      }
      return
    }

    // Regular browser — blob download
    const blob = dataUrlToBlob(previewUrl)
    triggerDownload(blob, filename)
  }, [previewUrl, filename, loading, t])

  // ── Copy Link (unchanged — already works) ──
  const [copied, setCopied] = useState(false)
  const handleCopyLink = useCallback(async () => {
    try {
      const bot = getBotUsernameSync() || 'BTC_Seer_Bot'
      await navigator.clipboard.writeText(`https://t.me/${bot}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Copy failed:', err)
    }
  }, [])

  if (!previewUrl) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-50" onClick={onClose} />

      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-bg-secondary rounded-t-2xl p-4 pb-8 slide-up max-h-[85vh] overflow-y-auto">
        {/* Header with handle + close */}
        <div className="flex items-center justify-between mb-3">
          <div className="w-8" />
          <div className="w-10 h-1 bg-white/20 rounded-full" />
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 text-text-secondary hover:text-text-primary active:scale-90 transition-all"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Toast */}
        {toast && (
          <div className={`mb-3 px-3 py-2 rounded-lg text-xs font-medium text-center transition-all ${
            toast.type === 'success' ? 'bg-accent-green/15 text-accent-green' : 'bg-red-500/15 text-red-400'
          }`}>
            {toast.text}
          </div>
        )}

        {/* Preview Image */}
        <div className="rounded-xl overflow-hidden mb-4 border border-white/10">
          <img
            src={previewUrl}
            alt="Card preview"
            className="w-full h-auto"
          />
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {/* Share Image / Send to Chat */}
          <button
            onClick={handleShareImage}
            disabled={!!loading}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-[#2AABEE]/15 border border-[#2AABEE]/30 active:scale-95 transition-all disabled:opacity-50"
          >
            {loading === 'share' ? (
              <div className="w-5 h-5 border-2 border-[#2AABEE]/30 border-t-[#2AABEE] rounded-full animate-spin" />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="#2AABEE" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
            )}
            <span className="text-[10px] font-semibold text-[#2AABEE]">
              {t('share.shareImage', 'Share')}
            </span>
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            disabled={!!loading}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-accent-blue/10 border border-accent-blue/30 active:scale-95 transition-all disabled:opacity-50"
          >
            {loading === 'download' ? (
              <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-accent-blue">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            )}
            <span className="text-[10px] font-semibold text-accent-blue">{t('share.download')}</span>
          </button>

          {/* Copy Link */}
          <button
            onClick={handleCopyLink}
            className="flex flex-col items-center gap-1.5 py-3 rounded-xl bg-white/5 border border-white/10 active:scale-95 transition-all"
          >
            {copied ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-accent-green">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-text-secondary">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
              </svg>
            )}
            <span className={`text-[10px] font-semibold ${copied ? 'text-accent-green' : 'text-text-secondary'}`}>
              {copied ? 'Copied!' : t('share.more')}
            </span>
          </button>
        </div>

        {/* Cancel button */}
        <button
          onClick={onClose}
          className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-text-muted text-sm font-medium active:scale-[0.98] transition-all"
        >
          {t('share.cancel', 'Cancel')}
        </button>
      </div>
    </>
  )
}
