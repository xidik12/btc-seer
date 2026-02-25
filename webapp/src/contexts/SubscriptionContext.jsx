import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
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

  // Only trust cache if it says premium (positive cache)
  const cached = getCachedState()
  const initialState = (cached && cached.isPremium) ? cached : { ...DEFAULT_STATE, loading: true }
  const [state, setState] = useState(initialState)
  const retryRef = useRef(null)

  const fetchStatus = useCallback(async (initData, retryCount = 0) => {
    if (!initData) {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
      return
    }

    try {
      const res = await api.registerUser(initData)
      const user = res?.user
      if (user) {
        const newState = {
          isPremium: !!user.is_premium,
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
      // Both endpoints failed — do NOT cache the error state
      setState((s) => ({ ...s, loading: false }))
      // Retry up to 3 times with exponential backoff
      if (retryCount < 3) {
        const delay = Math.min(3000 * Math.pow(2, retryCount), 15000)
        retryRef.current = setTimeout(() => fetchStatus(initData, retryCount + 1), delay)
      }
    }
  }, [])

  useEffect(() => {
    fetchStatus(tg?.initData)
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
    }
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
