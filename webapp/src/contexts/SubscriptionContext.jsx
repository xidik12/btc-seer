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
    } catch {
      // Silent — user sees free tier until next refresh
    }
  }, [])

  const fetchStatus = useCallback(async (initData) => {
    if (!initData) {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
      return
    }

    // Fast timeout — don't block UI on cold Railway starts
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
      // If aborted due to timeout, use cached state or default and retry in background
      if (err.name === 'AbortError') {
        setState((s) => ({ ...s, loading: false }))
        _retryInBackground(initData)
        return
      }
      // Registration failed — try subscription status endpoint
    }

    try {
      const sub = await api.getSubscriptionStatus(initData)
      const newState = {
        isPremium: !!sub?.is_premium,
        isAdmin: false,
        tier: sub?.tier || 'none',
        daysLeft: sub?.days_remaining ?? 0,
        statusText: sub?.status_text || '',
        loading: false,
      }
      setState(newState)
      saveCachedState(newState)
    } catch {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
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
