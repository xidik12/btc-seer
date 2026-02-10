import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

export default function TutorialTooltip({
  step,
  totalSteps,
  stepData,
  onNext,
  onPrev,
  onSkip,
  position,
  targetRect,
}) {
  const { t } = useTranslation('tutorial')
  const isFirst = step === 0
  const isLast = step === totalSteps - 1
  const progress = ((step + 1) / totalSteps) * 100

  const style = useMemo(() => {
    if (!targetRect) {
      return {
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      }
    }

    const gap = 12
    const tooltipWidth = 300
    const vw = window.innerWidth
    const vh = window.innerHeight

    let top, left

    if (position === 'bottom') {
      top = targetRect.bottom + gap
      left = targetRect.left + targetRect.width / 2 - tooltipWidth / 2
    } else if (position === 'top') {
      top = targetRect.top - gap
      left = targetRect.left + targetRect.width / 2 - tooltipWidth / 2
    } else if (position === 'left') {
      top = targetRect.top + targetRect.height / 2
      left = targetRect.left - tooltipWidth - gap
    } else {
      top = targetRect.top + targetRect.height / 2
      left = targetRect.right + gap
    }

    // Clamp to viewport
    left = Math.max(12, Math.min(left, vw - tooltipWidth - 12))
    if (position === 'top') {
      top = Math.max(12, top)
    } else {
      top = Math.min(vh - 200, Math.max(12, top))
    }

    return {
      position: 'fixed',
      top: position === 'top' ? undefined : `${top}px`,
      bottom: position === 'top' ? `${vh - targetRect.top + gap}px` : undefined,
      left: `${left}px`,
      width: `${tooltipWidth}px`,
    }
  }, [targetRect, position])

  const descLines = stepData?.description?.split('\n') || []

  return (
    <div
      style={style}
      className="z-[10001] bg-bg-secondary/95 backdrop-blur-md border border-white/10 rounded-2xl shadow-card p-4 animate-fade-in"
    >
      {/* Progress bar */}
      <div className="h-0.5 bg-bg-hover rounded-full mb-3 overflow-hidden">
        <div
          className="h-full bg-accent-green rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step counter */}
      <div className="text-[10px] text-text-muted mb-1">
        {t('stepOf', 'Step {{current}} of {{total}}', { current: step + 1, total: totalSteps })}
      </div>

      {/* Title */}
      <div className="text-text-primary text-sm font-bold mb-2">
        {stepData?.title}
      </div>

      {/* Description */}
      <div className="text-text-secondary text-xs leading-relaxed mb-2 space-y-1">
        {descLines.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>

      {/* Example */}
      {stepData?.example && (
        <div className="bg-accent-green/10 border border-accent-green/20 rounded-lg px-3 py-2 mb-3">
          <div className="text-accent-green text-[10px] font-semibold mb-0.5">{t('tip', 'TIP')}</div>
          <div className="text-text-secondary text-[11px]">{stepData.example}</div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-3">
        <button
          onClick={onSkip}
          className="text-text-muted text-[10px] hover:text-text-secondary transition-colors"
        >
          {t('skipTutorial', 'Skip Tutorial')}
        </button>
        <div className="flex gap-2">
          {!isFirst && (
            <button
              onClick={onPrev}
              className="px-3 py-1.5 rounded-lg text-[10px] font-semibold bg-bg-hover text-text-secondary hover:bg-bg-hover/80 transition-colors"
            >
              {t('common:nav.back')}
            </button>
          )}
          <button
            onClick={onNext}
            className="px-4 py-1.5 rounded-lg text-[10px] font-bold bg-accent-green text-white hover:bg-accent-green/80 transition-colors"
          >
            {isLast ? t('finish', 'Finish') : t('next', 'Next')}
          </button>
        </div>
      </div>
    </div>
  )
}
