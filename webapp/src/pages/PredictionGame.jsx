import { useState, useEffect, useCallback, useRef, memo } from 'react'
import { useTranslation } from 'react-i18next'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../utils/api'
import ShareButton from '../components/ShareButton'
import CardShareButton from '../components/CardShareButton'
import { gameShareText } from '../utils/shareTemplates'

const PERIOD_TABS = ['all_time', 'weekly', 'monthly']

// ── SVG Icons ───────────────────────────────────────────────────────────────

function CheckCircle({ size = 'w-4 h-4' }) {
  return (
    <svg className={`${size} text-accent-green`} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  )
}

function XCircle({ size = 'w-4 h-4' }) {
  return (
    <svg className={`${size} text-accent-red`} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  )
}

function ArrowUpIcon() {
  return (
    <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  )
}

function ArrowDownIcon() {
  return (
    <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <polyline points="19 12 12 19 5 12" />
    </svg>
  )
}

function ChevronDown({ open }) {
  return (
    <svg
      className={`w-4 h-4 text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  )
}

// ── Countdown Timer ─────────────────────────────────────────────────────────

function CountdownTimer({ label }) {
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
    <div className="flex items-center gap-2">
      {label && <span className="text-text-muted text-xs">{label}</span>}
      <span className="font-mono font-bold text-accent-blue text-sm tabular-nums">{timeLeft}</span>
    </div>
  )
}

// ── Loading Skeleton ────────────────────────────────────────────────────────

function GameSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20 animate-pulse">
      {/* Hero */}
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <div className="h-4 w-48 bg-bg-hover rounded mx-auto mb-4" />
        <div className="h-10 w-44 bg-bg-hover rounded mx-auto mb-6" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-20 bg-bg-hover rounded-2xl" />
          <div className="h-20 bg-bg-hover rounded-2xl" />
        </div>
        <div className="h-3 w-32 bg-bg-hover rounded mx-auto mt-4" />
      </div>
      {/* Stats */}
      <div className="grid grid-cols-4 gap-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="bg-bg-card rounded-2xl p-3 border border-white/5">
            <div className="h-6 w-8 bg-bg-hover rounded mx-auto mb-1" />
            <div className="h-3 w-12 bg-bg-hover rounded mx-auto" />
          </div>
        ))}
      </div>
      {/* Results */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="h-4 w-32 bg-bg-hover rounded mb-3" />
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 bg-bg-hover rounded-xl mb-2" />
        ))}
      </div>
      {/* Leaderboard */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="h-4 w-24 bg-bg-hover rounded mb-3" />
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="h-10 bg-bg-hover rounded-lg mb-1" />
        ))}
      </div>
    </div>
  )
}

// ── Streak Display ──────────────────────────────────────────────────────────

function StreakDisplay({ streak, showLabel = false }) {
  if (!streak) return <span>0</span>

  const multiplier = streak >= 10 ? 5 : streak >= 5 ? 3 : streak >= 3 ? 2 : 1

  return (
    <span className="flex items-center justify-center gap-0.5">
      <span>{streak}</span>
      {streak >= 3 && (
        <span className="streak-fire text-sm">&#x1F525;</span>
      )}
      {multiplier > 1 && showLabel && (
        <span className="text-xxs text-accent-yellow font-bold ml-0.5">{multiplier}x</span>
      )}
    </span>
  )
}

// ── Leaderboard Row ─────────────────────────────────────────────────────────

const LeaderboardRow = memo(function LeaderboardRow({ entry, period, isCurrentUser, rank }) {
  const pts = period === 'weekly' ? entry.weekly_points : period === 'monthly' ? entry.monthly_points : entry.total_points
  const accuracy = entry.accuracy_pct != null ? Math.round(entry.accuracy_pct) : null
  const streak = entry.current_streak || 0

  const rankDisplay = rank <= 3
    ? ['\u{1F947}', '\u{1F948}', '\u{1F949}'][rank - 1]
    : `#${rank}`

  return (
    <div className={`flex items-center justify-between px-3 py-2.5 rounded-xl transition-colors ${
      isCurrentUser
        ? 'bg-accent-blue/10 border border-accent-blue/30'
        : 'bg-bg-secondary/50 hover:bg-bg-secondary'
    }`}>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono w-7 text-center shrink-0">
          {rankDisplay}
        </span>
        <div>
          <span className={`text-xs font-semibold block ${isCurrentUser ? 'text-accent-blue' : 'text-text-primary'}`}>
            {entry.username}
            {isCurrentUser && <span className="text-xxs text-accent-blue/70 ml-1">(you)</span>}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {streak >= 3 && (
          <span className="text-xxs text-text-muted">&#x1F525;{streak}</span>
        )}
        {accuracy != null && (
          <span className="text-xxs text-text-muted">{accuracy}%</span>
        )}
        <span className="text-accent-blue text-xs font-bold min-w-[40px] text-right">{pts} pts</span>
      </div>
    </div>
  )
})

// ── History / Recent Result Row ─────────────────────────────────────────────

const ResultRow = memo(function ResultRow({ p }) {
  const isUp = p.direction === 'up'
  const isCorrect = p.was_correct
  const isPending = p.status === 'pending'

  return (
    <div className={`rounded-xl p-3 border transition-colors ${
      isPending
        ? 'bg-bg-secondary/50 border-accent-yellow/20'
        : isCorrect
          ? 'bg-accent-green/5 border-accent-green/20'
          : 'bg-accent-red/5 border-accent-red/20'
    }`}>
      <div className="flex items-center justify-between">
        {/* Left: direction + date */}
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
            isUp ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'
          }`}>
            {isUp ? '\u2191' : '\u2193'}
          </div>
          <div>
            <span className={`text-xs font-semibold block ${
              isUp ? 'text-accent-green' : 'text-accent-red'
            }`}>
              {isUp ? 'UP' : 'DOWN'}
            </span>
            <span className="text-xxs text-text-muted">{p.round_date}</span>
          </div>
        </div>

        {/* Center: prices */}
        <div className="text-right">
          {p.lock_price != null && (
            <span className="text-xxs text-text-muted font-mono block">
              ${Number(p.lock_price).toLocaleString()}
              {p.resolve_price != null && (
                <span> {'\u2192'} ${Number(p.resolve_price).toLocaleString()}</span>
              )}
            </span>
          )}
        </div>

        {/* Right: result badge + points */}
        <div className="flex items-center gap-2 ml-2">
          {p.multiplier > 1 && (
            <span className="text-xxs text-accent-yellow font-bold">{p.multiplier}x</span>
          )}
          {isPending ? (
            <span className="text-xxs font-semibold text-accent-yellow bg-accent-yellow/10 px-2 py-0.5 rounded-full">
              Pending
            </span>
          ) : (
            <>
              <span className={`text-xs font-bold ${isCorrect ? 'text-accent-green' : 'text-accent-red'}`}>
                {isCorrect ? `+${p.points_earned}` : p.points_earned}
              </span>
              {isCorrect ? <CheckCircle /> : <XCircle />}
            </>
          )}
        </div>
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
  const [locked, setLocked] = useState(false)
  const [howItWorksOpen, setHowItWorksOpen] = useState(() => {
    try {
      return localStorage.getItem('game_how_it_works_seen') !== 'true'
    } catch {
      return true
    }
  })
  const [refCode, setRefCode] = useState(null)

  const heroRef = useRef(null)
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
        api.getGameHistory(initData, 5).then((r) => setHistory(r?.predictions || [])).catch(() => {}),
      )
    }
    Promise.all(promises).finally(() => setLoading(false))
  }, [initData, period])

  useEffect(() => { fetchData() }, [fetchData])

  // Mark how-it-works as seen when collapsed
  const toggleHowItWorks = () => {
    setHowItWorksOpen((v) => {
      if (v) {
        try { localStorage.setItem('game_how_it_works_seen', 'true') } catch {}
      }
      return !v
    })
  }

  const handlePredict = async (direction) => {
    if (!initData || predicting) return
    setPredicting(true)
    try {
      await api.makeGamePrediction(initData, direction, '24h')
      try { tg?.HapticFeedback?.impactOccurred('medium') } catch {}
      setLocked(true)
      setTimeout(() => setLocked(false), 2000)
      fetchData()
    } catch (err) {
      const msg = err.message || 'Failed'
      if (tg?.showAlert) { tg.showAlert(msg) } else { console.error(msg) }
    } finally {
      setPredicting(false)
    }
  }

  const profile = status?.profile
  const current = status?.current_prediction
  const hasPredicted = !!current
  const upPct = consensus?.up_pct || 50
  const downPct = consensus?.down_pct || 50

  const userId = status?.user_id || tg?.initDataUnsafe?.user?.id
  const userInLeaderboard = leaderboard.some((e) => e.user_id === userId || e.telegram_id === userId)
  const userRank = status?.rank || profile?.rank

  if (loading && !status && !leaderboard.length) {
    return <GameSkeleton />
  }

  return (
    <div className="px-4 pt-4 space-y-4 pb-20 dashboard-stagger">

      {/* ================================================================
          SECTION 1 — Hero: "Will BTC go UP or DOWN?"
          ================================================================ */}
      <div ref={heroRef} className="bg-bg-card rounded-2xl p-5 border border-white/5 text-center relative overflow-hidden">
        {/* Subtle gradient bg accent */}
        <div className="absolute inset-0 bg-gradient-to-b from-accent-blue/5 via-transparent to-transparent pointer-events-none" />

        <h1 className="text-text-secondary text-sm font-semibold mb-1 relative">
          Will BTC go UP or DOWN?
        </h1>

        {/* Current price — large and prominent */}
        <div className="mb-5 relative">
          <p className="text-text-muted text-xxs uppercase tracking-wider mb-1">Current BTC Price</p>
          <p className="text-text-primary font-bold text-4xl gold-glow tabular-nums">
            ${currentPrice ? Number(currentPrice).toLocaleString() : '\u2014'}
          </p>
        </div>

        {/* Locked confirmation overlay */}
        {locked && (
          <div className="absolute inset-0 bg-bg-primary/80 backdrop-blur-sm flex flex-col items-center justify-center z-10 slide-up rounded-2xl">
            <CheckCircle size="w-10 h-10" />
            <p className="text-accent-green font-bold text-lg mt-2">Prediction Locked!</p>
            <p className="text-text-muted text-xs mt-1">Check back tomorrow for results</p>
          </div>
        )}

        {/* UP / DOWN buttons — or current prediction */}
        {!hasPredicted ? (
          <div className="relative">
            <div className="grid grid-cols-2 gap-3 mb-4">
              <button
                onClick={() => handlePredict('up')}
                disabled={predicting || !initData}
                className="group relative py-5 rounded-2xl bg-accent-green/10 border-2 border-accent-green/30 text-accent-green font-bold text-lg active:scale-95 transition-all disabled:opacity-40 hover:bg-accent-green/20 hover:border-accent-green/50 flex flex-col items-center gap-1"
              >
                <ArrowUpIcon />
                <span>UP</span>
              </button>
              <button
                onClick={() => handlePredict('down')}
                disabled={predicting || !initData}
                className="group relative py-5 rounded-2xl bg-accent-red/10 border-2 border-accent-red/30 text-accent-red font-bold text-lg active:scale-95 transition-all disabled:opacity-40 hover:bg-accent-red/20 hover:border-accent-red/50 flex flex-col items-center gap-1"
              >
                <ArrowDownIcon />
                <span>DOWN</span>
              </button>
            </div>
            {!initData && (
              <p className="text-text-muted text-xxs">Open in Telegram to play</p>
            )}
          </div>
        ) : (
          <div className="relative">
            {/* Active prediction display */}
            <div className={`rounded-2xl p-4 mb-3 border-2 ${
              current.direction === 'up'
                ? 'bg-accent-green/10 border-accent-green/30'
                : 'bg-accent-red/10 border-accent-red/30'
            }`}>
              <div className="flex items-center justify-center gap-3 mb-2">
                <span className={`text-3xl font-bold ${
                  current.direction === 'up' ? 'text-accent-green' : 'text-accent-red'
                }`}>
                  {current.direction === 'up' ? '\u2191 UP' : '\u2193 DOWN'}
                </span>
              </div>
              <p className="text-text-muted text-xs">
                Your prediction
                {current.lock_price && (
                  <span> &middot; locked at <span className="text-text-secondary font-mono">${Number(current.lock_price).toLocaleString()}</span></span>
                )}
              </p>
              {current.multiplier > 1 && (
                <span className="inline-block mt-1 text-xxs text-accent-yellow font-bold bg-accent-yellow/10 px-2 py-0.5 rounded-full">
                  {current.multiplier}x streak bonus
                </span>
              )}
            </div>

            {/* Countdown to evaluation */}
            <div className="flex items-center justify-center gap-2 mb-2">
              <span className="text-text-muted text-xs">Evaluates in</span>
              <CountdownTimer />
            </div>

            {/* Share buttons */}
            <div className="flex items-center justify-center gap-2">
              <CardShareButton cardRef={heroRef} label="Prediction" filename="prediction.png" />
              <ShareButton compact text={gameShareText(current, profile, refCode)} />
            </div>
          </div>
        )}

        {/* Community consensus bar */}
        {consensus && consensus.total > 0 && (
          <div className="mt-4 pt-4 border-t border-white/5 relative">
            <p className="text-text-muted text-xxs mb-2">
              {upPct >= downPct
                ? `${upPct}% of players think UP`
                : `${downPct}% of players think DOWN`}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-accent-green text-xxs font-bold w-10">{upPct}%</span>
              <div className="flex-1 h-2.5 bg-bg-primary rounded-full overflow-hidden flex">
                <div
                  className="bg-accent-green h-full rounded-l-full transition-all duration-500"
                  style={{ width: `${upPct}%` }}
                />
                <div
                  className="bg-accent-red h-full rounded-r-full transition-all duration-500"
                  style={{ width: `${downPct}%` }}
                />
              </div>
              <span className="text-accent-red text-xxs font-bold w-10 text-right">{downPct}%</span>
            </div>
            <p className="text-text-muted text-xxs mt-1">{consensus.total} predictions today</p>
          </div>
        )}

        {/* Share on win */}
        {current?.was_correct && (
          <div className="mt-3 pt-3 border-t border-accent-green/20">
            <p className="text-accent-green text-xs font-semibold mb-2">&#x1F389; You got it right! Share your win</p>
            <ShareButton text={gameShareText(current, profile, refCode)} />
          </div>
        )}
      </div>

      {/* ================================================================
          SECTION 2 — How It Works (collapsible)
          ================================================================ */}
      <div className="bg-bg-card rounded-2xl border border-white/5 overflow-hidden">
        <button
          onClick={toggleHowItWorks}
          className="w-full flex items-center justify-between p-4 text-left"
        >
          <h2 className="text-sm font-semibold text-text-primary">How It Works</h2>
          <ChevronDown open={howItWorksOpen} />
        </button>

        {howItWorksOpen && (
          <div className="px-4 pb-4 space-y-4 slide-up">
            {/* 3 steps */}
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-blue/15 flex items-center justify-center text-accent-blue font-bold text-sm shrink-0">1</div>
                <div>
                  <p className="text-text-primary text-xs font-semibold">Make your prediction</p>
                  <p className="text-text-muted text-xxs">Predict if BTC will be higher or lower in 24 hours</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-purple/15 flex items-center justify-center text-accent-purple font-bold text-sm shrink-0">2</div>
                <div>
                  <p className="text-text-primary text-xs font-semibold">Wait for the result</p>
                  <p className="text-text-muted text-xxs">Predictions are evaluated daily at midnight UTC</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-yellow/15 flex items-center justify-center text-accent-yellow font-bold text-sm shrink-0">3</div>
                <div>
                  <p className="text-text-primary text-xs font-semibold">Earn points &amp; climb the leaderboard</p>
                  <p className="text-text-muted text-xxs">Build streaks for bonus multipliers</p>
                </div>
              </div>
            </div>

            {/* Scoring */}
            <div className="bg-bg-secondary/60 rounded-xl p-3">
              <p className="text-text-secondary text-xs font-semibold mb-2">Scoring</p>
              <div className="grid grid-cols-2 gap-2 text-xxs">
                <div className="flex items-center gap-1.5">
                  <span className="text-accent-green font-bold">+10</span>
                  <span className="text-text-muted">Correct prediction</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-accent-red font-bold">-5</span>
                  <span className="text-text-muted">Wrong prediction</span>
                </div>
              </div>
            </div>

            {/* Streak multipliers */}
            <div className="bg-bg-secondary/60 rounded-xl p-3">
              <p className="text-text-secondary text-xs font-semibold mb-2">Streak Multipliers (wins only)</p>
              <div className="flex items-center justify-between text-xxs">
                <div className="text-center">
                  <p className="text-accent-yellow font-bold">2x</p>
                  <p className="text-text-muted">3+ streak</p>
                </div>
                <div className="text-text-muted">{'\u2192'}</div>
                <div className="text-center">
                  <p className="text-accent-yellow font-bold">3x</p>
                  <p className="text-text-muted">5+ streak</p>
                </div>
                <div className="text-text-muted">{'\u2192'}</div>
                <div className="text-center">
                  <p className="text-accent-yellow font-bold">5x</p>
                  <p className="text-text-muted">10+ streak</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ================================================================
          SECTION 3 — Your Stats (horizontal cards)
          ================================================================ */}
      {profile && (
        <div ref={statsRef}>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-text-primary">Your Stats</h2>
            <CardShareButton cardRef={statsRef} label="My Stats" filename="game-stats.png" />
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-bg-card rounded-2xl p-3 border border-white/5 text-center">
              <p className="text-text-primary font-bold text-lg leading-tight">
                <StreakDisplay streak={profile.current_streak} showLabel />
              </p>
              <p className="text-text-muted text-xxs mt-0.5">Streak</p>
            </div>
            <div className="bg-bg-card rounded-2xl p-3 border border-white/5 text-center">
              <p className="text-text-primary font-bold text-lg leading-tight">{profile.total_points}</p>
              <p className="text-text-muted text-xxs mt-0.5">Points</p>
            </div>
            <div className="bg-bg-card rounded-2xl p-3 border border-white/5 text-center">
              <p className="text-text-primary font-bold text-lg leading-tight">{Math.round(profile.accuracy_pct || 0)}%</p>
              <p className="text-text-muted text-xxs mt-0.5">Accuracy</p>
            </div>
            <div className="bg-bg-card rounded-2xl p-3 border border-white/5 text-center">
              <p className="text-text-primary font-bold text-lg leading-tight">{profile.best_streak || 0}</p>
              <p className="text-text-muted text-xxs mt-0.5">Best</p>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================
          SECTION 4 — Recent Results (last 5)
          ================================================================ */}
      {history.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-text-primary mb-2">Recent Results</h2>
          <div className="space-y-2">
            {history.slice(0, 5).map((p) => (
              <ResultRow key={p.id} p={p} />
            ))}
          </div>
        </div>
      )}

      {/* ================================================================
          SECTION 5 — Leaderboard (top 10)
          ================================================================ */}
      <div ref={leaderboardRef} className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-primary">Leaderboard</h2>
          <CardShareButton cardRef={leaderboardRef} label="Leaderboard" filename="leaderboard.png" />
        </div>

        {/* Period tabs */}
        <div className="flex gap-1 mb-3 bg-bg-secondary/50 rounded-xl p-1">
          {PERIOD_TABS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`flex-1 py-1.5 rounded-lg text-xxs font-semibold transition-all ${
                period === p
                  ? 'bg-accent-blue text-white shadow-sm'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {t(periodKeys[p])}
            </button>
          ))}
        </div>

        {/* Leaderboard rows */}
        <div className="space-y-1.5">
          {leaderboard.length > 0 ? leaderboard.slice(0, 10).map((entry) => (
            <LeaderboardRow
              key={entry.rank}
              entry={entry}
              period={period}
              rank={entry.rank}
              isCurrentUser={entry.user_id === userId || entry.telegram_id === userId}
            />
          )) : (
            <p className="text-text-muted text-xs text-center py-6">No entries yet. Be the first to predict!</p>
          )}
        </div>

        {/* User rank if not in top 10 */}
        {!userInLeaderboard && userRank && (
          <div className="mt-3 pt-3 border-t border-white/5 text-center">
            <p className="text-text-muted text-xxs">
              Your rank: <span className="text-accent-blue font-semibold">#{userRank}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
