import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'btcseer_tutorial_v1'
const TOTAL_STEPS = 21

export function useTutorial() {
  const [step, setStep] = useState(0)
  const [active, setActive] = useState(false)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'completed') {
      setCompleted(true)
      setActive(false)
    } else {
      setActive(true)
    }
  }, [])

  const next = useCallback(() => {
    if (step < TOTAL_STEPS - 1) {
      setStep(s => s + 1)
    } else {
      setActive(false)
      setCompleted(true)
      localStorage.setItem(STORAGE_KEY, 'completed')
    }
  }, [step])

  const prev = useCallback(() => {
    if (step > 0) setStep(s => s - 1)
  }, [step])

  const skip = useCallback(() => {
    setActive(false)
    setCompleted(true)
    localStorage.setItem(STORAGE_KEY, 'completed')
  }, [])

  const restart = useCallback(() => {
    setStep(0)
    setActive(true)
    setCompleted(false)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const goTo = useCallback((n) => {
    if (n >= 0 && n < TOTAL_STEPS) setStep(n)
  }, [])

  return {
    step,
    active: active && !completed,
    completed,
    totalSteps: TOTAL_STEPS,
    next,
    prev,
    skip,
    restart,
    goTo,
  }
}
