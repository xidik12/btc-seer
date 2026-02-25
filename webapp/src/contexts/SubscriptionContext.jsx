import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'

const SubscriptionContext = createContext({
  isPremium: false,
  isAdmin: false,
  tier: 'none',
  daysLeft: 0,
  statusText: '',
  loading: true,
  refresh: () => {},
})

export function SubscriptionProvider({ children }) {
  const { tg } = useTelegram()
  const [state, setState] = useState({
    isPremium: false,
    isAdmin: false,
    tier: 'none',
    daysLeft: 0,
    statusText: '',
    loading: true,
  })

  const fetchStatus = useCallback(async (initData) => {
    if (!initData) {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
      return
    }

    try {
      // Register user (also grants trial on first use) and get premium status
      const res = await api.registerUser(initData)
      const user = res?.user
      if (user) {
        setState({
          isPremium: !!user.is_premium,
          isAdmin: !!user.is_admin,
          tier: user.subscription_status || (user.is_premium ? 'active' : 'none'),
          daysLeft: user.days_remaining ?? 0,
          statusText: user.status_text || '',
          loading: false,
        })
        return
      }
    } catch {
      // Registration failed — try subscription status endpoint
    }

    try {
      const sub = await api.getSubscriptionStatus(initData)
      setState({
        isPremium: !!sub?.is_premium,
        tier: sub?.tier || 'none',
        daysLeft: sub?.days_remaining ?? 0,
        statusText: sub?.status_text || '',
        loading: false,
      })
    } catch {
      setState((s) => ({ ...s, loading: false, isPremium: false, tier: 'none' }))
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
