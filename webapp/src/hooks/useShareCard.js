import { useState, useCallback } from 'react'
import { captureCard } from '../utils/captureCard'

/**
 * Hook for capturing a card as a shareable PNG image.
 * @returns {{ capturing, previewUrl, capture, clearPreview }}
 */
export function useShareCard() {
  const [capturing, setCapturing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState(null)

  const capture = useCallback(async (ref, label) => {
    if (!ref?.current || capturing) return
    setCapturing(true)

    // Haptic feedback
    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light') } catch {}

    try {
      const dataUrl = await captureCard(ref.current, label)
      setPreviewUrl(dataUrl)
    } catch (err) {
      console.error('Card capture failed:', err)
    } finally {
      setCapturing(false)
    }
  }, [capturing])

  const clearPreview = useCallback(() => {
    setPreviewUrl(null)
  }, [])

  return { capturing, previewUrl, capture, clearPreview }
}
