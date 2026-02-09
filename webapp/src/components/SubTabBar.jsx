import { useLocation, useNavigate } from 'react-router-dom'
import { useTelegram } from '../hooks/useTelegram'

export default function SubTabBar({ tabs }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { hapticFeedback } = useTelegram()

  return (
    <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5 mb-4 overflow-x-auto no-scrollbar">
      {tabs.map((tab) => {
        const active = location.pathname === tab.path
        return (
          <button
            key={tab.path}
            onClick={() => { hapticFeedback?.selectionChanged(); navigate(tab.path) }}
            className={`flex-shrink-0 whitespace-nowrap px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              active ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
