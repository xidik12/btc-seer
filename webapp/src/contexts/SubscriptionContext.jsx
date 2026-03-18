import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'

const CACHE_KEY = 'btc_sub_state'

function getCachedState() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (raw) {
      const cached = JSON.parse(raw)
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

  // KEY OPTIMIZATION: Use cache immediately — never block render on first load.
  // If cache exists, user sees the app instantly. Fresh data updates in background.
  const cached = getCachedState()
  const [state, setState] = useState(
    cached || { ...DEFAULT_STATE, loading: true }
  )

  const fetchStatus = useCallback(async (initData) => {
    if (!initData) {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
      return
    }

    // If we have cache, don't block — fetch silently in background
    const hasCachedPremium = cached?.isPremium || cached?.isAdmin

    // Shorter timeout: 3s for warm starts, cache covers cold starts
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)

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
      if (err.name === 'AbortError') {
        // Timed out — trust cache, retry once in background
        if (hasCachedPremium) {
          setState((s) => ({ ...s, ...cached, loading: false }))
        }
        // Single background retry after 2s (not 3 retries)
        setTimeout(async () => {
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
            }
          } catch {}
        }, 2000)
        return
      }
    }

    // Fallback: try subscription status endpoint
    try {
      const sub = await api.getSubscriptionStatus(initData)
      setState((prev) => {
        const newState = {
          isPremium: !!sub?.is_premium || prev.isAdmin,
          isAdmin: prev.isAdmin,
          tier: sub?.tier || 'none',
          daysLeft: sub?.days_remaining ?? 0,
          statusText: sub?.status_text || '',
          loading: false,
        }
        saveCachedState(newState)
        return newState
      })
    } catch {
      // Both failed — use cache or default
      if (hasCachedPremium) {
        setState((s) => ({ ...s, ...cached, loading: false }))
      } else {
        setState((s) => ({ ...s, loading: false }))
      }
    }
  }, [])

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
