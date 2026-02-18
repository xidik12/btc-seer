import { useEffect, useMemo } from 'react'

export function useTelegram() {
  const tg = useMemo(() => window.Telegram?.WebApp, [])

  useEffect(() => {
    if (tg) {
      tg.ready()
      tg.expand()
      tg.setHeaderColor('#0f0f14')
      tg.setBackgroundColor('#0f0f14')
    }
  }, [tg])

  return {
    tg,
    user: tg?.initDataUnsafe?.user,
    initData: tg?.initData || '',
    colorScheme: tg?.colorScheme || 'dark',
    isAvailable: !!tg,
    close: () => tg?.close(),
    showAlert: (msg) => tg?.showAlert(msg),
    hapticFeedback: tg?.HapticFeedback,
  }
}
