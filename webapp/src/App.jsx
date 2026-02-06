import { Routes, Route } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import Dashboard from './pages/Dashboard'
import Signals from './pages/Signals'
import News from './pages/News'
import History from './pages/History'
import NavBar from './components/NavBar'

export default function App() {
  useTelegram()

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary pb-20">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/news" element={<News />} />
        <Route path="/history" element={<History />} />
      </Routes>
      <NavBar />
    </div>
  )
}
