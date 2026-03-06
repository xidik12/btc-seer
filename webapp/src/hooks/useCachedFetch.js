import { useState, useEffect, useCallback, useRef } from 'react'
import { getCached } from '../utils/api'

/**
 * Hook that initializes state from cache synchronously (no skeleton flash)
 * and polls for fresh data at the given interval.
 *
 * @param {() => Promise<T>} fetchFn  - The API function to call
 * @param {string} cacheKey           - The endpoint key used in api.js cache
 * @param {number} [pollInterval=0]   - Auto-refresh interval in ms (0 = no poll)
 * @returns {{ data: T|null, loading: boolean, error: string|null, refresh: () => void }}
 */
export default function useCachedFetch(fetchFn, cacheKey, pollInterval = 0) {
  const cached = getCached(cacheKey)
  const [data, setData] = useState(cached ?? null)
  const [loading, setLoading] = useState(cached == null)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  const refresh = useCallback(async () => {
    try {
      const result = await fetchFn()
      if (mountedRef.current) {
        setData(result)
        setError(null)
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message)
        setLoading(false)
      }
    }
  }, [fetchFn])

  useEffect(() => {
    mountedRef.current = true
    refresh()
    let interval
    if (pollInterval > 0) {
      interval = setInterval(refresh, pollInterval)
    }
    return () => {
      mountedRef.current = false
      if (interval) clearInterval(interval)
    }
  }, [refresh, pollInterval])

  return { data, loading, error, refresh }
}
