import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()
  const { t } = useTranslation()

  const isHome = location.pathname === '/'

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary/95 backdrop-blur-md border-t border-white/5 flex justify-around items-center h-14 z-50" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      {/* Back */}
      <button
        onClick={() => { hapticFeedback?.selectionChanged(); window.history.length > 1 ? navigate(-1) : navigate('/') }}
        disabled={isHome}
        className={`flex flex-col items-center gap-0.5 px-6 py-2 transition-all duration-200 ${
          isHome ? 'text-accent-yellow/20' : 'text-accent-yellow/60 hover:text-accent-yellow active:scale-90'
        }`}
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
        <span className="text-[9px] font-medium">{t('nav.back')}</span>
      </button>

      {/* Home */}
      <button
        onClick={() => { hapticFeedback?.selectionChanged(); navigate('/') }}
        className={`flex flex-col items-center gap-0.5 px-6 py-2 transition-all duration-200 ${
          isHome ? 'text-accent-yellow' : 'text-accent-yellow/60 hover:text-accent-yellow active:scale-90'
        }`}
      >
        <svg className={`w-6 h-6 transition-transform duration-200 ${isHome ? 'scale-110' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
          <path d="M9 21V12h6v9" />
        </svg>
        <span className="text-[9px] font-medium">{t('nav.home')}</span>
      </button>

      {/* Forward */}
      <button
        onClick={() => { hapticFeedback?.selectionChanged(); navigate(1) }}
        className="flex flex-col items-center gap-0.5 px-6 py-2 transition-all duration-200 text-accent-yellow/60 hover:text-accent-yellow active:scale-90"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18l6-6-6-6" />
        </svg>
        <span className="text-[9px] font-medium">{t('nav.forward')}</span>
      </button>
    </nav>
  )
}
