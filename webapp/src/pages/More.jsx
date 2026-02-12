import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'

const menuItems = [
  {
    path: '/history',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <circle cx="12" cy="12" r="9" />
        <polyline points="12 7 12 12 15.5 14" />
      </svg>
    ),
    labelKey: 'link.history',
    descKey: 'nav.back',
  },
  {
    path: '/whales',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M3 12c0-3.5 3-7 9-7s9 3.5 9 7-3 6-9 6-9-2.5-9-6z" />
        <circle cx="8" cy="11" r="1" fill="currentColor" />
        <path d="M21 12c1 1 2 2 2 3" />
      </svg>
    ),
    labelKey: 'link.whales',
    descKey: 'nav.forward',
  },
  {
    path: '/news',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
        <path d="M10 6h8M10 10h8M10 14h4" />
      </svg>
    ),
    labelKey: 'link.news',
    descKey: 'nav.forward',
  },
  {
    path: '/advisor',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    ),
    labelKey: 'link.advisor',
    descKey: 'nav.home',
  },
  {
    path: '/subscription',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    ),
    labelKey: 'link.premium',
    descKey: 'nav.forward',
  },
  {
    external: true,
    href: 'https://t.me/BTCSeerSignals',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M22 2L11 13" />
        <path d="M22 2L15 22L11 13L2 9L22 2Z" />
      </svg>
    ),
    labelKey: 'link.signalsChannel',
    descKey: 'nav.forward',
  },
  {
    path: '/settings',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
      </svg>
    ),
    labelKey: 'link.settings',
    descKey: 'nav.home',
  },
  {
    path: '/about',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
    labelKey: 'link.about',
    descKey: 'nav.forward',
  },
]

export default function More() {
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()
  const { t } = useTranslation('common')

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">{t('category.more')}</h1>

      <div className="space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.href || item.path}
            onClick={() => { hapticFeedback?.selectionChanged(); item.external ? window.open(item.href, '_blank') : navigate(item.path) }}
            className="w-full flex items-center gap-3 bg-bg-card rounded-xl p-4 border border-white/5 hover:bg-bg-hover transition-colors text-left slide-up"
          >
            <span className="text-accent-blue shrink-0">{item.icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-text-primary text-sm font-medium">{t(item.labelKey)}</p>
            </div>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        ))}
      </div>

      <p className="text-text-muted text-[10px] text-center pt-4">
        {t('app.title')} v1.0
      </p>
    </div>
  )
}
