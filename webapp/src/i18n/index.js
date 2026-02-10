import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import commonEN from './locales/en/common.json'

// Lazy-load namespace backend
const LazyImportBackend = {
  type: 'backend',
  read(language, namespace, callback) {
    if (language === 'en' && namespace === 'common') {
      callback(null, commonEN)
      return
    }
    import(`./locales/${language}/${namespace}.json`)
      .then((mod) => callback(null, mod.default || mod))
      .catch((err) => callback(err, null))
  },
}

i18n
  .use(LazyImportBackend)
  .use(initReactI18next)
  .init({
    lng: localStorage.getItem('btc-seer-lang') || undefined,
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: ['common'],
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
    detection: { order: [] },
    resources: {
      en: { common: commonEN },
    },
    partialBundledLanguages: true,
  })

export default i18n
