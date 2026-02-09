import { useLocation, useNavigate } from 'react-router-dom'
import { useTelegram } from '../hooks/useTelegram'

const icons = {
  home: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  analysis: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-6 4 4 5-8" />
    </svg>
  ),
  markets: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2c-4 4.5-8 8.5-8 13a8 8 0 0016 0c0-4.5-4-8.5-8-13z" />
      <path d="M12 18a4 4 0 01-4-4c0-2.5 2-4.5 4-7" />
    </svg>
  ),
  coins: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8" />
      <path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5 1-2.5 2s1 2 2.5 2 2.5 1 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5" />
      <path d="M12 6.5v1M12 16.5v1" />
    </svg>
  ),
  more: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="5" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="12" cy="19" r="1.5" />
    </svg>
  ),
}

const tabs = [
  { path: '/', label: 'Home', icon: 'home', matchPaths: ['/'] },
  { path: '/technical', label: 'Analysis', icon: 'analysis', matchPaths: ['/technical', '/signals'] },
  { path: '/liquidations', label: 'Markets', icon: 'markets', matchPaths: ['/liquidations', '/powerlaw', '/events'] },
  { path: '/coins', label: 'Coins', icon: 'coins', matchPaths: ['/coins'] },
  { path: '/more', label: 'More', icon: 'more', matchPaths: ['/more', '/news', '/advisor', '/about', '/settings', '/history'] },
]

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary/95 backdrop-blur-md border-t border-white/5 flex justify-around items-center h-16 z-50">
      {tabs.map((tab) => {
        const active = tab.matchPaths.some(p =>
          p === '/' ? location.pathname === '/' : location.pathname.startsWith(p)
        )
        return (
          <button
            key={tab.path}
            onClick={() => { hapticFeedback?.selectionChanged(); navigate(tab.path) }}
            className={`flex flex-col items-center gap-0.5 px-3 py-2 transition-all duration-200 ${
              active
                ? 'text-accent-blue'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <span className={`w-5 h-5 transition-transform duration-200 ${active ? 'scale-110' : ''}`}>
              {icons[tab.icon]}
            </span>
            <span className={`text-[10px] font-medium transition-colors ${active ? 'text-accent-blue' : ''}`}>
              {tab.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
