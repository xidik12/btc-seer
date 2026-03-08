import { useState, useEffect, useCallback, useRef, memo } from 'react'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'
import ShareButton from '../components/ShareButton'
import CardShareButton from '../components/CardShareButton'
import { gameShareText } from '../utils/shareTemplates'

const PERIOD_TABS = ['all_time', 'weekly', 'monthly']

// ── SVG Icons ───────────────────────────────────────────────────────────────

function CheckCircle() {
  return (
    <svg className="w-4 h-4 text-accent-green" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  )
}

function XCircle() {
  return (
    <svg className="w-4 h-4 text-accent-red" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  )
}

// ── Countdown Timer ─────────────────────────────────────────────────────────

function CountdownTimer({ t }) {
  const [timeLeft, setTimeLeft] = useState('')

  useEffect(() => {
    const calc = () => {
      const now = new Date()
      const tomorrow = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1))
      const diff = Math.max(0, tomorrow - now)
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`)
    }
    calc()
    const iv = setInterval(calc, 1000)
    return () => clearInterval(iv)
  }, [])

  return (
    <div className="flex items-center gap-1.5 text-text-muted text-[10px]">
      <span>{t('game.timeLeft')}</span>
      <span className="font-mono font-semibold text-text-secondary">{timeLeft}</span>
    </div>
  )
}

// ── Loading Skeleton ────────────────────────────────────────────────────────

function GameSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20 animate-pulse">
      {/* Price card */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 text-center">
        <div className="h-3 w-24 bg-bg-hover rounded mx-auto mb-2" />
        <div className="h-7 w-36 bg-bg-hover rounded mx-auto" />
      </div>
      {/* Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <div className="h-16 bg-bg-hover rounded-2xl" />
        <div className="h-16 bg-bg-hover rounded-2xl" />
      </div>
      {/* Stats */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="h-3 w-20 bg-bg-hover rounded mb-3" />
        <div className="grid grid-cols-3 gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-bg-secondary rounded-xl p-2 text-center">
              <div className="h-5 w-8 bg-bg-hover rounded mx-auto mb-1" />
              <div className="h-2.5 w-12 bg-bg-hover rounded mx-auto" />
            </div>
          ))}
        </div>
      </div>
      {/* Leaderboard */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="h-3 w-24 bg-bg-hover rounded mb-3" />
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-bg-hover rounded-lg mb-1" />
        ))}
      </div>
    </div>
  )
}

// ── Streak Display ──────────────────────────────────────────────────────────

function StreakDisplay({ streak }) {
  if (!streak) return <span>0</span>

  const multiplier = streak >= 10 ? 5 : streak >= 5 ? 3 : streak >= 3 ? 2 : 1
  const fireSize = streak >= 10 ? 'text-base' : streak >= 5 ? 'text-sm' : streak >= 3 ? 'text-xs' : ''

  return (
    <span className="flex items-center justify-center gap-0.5">
      <span>{streak}</span>
      {streak >= 3 && (
        <span className={`streak-fire ${fireSize}`}>🔥</span>
      )}
      {multiplier > 1 && (
        <span className="text-[9px] text-accent-yellow font-bold">{multiplier}x</span>
      )}
    </span>
  )
}

// ── Leaderboard Row ─────────────────────────────────────────────────────────

const LeaderboardRow = memo(function LeaderboardRow({ entry, period, isCurrentUser, t }) {
  const pts = period === 'weekly' ? entry.weekly_points : period === 'monthly' ? entry.monthly_points : entry.total_points
  const accuracy = entry.accuracy_pct != null ? Math.round(entry.accuracy_pct) : null

  return (
    <div className={`flex items-center justify-between bg-bg-secondary rounded-lg px-3 py-2 ${
      isCurrentUser ? 'border border-accent-blue/40' : ''
    }`}>
      <div className="flex items-center gap-2">
        <span className="text-text-muted text-xs font-mono w-6">
          {entry.rank <= 3 ? ['🥇', '🥈', '🥉'][entry.rank - 1] : `#${entry.rank}`}
        </span>
        <span className={`text-xs font-medium ${isCurrentUser ? 'text-accent-blue' : 'text-text-primary'}`}>
          {entry.username}
        </span>
        {entry.current_streak >= 3 && <span className="text-[10px]">🔥{entry.current_streak}</span>}
      </div>
      <div className="flex items-center gap-2">
        {accuracy != null && (
          <span className="text-[10px] text-text-muted">{accuracy}%</span>
        )}
        <span className="text-accent-blue text-xs font-semibold">{pts} {t('game.pts')}</span>
      </div>
    </div>
  )
})

// ── History Row ─────────────────────────────────────────────────────────────

