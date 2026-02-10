import { useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

const STORAGE_KEY = 'btc-seer-lang'
const SUPPORTED = ['en', 'ru', 'zh']

function detectLanguage() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && SUPPORTED.includes(saved)) return saved

  const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
  if (tgLang) {
    if (SUPPORTED.includes(tgLang)) return tgLang
    const prefix = tgLang.slice(0, 2)
    if (SUPPORTED.includes(prefix)) return prefix
  }

  return 'en'
}

export function useLanguageInit() {
  const { i18n } = useTranslation()

  useEffect(() => {
    const lang = detectLanguage()
    if (i18n.language !== lang) {
      i18n.changeLanguage(lang)
    }
  }, [i18n])
}

export function useLanguageSwitch() {
  const { i18n } = useTranslation()

  const currentLang = i18n.language || 'en'

  const switchLanguage = useCallback((lang) => {
    if (SUPPORTED.includes(lang)) {
      localStorage.setItem(STORAGE_KEY, lang)
      i18n.changeLanguage(lang)
    }
  }, [i18n])

  return { currentLang, switchLanguage, supported: SUPPORTED }
}
