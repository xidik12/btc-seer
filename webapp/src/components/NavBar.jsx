import { useLocation, useNavigate } from 'react-router-dom'

// Outline SVG icons (24x24 viewBox, stroke-based)
const icons = {
  home: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  technical: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 16l4-6 4 4 5-8" />
    </svg>
  ),
  signals: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  ),
  news: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M10 6h8M10 10h8M10 14h4" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15.5 14" />
    </svg>
  ),
  powerlaw: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 20c2-4 5-10 9-13s7-4 11-5" />
      <path d="M2 20h20" />
      <path d="M2 20V4" />
    </svg>
  ),
  liquidations: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2c-4 4.5-8 8.5-8 13a8 8 0 0016 0c0-4.5-4-8.5-8-13z" />
      <path d="M12 18a4 4 0 01-4-4c0-2.5 2-4.5 4-7" />
    </svg>
  ),
  about: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
}

const tabs = [
  { path: '/', label: 'Home', icon: 'home' },
  { path: '/technical', label: 'Technical', icon: 'technical' },
  { path: '/signals', label: 'Signals', icon: 'signals' },
  { path: '/news', label: 'News', icon: 'news' },
  { path: '/history', label: 'History', icon: 'history' },
  { path: '/powerlaw', label: 'Power Law', icon: 'powerlaw' },
  { path: '/liquidations', label: 'Liquids', icon: 'liquidations' },
  { path: '/about', label: 'About', icon: 'about' },
]

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary/95 backdrop-blur-md border-t border-white/5 flex justify-around items-center h-16 z-50">
      {tabs.map((tab) => {
        const active = location.pathname === tab.path
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={`flex flex-col items-center gap-0.5 px-1.5 py-2 transition-all duration-200 ${
              active
                ? 'text-accent-blue'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <span className={`w-5 h-5 transition-transform duration-200 ${active ? 'scale-110' : ''}`}>
              {icons[tab.icon]}
            </span>
            <span className={`text-[9px] font-medium transition-colors ${active ? 'text-accent-blue' : ''}`}>
              {tab.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
