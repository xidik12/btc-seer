import { useState, useEffect, useCallback } from 'react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'
import ShareButton from '../components/ShareButton'
import { gameShareText } from '../utils/shareTemplates'

const PERIOD_TABS = ['all_time', 'weekly', 'monthly']
const PERIOD_LABELS = { all_time: 'All Time', weekly: 'Weekly', monthly: 'Monthly' }

export default function PredictionGame() {
  const { tg } = useTelegram()
  const [status, setStatus] = useState(null)
  const [leaderboard, setLeaderboard] = useState([])
  const [period, setPeriod] = useState('all_time')
  const [history, setHistory] = useState([])
  const [consensus, setConsensus] = useState(null)
  const [currentPrice, setCurrentPrice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [predicting, setPredicting] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [refCode, setRefCode] = useState(null)

  const initData = tg?.initData

  const fetchData = useCallback(() => {
    const promises = [
      api.getCurrentPrice().then((r) => setCurrentPrice(r?.price || r?.close)).catch(() => {}),
      api.getGameConsensus().then(setConsensus).catch(() => {}),
      api.getGameLeaderboard(period).then((r) => setLeaderboard(r?.leaderboard || [])).catch(() => {}),
    ]
    if (initData) {
      promises.push(
        api.getGameStatus(initData).then(setStatus).catch(() => {}),
        api.getReferralInfo(initData).then((r) => setRefCode(r?.referral_code)).catch(() => {}),
      )
    }
    Promise.all(promises).finally(() => setLoading(false))
  }, [initData, period])

  useEffect(() => { fetchData() }, [fetchData])

  const handlePredict = async (direction) => {
    if (!initData || predicting) return
    setPredicting(true)
    try {
      await api.makeGamePrediction(initData, direction, '24h')
      fetchData()
    } catch (err) {
      alert(err.message || 'Failed')
    }
    setPredicting(false)
  }

  const handleShowHistory = () => {
    if (!showHistory && initData) {
      api.getGameHistory(initData).then((r) => setHistory(r?.predictions || [])).catch(() => {})
    }
    setShowHistory((v) => !v)
  }

  const profile = status?.profile
  const current = status?.current_prediction
  const hasPredicted = !!current
  const upPct = consensus?.up_pct || 50
  const downPct = consensus?.down_pct || 50

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Prediction Game</h1>

      {/* Current BTC Price */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 text-center">
        <p className="text-text-muted text-xs mb-1">Current BTC Price</p>
        <p className="text-text-primary font-bold text-2xl">
          ${currentPrice ? Number(currentPrice).toLocaleString() : '—'}
        </p>
      </div>

      {/* UP / DOWN Buttons */}
      {!hasPredicted ? (
        <div className="space-y-2">
          <p className="text-text-muted text-xs text-center">Will BTC go UP or DOWN in the next 24h?</p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => handlePredict('up')}
              disabled={predicting || !initData}
              className="py-6 rounded-2xl bg-accent-green/10 border-2 border-accent-green/30 text-accent-green font-bold text-xl active:scale-95 transition-all disabled:opacity-50 hover:bg-accent-green/20"
            >
              🟢 UP
            </button>
            <button
              onClick={() => handlePredict('down')}
              disabled={predicting || !initData}
              className="py-6 rounded-2xl bg-accent-red/10 border-2 border-accent-red/30 text-accent-red font-bold text-xl active:scale-95 transition-all disabled:opacity-50 hover:bg-accent-red/20"
            >
              🔴 DOWN
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">Your Prediction</h3>
            <ShareButton
              compact
              text={gameShareText(current, profile, refCode)}
            />
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-2xl font-bold ${current.direction === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
              {current.direction === 'up' ? '🟢 UP' : '🔴 DOWN'}
            </span>
            <div className="text-text-muted text-xs">
              <p>Lock: ${Number(current.lock_price).toLocaleString()}</p>
              <p>Multiplier: {current.multiplier}x</p>
            </div>
          </div>
        </div>
      )}

      {/* Community Consensus */}
      {consensus && consensus.total > 0 && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h3 className="text-sm font-semibold mb-2">Community Consensus</h3>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-accent-green text-xs font-semibold w-12">{upPct}%</span>
            <div className="flex-1 h-3 bg-bg-primary rounded-full overflow-hidden flex">
              <div className="bg-accent-green h-full transition-all" style={{ width: `${upPct}%` }} />
              <div className="bg-accent-red h-full transition-all" style={{ width: `${downPct}%` }} />
            </div>
            <span className="text-accent-red text-xs font-semibold w-12 text-right">{downPct}%</span>
          </div>
          <p className="text-text-muted text-[10px] text-center">{consensus.total} votes today</p>
        </div>
      )}

      {/* User Stats */}
      {profile && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <h3 className="text-sm font-semibold mb-2">Your Stats</h3>
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">{profile.total_points}</p>
              <p className="text-text-muted text-[10px]">Points</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">{profile.current_streak}{profile.current_streak >= 3 ? '🔥' : ''}</p>
              <p className="text-text-muted text-[10px]">Streak</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">{Math.round(profile.accuracy_pct)}%</p>
              <p className="text-text-muted text-[10px]">Accuracy</p>
            </div>
          </div>
        </div>
      )}

      {/* Leaderboard */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-sm font-semibold mb-2">Leaderboard</h3>
        <div className="flex gap-1 mb-3">
          {PERIOD_TABS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition-colors ${
                period === p ? 'bg-accent-blue text-white' : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
        <div className="space-y-1">
          {leaderboard.length > 0 ? leaderboard.map((entry) => {
            const pts = period === 'weekly' ? entry.weekly_points : period === 'monthly' ? entry.monthly_points : entry.total_points
            return (
              <div key={entry.rank} className="flex items-center justify-between bg-bg-secondary rounded-lg px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-text-muted text-xs font-mono w-6">
                    {entry.rank <= 3 ? ['🥇', '🥈', '🥉'][entry.rank - 1] : `#${entry.rank}`}
                  </span>
                  <span className="text-text-primary text-xs font-medium">{entry.username}</span>
                  {entry.current_streak >= 3 && <span className="text-[10px]">🔥{entry.current_streak}</span>}
                </div>
                <span className="text-accent-blue text-xs font-semibold">{pts} pts</span>
              </div>
            )
          }) : (
            <p className="text-text-muted text-xs text-center py-4">No entries yet</p>
          )}
        </div>
      </div>

      {/* History toggle */}
      <button
        onClick={handleShowHistory}
        className="w-full text-center text-text-muted text-xs py-1.5 hover:text-text-secondary transition-colors"
      >
        {showHistory ? 'Hide History' : 'Show Prediction History'}
      </button>

      {showHistory && (
        <div className="space-y-1">
          {history.length > 0 ? history.map((p) => (
            <div key={p.id} className="bg-bg-card rounded-xl p-3 border border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold ${p.direction === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
                  {p.direction?.toUpperCase()}
                </span>
                <span className="text-text-muted text-[10px]">{p.round_date}</span>
              </div>
              <div className="flex items-center gap-2">
                {p.status === 'resolved' && (
                  <span className={`text-[10px] font-semibold ${p.was_correct ? 'text-accent-green' : 'text-accent-red'}`}>
                    {p.was_correct ? `+${p.points_earned}` : p.points_earned}
                  </span>
                )}
                {p.status === 'pending' && (
                  <span className="text-accent-yellow text-[10px]">Pending</span>
                )}
              </div>
            </div>
          )) : (
            <p className="text-text-muted text-xs text-center py-2">No predictions yet</p>
          )}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  )
}
