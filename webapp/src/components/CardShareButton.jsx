import { useShareCard } from '../hooks/useShareCard'
import SharePreviewSheet from './SharePreviewSheet'

/**
 * Small share icon button that captures a card ref as PNG and shows preview sheet.
 *
 * Usage:
 *   const cardRef = useRef(null)
 *   <div ref={cardRef}>...</div>
 *   <CardShareButton cardRef={cardRef} label="Power Law" filename="powerlaw.png" />
 */
export default function CardShareButton({ cardRef, label, filename }) {
  const { capturing, previewUrl, capture, clearPreview } = useShareCard()

  return (
    <>
      <button
        onClick={(e) => { e.stopPropagation(); capture(cardRef, label) }}
        disabled={capturing}
        className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20 active:scale-95 transition-all disabled:opacity-50"
        title="Share as image"
      >
        {capturing ? (
          <div className="w-4 h-4 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        )}
      </button>

      <SharePreviewSheet
        previewUrl={previewUrl}
        filename={filename}
        onClose={clearPreview}
      />
    </>
  )
}