const HistoryRow = memo(function HistoryRow({ p, t }) {
  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={`text-xs font-bold ${p.direction === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
          {p.direction === 'up' ? '↑' : '↓'} {t(`game.${p.direction}`)}
        </span>
        <span className="text-text-muted text-[10px]">{p.round_date}</span>
      </div>
      <div className="flex items-center gap-2">
        {p.lock_price != null && (
          <span className="text-text-muted text-[9px] font-mono">
            ${Number(p.lock_price).toLocaleString()}
            {p.resolve_price != null && ` → $${Number(p.resolve_price).toLocaleString()}`}
          </span>
        )}
        {p.multiplier > 1 && (
          <span className="text-[9px] text-accent-yellow font-bold">{p.multiplier}x</span>
        )}
        {p.status === 'resolved' && (
          p.was_correct ? <CheckCircle /> : <XCircle />
        )}
        {p.status === 'resolved' && (
          <span className={`text-[10px] font-semibold ${p.was_correct ? 'text-accent-green' : 'text-accent-red'}`}>
            {p.was_correct ? `+${p.points_earned}` : p.points_earned}
          </span>
        )}
        {p.status === 'pending' && (
          <span className="text-accent-yellow text-[10px]">{t('game.pending')}</span>
        )}
      </div>
    </div>
  )
})

// ── Main Component ──────────────────────────────────────────────────────────

export default function PredictionGame() {
  const { t } = useTranslation('common')
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
  const [locked, setLocked] = useState(false)
  const predictionRef = useRef(null)
  const consensusRef = useRef(null)
  const statsRef = useRef(null)
  const leaderboardRef = useRef(null)

  const initData = tg?.initData

  const periodKeys = { all_time: 'game.allTime', weekly: 'game.weekly', monthly: 'game.monthly' }

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
      // Haptic feedback
      try { tg?.HapticFeedback?.impactOccurred('medium') } catch {}
      // Show locked state briefly
      setLocked(true)
      setTimeout(() => setLocked(false), 1500)
      fetchData()
    } catch (err) {
      const msg = err.message || 'Failed'
      if (tg?.showAlert) { tg.showAlert(msg) } else { console.error(msg) }
    } finally {
      setPredicting(false)
    }
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

  // Determine if user is in leaderboard
  const userId = status?.user_id || tg?.initDataUnsafe?.user?.id
  const userInLeaderboard = leaderboard.some((e) => e.user_id === userId || e.telegram_id === userId)
  const userRank = status?.rank || profile?.rank

  if (loading && !status && !leaderboard.length) {
    return <GameSkeleton />
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">{t('game.title')}</h1>
        <CountdownTimer t={t} />
      </div>

      {/* Locked confirmation */}
      {locked && (
        <div className="bg-accent-green/10 border border-accent-green/30 rounded-2xl p-4 text-center slide-up">
          <CheckCircle />
          <p className="text-accent-green font-bold text-sm mt-1">{t('game.locked')}</p>
        </div>
      )}

      {/* Current BTC Price */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 text-center">
        <p className="text-text-muted text-xs mb-1">{t('game.currentPrice')}</p>
        <p className="text-text-primary font-bold text-2xl">
          ${currentPrice ? Number(currentPrice).toLocaleString() : '—'}
        </p>
      </div>

      {/* UP / DOWN Buttons */}
      {!hasPredicted ? (
        <div className="space-y-2">
          <p className="text-text-muted text-xs text-center">{t('game.question')}</p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => handlePredict('up')}
              disabled={predicting || !initData}
              className="py-6 rounded-2xl bg-accent-green/10 border-2 border-accent-green/30 text-accent-green font-bold text-xl active:scale-95 transition-all disabled:opacity-50 hover:bg-accent-green/20"
            >
              ↑ {t('game.up')}
            </button>
            <button
              onClick={() => handlePredict('down')}
              disabled={predicting || !initData}
              className="py-6 rounded-2xl bg-accent-red/10 border-2 border-accent-red/30 text-accent-red font-bold text-xl active:scale-95 transition-all disabled:opacity-50 hover:bg-accent-red/20"
            >
              ↓ {t('game.down')}
            </button>
          </div>
        </div>
      ) : (
        <div ref={predictionRef} className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">{t('game.yourPrediction')}</h3>
            <div className="flex items-center gap-2">
            <CardShareButton cardRef={predictionRef} label="Prediction" filename="prediction.png" />
            <ShareButton
              compact
              text={gameShareText(current, profile, refCode)}
            />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-2xl font-bold ${current.direction === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
              {current.direction === 'up' ? `↑ ${t('game.up')}` : `↓ ${t('game.down')}`}
            </span>
            <div className="text-text-muted text-xs">
              <p>{t('game.lockPrice')}: ${Number(current.lock_price).toLocaleString()}</p>
              <p>{t('game.multiplier')}: {current.multiplier}x</p>
            </div>
          </div>
          <CountdownTimer t={t} />
        </div>
      )}

      {/* Share on win */}
      {current?.was_correct && (
        <div className="bg-accent-green/10 border border-accent-green/30 rounded-2xl p-4 text-center">
          <p className="text-accent-green text-sm font-semibold mb-2">{t('game.shareWin')}</p>
          <ShareButton text={gameShareText(current, profile, refCode)} />
        </div>
      )}

      {/* Community Consensus */}
      {consensus && consensus.total > 0 && (
        <div ref={consensusRef} className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between mb-2"><h3 className="text-sm font-semibold">{t('game.consensus')}</h3><CardShareButton cardRef={consensusRef} label="Community Consensus" filename="consensus.png" /></div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-accent-green text-xs font-semibold w-12">{upPct}%</span>
            <div className="flex-1 h-3 bg-bg-primary rounded-full overflow-hidden flex">
              <div className="bg-accent-green h-full transition-all" style={{ width: `${upPct}%` }} />
              <div className="bg-accent-red h-full transition-all" style={{ width: `${downPct}%` }} />
            </div>
            <span className="text-accent-red text-xs font-semibold w-12 text-right">{downPct}%</span>
          </div>
          <p className="text-text-muted text-[10px] text-center">{t('game.votesToday', { count: consensus.total })}</p>
        </div>
      )}

      {/* User Stats */}
      {profile && (
        <div ref={statsRef} className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between mb-2"><h3 className="text-sm font-semibold">{t('game.yourStats')}</h3><CardShareButton cardRef={statsRef} label="My Stats" filename="game-stats.png" /></div>
          <div className="grid grid-cols-3 gap-2 mb-2">
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">{profile.total_points}</p>
              <p className="text-text-muted text-[10px]">{t('game.points')}</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">
                <StreakDisplay streak={profile.current_streak} />
              </p>
              <p className="text-text-muted text-[10px]">{t('game.streak')}</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-lg">{Math.round(profile.accuracy_pct)}%</p>
              <p className="text-text-muted text-[10px]">{t('game.accuracy')}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-sm">{profile.best_streak || 0}</p>
              <p className="text-text-muted text-[10px]">{t('game.bestStreak')}</p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2 text-center">
              <p className="text-text-primary font-bold text-sm">
                {profile.correct_predictions || 0}/{profile.total_predictions || 0}
              </p>
              <p className="text-text-muted text-[10px]">{t('game.correctPredictions')}</p>
            </div>
          </div>
        </div>
      )}

      {/* Leaderboard */}
      <div ref={leaderboardRef} className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between mb-2"><h3 className="text-sm font-semibold">{t('game.leaderboard')}</h3><CardShareButton cardRef={leaderboardRef} label="Leaderboard" filename="leaderboard.png" /></div>
        <div className="flex gap-1 mb-3">
          {PERIOD_TABS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition-colors ${
                period === p ? 'bg-accent-blue text-white' : 'bg-bg-secondary text-text-muted'
              }`}
            >
              {t(periodKeys[p])}
            </button>
          ))}
        </div>
        <div className="space-y-1">
          {leaderboard.length > 0 ? leaderboard.map((entry) => (
            <LeaderboardRow
              key={entry.rank}
              entry={entry}
              period={period}
              isCurrentUser={entry.user_id === userId || entry.telegram_id === userId}
              t={t}
            />
          )) : (
            <p className="text-text-muted text-xs text-center py-4">{t('game.noEntries')}</p>
          )}
        </div>
        {/* User rank if not in top 20 */}
        {!userInLeaderboard && userRank && (
          <p className="text-text-muted text-[10px] text-center mt-2 border-t border-white/5 pt-2">
            {t('game.yourRank', { rank: userRank })}
          </p>
        )}
      </div>

      {/* History toggle */}
      <button
        onClick={handleShowHistory}
        className="w-full text-center text-text-muted text-xs py-1.5 hover:text-text-secondary transition-colors"
      >
        {showHistory ? t('game.hideHistory') : t('game.showHistory')}
      </button>

      {showHistory && (
        <div className="space-y-1">
          {history.length > 0 ? history.map((p) => (
            <HistoryRow key={p.id} p={p} t={t} />
          )) : (
            <p className="text-text-muted text-xs text-center py-2">{t('game.noPredictions')}</p>
          )}
        </div>
      )}
    </div>
  )
}
