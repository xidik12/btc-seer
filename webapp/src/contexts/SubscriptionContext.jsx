import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'

const CACHE_KEY = 'btc_sub_state'

function getCachedState() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (raw) {
      const cached = JSON.parse(raw)
      // Use cached state but mark as not loading (optimistic render)
      return { ...cached, loading: false, _fromCache: true }
    }
  } catch {}
  return null
}

function saveCachedState(state) {
  try {
    const { loading, refresh, _fromCache, ...rest } = state
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(rest))
  } catch {}
}

const SubscriptionContext = createContext({
  isPremium: false,
  isAdmin: false,
  tier: 'none',
  daysLeft: 0,
  statusText: '',
  loading: true,
  refresh: () => {},
})

const DEFAULT_STATE = {
  isPremium: false,
  isAdmin: false,
  tier: 'none',
  daysLeft: 0,
  statusText: '',
}

export function SubscriptionProvider({ children }) {
  const { tg } = useTelegram()

  // Initialize from cache for instant render, or default with loading=true
  const cached = getCachedState()
  const [state, setState] = useState(
    cached || { ...DEFAULT_STATE, loading: true }
  )

  const _retryInBackground = useCallback(async (initData) => {
    // Retry up to 3 times with increasing delays (cold start recovery)
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt > 0) await new Promise(r => setTimeout(r, attempt * 2000))
      try {
        const res = await api.registerUser(initData)
        const user = res?.user
        if (user) {
          const newState = {
            isPremium: !!user.is_premium || !!user.is_admin,
            isAdmin: !!user.is_admin,
            tier: user.subscription_status || (user.is_premium ? 'active' : 'none'),
            daysLeft: user.days_remaining ?? 0,
            statusText: user.status_text || '',
            loading: false,
          }
          setState(newState)
          saveCachedState(newState)
          return
        }
      } catch {
        // Retry on next iteration
      }
    }
  }, [])

  const fetchStatus = useCallback(async (initData) => {
    if (!initData) {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
      return
    }

    // Timeout for cold Railway starts — 5s gives enough time for warm worker
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)

    try {
      const res = await api.registerUser(initData, { signal: controller.signal })
      clearTimeout(timeout)
      const user = res?.user
      if (user) {
        const newState = {
          isPremium: !!user.is_premium || !!user.is_admin,
          isAdmin: !!user.is_admin,
          tier: user.subscription_status || (user.is_premium ? 'active' : 'none'),
          daysLeft: user.days_remaining ?? 0,
          statusText: user.status_text || '',
          loading: false,
        }
        setState(newState)
        saveCachedState(newState)
        return
      }
    } catch (err) {
      clearTimeout(timeout)
      // If aborted due to timeout, keep loading=true (don't show paywall) and retry
      if (err.name === 'AbortError') {
        const cached = getCachedState()
        if (cached && cached.isPremium) {
          // Trust the cache — user was premium last time
          setState((s) => ({ ...s, ...cached, loading: false }))
        }
        // Either way, retry in background — keep loading=true if no premium cache
        _retryInBackground(initData)
        return
      }
      // Registration failed — try subscription status endpoint
    }

    try {
      const sub = await api.getSubscriptionStatus(initData)
      setState((prev) => {
        const newState = {
          isPremium: !!sub?.is_premium || prev.isAdmin,
          isAdmin: prev.isAdmin,  // preserve admin from cache — never downgrade here
          tier: sub?.tier || 'none',
          daysLeft: sub?.days_remaining ?? 0,
          statusText: sub?.status_text || '',
          loading: false,
        }
        saveCachedState(newState)
        return newState
      })
    } catch {
      // If both register and status failed, use cache if available
      const cached = getCachedState()
      if (cached && cached.isPremium) {
        setState((s) => ({ ...s, ...cached, loading: false }))
      } else {
        setState((s) => ({ ...s, loading: false }))
      }
    }
  }, [_retryInBackground])

  useEffect(() => {
    fetchStatus(tg?.initData)
  }, [tg, fetchStatus])

  const refresh = useCallback(() => {
    if (tg?.initData) {
      setState((s) => ({ ...s, loading: true }))
      fetchStatus(tg.initData)
    }
  }, [tg, fetchStatus])

  return (
    <SubscriptionContext.Provider value={{ ...state, refresh }}>
      {children}
    </SubscriptionContext.Provider>
  )
}

export function useSubscription() {
  return useContext(SubscriptionContext)
}
