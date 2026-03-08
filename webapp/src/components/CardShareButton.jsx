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
        data-share-btn="true"
        onClick={(e) => { e.stopPropagation(); capture(cardRef, label) }}
        disabled={capturing}
        className="p-1.5 rounded-lg bg-white/5 text-text-muted hover:text-accent-blue hover:bg-accent-blue/10 active:scale-90 transition-all disabled:opacity-50"
        title="Share as image"
      >
        {capturing ? (
          <div className="w-3.5 h-3.5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
            <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8" />
            <polyline points="16 6 12 2 8 6" />
            <line x1="12" y1="2" x2="12" y2="15" />
          </svg>
        )}
      </button>

      {previewUrl && (
        <SharePreviewSheet
          previewUrl={previewUrl}
          filename={filename}
          onClose={clearPreview}
        />
      )}
    </>
  )
}
