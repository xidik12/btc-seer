import { useState, useEffect, useCallback } from 'react'
import TutorialTooltip from './TutorialTooltip'
import tutorialSteps from './tutorialSteps'

export default function TutorialOverlay({ tutorial }) {
  const { step, totalSteps, next, prev, skip, active } = tutorial
  const [targetRect, setTargetRect] = useState(null)

  const stepData = tutorialSteps[step] || tutorialSteps[0]

  const updatePosition = useCallback(() => {
    if (!stepData?.target) {
      setTargetRect(null)
      return
    }
    const el = document.querySelector(stepData.target)
    if (el) {
      const rect = el.getBoundingClientRect()
      setTargetRect(rect)
      // Scroll element into view if needed
      const vh = window.innerHeight
      if (rect.top < 60 || rect.bottom > vh - 60) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        // Re-measure after scroll
        setTimeout(() => {
          setTargetRect(el.getBoundingClientRect())
        }, 350)
      }
    } else {
      setTargetRect(null)
    }
  }, [stepData?.target])

  useEffect(() => {
    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    const observer = new ResizeObserver(updatePosition)
    observer.observe(document.body)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
      observer.disconnect()
    }
  }, [updatePosition])

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'Enter') next()
      else if (e.key === 'ArrowLeft') prev()
      else if (e.key === 'Escape') skip()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [next, prev, skip])

  if (!active) return null

  const pad = 6

  // Build clip path to cut out the highlighted area
  const clipPath = targetRect
    ? `polygon(
        0% 0%, 0% 100%, 100% 100%, 100% 0%, 0% 0%,
        ${targetRect.left - pad}px ${targetRect.top - pad}px,
        ${targetRect.left - pad}px ${targetRect.bottom + pad}px,
        ${targetRect.right + pad}px ${targetRect.bottom + pad}px,
        ${targetRect.right + pad}px ${targetRect.top - pad}px,
        ${targetRect.left - pad}px ${targetRect.top - pad}px
      )`
    : undefined

  return (
    <>
      {/* Backdrop with cutout */}
      <div
        className="fixed inset-0 z-[9999] transition-all duration-300"
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          clipPath,
        }}
        onClick={next}
      />

      {/* Highlight ring */}
      {targetRect && (
        <div
          className="fixed z-[10000] pointer-events-none rounded-xl"
          style={{
            top: targetRect.top - pad,
            left: targetRect.left - pad,
            width: targetRect.width + pad * 2,
            height: targetRect.height + pad * 2,
            boxShadow: '0 0 0 2px #00d68f, 0 0 12px rgba(0, 214, 143, 0.3)',
            animation: 'tutorialPulse 2s ease-in-out infinite',
          }}
        />
      )}

      {/* Tooltip */}
      <TutorialTooltip
        step={step}
        totalSteps={totalSteps}
        stepData={stepData}
        onNext={next}
        onPrev={prev}
        onSkip={skip}
        position={stepData?.position || 'bottom'}
        targetRect={targetRect}
      />

      {/* Pulse animation */}
      <style>{`
        @keyframes tutorialPulse {
          0%, 100% { box-shadow: 0 0 0 2px #00d68f, 0 0 12px rgba(0, 214, 143, 0.3); }
          50% { box-shadow: 0 0 0 3px #00d68f, 0 0 20px rgba(0, 214, 143, 0.5); }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.25s ease-out;
        }
      `}</style>
    </>
  )
}
