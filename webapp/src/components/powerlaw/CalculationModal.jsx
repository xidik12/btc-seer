import { useTranslation } from 'react-i18next'
import { useEffect, useRef, useCallback } from 'react'

export default function CalculationModal({ calc, label, onClose }) {
  const { t } = useTranslation(['market'])
  const contentRef = useRef(null)

  // Lock body scroll when modal is open
  useEffect(() => {
    const scrollY = window.scrollY
    document.body.style.position = 'fixed'
    document.body.style.top = `-${scrollY}px`
    document.body.style.left = '0'
    document.body.style.right = '0'
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.left = ''
      document.body.style.right = ''
      document.body.style.overflow = ''
      window.scrollTo(0, scrollY)
    }
  }, [])

  useEffect(() => {
    const handleEsc = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  // Prevent touch events on backdrop from scrolling through
  const handleBackdropTouch = useCallback((e) => {
    e.preventDefault()
  }, [])

  if (!calc) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={onClose}
      onTouchMove={handleBackdropTouch}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div
        ref={contentRef}
        className="relative w-full max-w-md mx-auto bg-bg-secondary rounded-t-2xl sm:rounded-2xl border border-white/10 shadow-2xl max-h-[80vh] overflow-y-auto overscroll-contain animate-slide-up touch-pan-y"
        onClick={(e) => e.stopPropagation()}
        onTouchMove={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg-secondary border-b border-white/5 px-4 py-3 flex items-center justify-between rounded-t-2xl z-10">
          <div>
            <h3 className="text-text-primary text-sm font-bold">{label}</h3>
            <div className="text-accent-blue text-[10px] font-medium mt-0.5">
              {t('market:powerLaw.calculation.howCalculated')}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 text-text-muted hover:text-text-primary transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 1L11 11M1 11L11 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Formula */}
          <div>
            <div className="text-text-muted text-[10px] font-medium uppercase tracking-wider mb-1.5">
              {t('market:powerLaw.calculation.formula')}
            </div>
            <div className="bg-bg-card rounded-xl p-3 border border-white/5">
              <code className="text-accent-yellow text-xs font-mono break-all">{calc.formula}</code>
            </div>
          </div>

          {/* Inputs */}
          {calc.inputs && Object.keys(calc.inputs).length > 0 && (
            <div>
              <div className="text-text-muted text-[10px] font-medium uppercase tracking-wider mb-1.5">
                {t('market:powerLaw.calculation.inputs')}
              </div>
              <div className="bg-bg-card rounded-xl border border-white/5 divide-y divide-white/5">
                {Object.entries(calc.inputs).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between px-3 py-2">
                    <span className="text-text-muted text-[11px] font-mono">{key}</span>
                    <span className="text-text-primary text-[11px] font-mono font-medium">
                      {typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 6 }) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Steps */}
          {calc.steps && calc.steps.length > 0 && (
            <div>
              <div className="text-text-muted text-[10px] font-medium uppercase tracking-wider mb-1.5">
                {t('market:powerLaw.calculation.steps')}
              </div>
              <div className="bg-bg-card rounded-xl p-3 border border-white/5 space-y-2">
                {calc.steps.map((step, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-accent-blue text-[10px] font-bold mt-0.5 shrink-0">{i + 1}.</span>
                    <code className="text-text-secondary text-[11px] font-mono break-all">{step}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Explanation */}
          {calc.explanation && (
            <div>
              <div className="text-text-muted text-[10px] font-medium uppercase tracking-wider mb-1.5">
                {t('market:powerLaw.calculation.explanation')}
              </div>
              <div className="bg-bg-card rounded-xl p-3 border border-white/5">
                <p className="text-text-secondary text-xs leading-relaxed">{calc.explanation}</p>
              </div>
            </div>
          )}
        </div>

        {/* Safe area padding for mobile */}
        <div className="h-6" />
      </div>
    </div>
  )
}

export function ClickableStat({ label, value, subtext, color, calcKey, calculations, onShowCalc }) {
  const hasCalc = calculations && calcKey && calculations[calcKey]

  return (
    <div
      className={`bg-bg-card rounded-xl p-3 border border-white/5 ${hasCalc ? 'cursor-pointer hover:border-accent-blue/30 hover:bg-white/[0.02] active:scale-[0.98] transition-all' : ''}`}
      onClick={() => hasCalc && onShowCalc(calcKey, label)}
    >
      <div className="flex items-center gap-1">
        <div className="text-text-muted text-[9px] font-medium mb-1 flex-1">{label}</div>
        {hasCalc && (
          <svg className="w-2.5 h-2.5 text-accent-blue/40 mb-1 shrink-0" viewBox="0 0 10 10" fill="none">
            <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
            <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
          </svg>
        )}
      </div>
      <div className={`text-sm font-bold tabular-nums ${color || 'text-text-primary'}`}>{value}</div>
      {subtext && <div className="text-text-muted text-[9px] mt-0.5">{subtext}</div>}
    </div>
  )
}
