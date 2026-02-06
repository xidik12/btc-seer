import { useLocation, useNavigate } from 'react-router-dom'

const tabs = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/signals', label: 'Signals', icon: '📈' },
  { path: '/news', label: 'News', icon: '📰' },
  { path: '/history', label: 'History', icon: '🎯' },
]

export default function NavBar() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary border-t border-white/5 flex justify-around items-center h-16 z-50">
      {tabs.map((tab) => {
        const active = location.pathname === tab.path
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={`flex flex-col items-center gap-0.5 px-4 py-2 transition-colors ${
              active ? 'text-accent-blue' : 'text-text-muted'
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            <span className="text-[10px] font-medium">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
