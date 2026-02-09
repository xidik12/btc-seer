import { useState, useRef, useCallback, useMemo } from 'react'

/**
 * Touch-based pinch-to-zoom and pan for charts.
 * Returns sliced data + container event handlers.
 *
 * Usage:
 *   const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(fullData)
 *   <div {...bindGestures}> <Chart data={visibleData} /> </div>
 */
export function useChartZoom(data, { minWindow = 5 } = {}) {
  const len = data?.length || 0

  // range as [0..1] percentages of data array
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(1)

  // Touch state refs (no re-render needed)
  const touchState = useRef({
    pinching: false,
    panning: false,
    initialDist: 0,
    initialStart: 0,
    initialEnd: 0,
    lastX: 0,
  })

  const isZoomed = end - start < 0.98

  const resetZoom = useCallback(() => {
    setStart(0)
    setEnd(1)
  }, [])

  const getDistance = (t1, t2) => {
    const dx = t1.clientX - t2.clientX
    const dy = t1.clientY - t2.clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  const onTouchStart = useCallback((e) => {
    const ts = touchState.current
    if (e.touches.length === 2) {
      // Pinch start
      e.preventDefault()
      ts.pinching = true
      ts.panning = false
      ts.initialDist = getDistance(e.touches[0], e.touches[1])
      ts.initialStart = start
      ts.initialEnd = end
    } else if (e.touches.length === 1 && isZoomed) {
      // Pan start (only when zoomed in)
      ts.panning = true
      ts.pinching = false
      ts.lastX = e.touches[0].clientX
      ts.initialStart = start
      ts.initialEnd = end
    }
  }, [start, end, isZoomed])

  const onTouchMove = useCallback((e) => {
    const ts = touchState.current

    if (ts.pinching && e.touches.length === 2) {
      e.preventDefault()
      const newDist = getDistance(e.touches[0], e.touches[1])
      const scale = ts.initialDist / newDist // >1 = zoom in, <1 = zoom out

      const initWindow = ts.initialEnd - ts.initialStart
      const newWindow = Math.max(minWindow / Math.max(len, 1), Math.min(1, initWindow * scale))

      // Zoom centered on middle of current view
      const center = (ts.initialStart + ts.initialEnd) / 2
      let newStart = center - newWindow / 2
      let newEnd = center + newWindow / 2

      // Clamp
      if (newStart < 0) { newEnd -= newStart; newStart = 0 }
      if (newEnd > 1) { newStart -= (newEnd - 1); newEnd = 1 }
      newStart = Math.max(0, newStart)
      newEnd = Math.min(1, newEnd)

      setStart(newStart)
      setEnd(newEnd)
    }

    if (ts.panning && e.touches.length === 1) {
      const dx = e.touches[0].clientX - ts.lastX
      ts.lastX = e.touches[0].clientX

      // Convert pixel delta to data fraction
      // Assume chart width ~350px (mobile)
      const frac = -dx / 350 * (end - start)
      let newStart = start + frac
      let newEnd = end + frac

      if (newStart < 0) { newEnd -= newStart; newStart = 0 }
      if (newEnd > 1) { newStart -= (newEnd - 1); newEnd = 1 }
      newStart = Math.max(0, newStart)
      newEnd = Math.min(1, newEnd)

      setStart(newStart)
      setEnd(newEnd)
    }
  }, [start, end, len, minWindow])

  const onTouchEnd = useCallback(() => {
    touchState.current.pinching = false
    touchState.current.panning = false
  }, [])

  // Double tap to reset
  const lastTap = useRef(0)
  const onDoubleClick = useCallback(() => {
    const now = Date.now()
    if (now - lastTap.current < 300) {
      resetZoom()
    }
    lastTap.current = now
  }, [resetZoom])

  const visibleData = useMemo(() => {
    if (!data || !data.length) return data || []
    const s = Math.floor(start * len)
    const e = Math.ceil(end * len)
    return data.slice(s, e)
  }, [data, start, end, len])

  const bindGestures = {
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    onClick: onDoubleClick,
    style: { touchAction: isZoomed ? 'none' : 'pan-y' },
  }

  return { data: visibleData, bindGestures, isZoomed, resetZoom }
}
