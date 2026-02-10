import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  BarChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Brush,
  Cell,
  ScatterChart,
  Scatter,
  ZAxis,
} from 'recharts'
import { api } from '../utils/api'
import { formatPrice, formatDate, formatTime, getDirectionColor, formatPercent } from '../utils/format'

const TIMEFRAMES = ['1h', '4h', '24h']
const DAY_OPTIONS = [7, 14, 30, 90]

// ── Accuracy Ring ──

function AccuracyRing({ label, correct, total, size = 80, strokeWidth = 6 }) {
  const pct = total > 0 ? (correct / total) * 100 : 0
  const r = (size - strokeWidth) / 2
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  const color = pct >= 65 ? '#00d68f' : pct >= 50 ? '#ffb800' : '#ff4d6a'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e1e30" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-text-primary text-base font-bold tabular-nums">{pct.toFixed(0)}%</span>
      </div>
      <div className="mt-1 text-center">
        <div className="text-text-primary text-[11px] font-semibold">{label}</div>
        <div className="text-text-muted text-[9px]">{correct}/{total}</div>
      </div>
    </div>
  )
}

// ── Streak Badge ──

function StreakBadge({ history }) {
  if (!history?.length) return null
  const evaluated = history.filter(p => p.was_correct !== null)
  if (!evaluated.length) return null

  let streak = 0
  const first = evaluated[0].was_correct
  for (const p of evaluated) {
    if (p.was_correct === first) streak++
    else break
  }

  if (streak < 2) return null
  const isWin = first
  const { t } = useTranslation(['market', 'common'])
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
      isWin ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'
    }`}>
      {t('market:history.streakLabel', { type: isWin ? 'W' : 'L', count: streak })}
    </span>
  )
}

// ── Accuracy Over Time Chart ──

function AccuracyTrendChart({ history, timeframe }) {
  const { t } = useTranslation(['market', 'common'])
  const dailyData = useMemo(() => {
    if (!history?.length) return []
    const byDay = {}
    for (const p of history) {
      if (p.was_correct === null) continue
      const day = p.timestamp.slice(0, 10)
      if (!byDay[day]) byDay[day] = { correct: 0, total: 0 }
      byDay[day].total++
      if (p.was_correct) byDay[day].correct++
    }
    return Object.entries(byDay)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, d]) => ({
        date,
        accuracy: +(d.correct / d.total * 100).toFixed(1),
        total: d.total,
        correct: d.correct,
      }))
  }, [history])

  if (dailyData.length < 2) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">
        {timeframe.toUpperCase()} {t('market:history.trend30d').toUpperCase()}
      </h3>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dailyData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4a9eff" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#4a9eff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 6" stroke="#1e1e30" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              tickFormatter={(d) => formatDate(d)}
              axisLine={false} tickLine={false}
              minTickGap={40}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[25, 50, 75, 100]}
              tick={{ fontSize: 9, fill: '#5a5a70' }}
              axisLine={false} tickLine={false}
              tickFormatter={v => `${v}%`}
            />
            <ReferenceLine y={50} stroke="#ff4d6a" strokeDasharray="3 4" strokeWidth={0.5} />
            <ReferenceLine y={65} stroke="#00d68f" strokeDasharray="3 4" strokeWidth={0.5} />
            <Tooltip
              contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              formatter={(v, name) => {
                if (name === 'accuracy') return [`${v}%`, t('market:history.accuracy')]
                return [v, name]
              }}
              labelFormatter={(d) => formatDate(d)}
            />
            <Area type="monotone" dataKey="accuracy" stroke="#4a9eff" strokeWidth={2} fill="url(#accGrad)" dot={false} />
            <Bar dataKey="total" fill="#4a9eff" opacity={0.15} radius={[2, 2, 0, 0]} yAxisId="right" />
            <YAxis yAxisId="right" orientation="right" hide domain={[0, 'auto']} />
            {dailyData.length > 15 && (
              <Brush
                dataKey="date"
                height={20}
                stroke="#4a9eff"
                fill="#0f0f14"
                tickFormatter={(d) => formatDate(d)}
                startIndex={Math.max(0, dailyData.length - 15)}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Confidence vs Accuracy Chart ──

function ConfidenceChart({ history }) {
  const { t } = useTranslation(['market', 'common'])
  const data = useMemo(() => {
    if (!history?.length) return []
    // Group by confidence bucket (5% increments)
    const buckets = {}
    for (const p of history) {
      if (p.was_correct === null || !p.confidence) continue
      const bucket = Math.floor(p.confidence / 5) * 5
      if (!buckets[bucket]) buckets[bucket] = { correct: 0, total: 0 }
      buckets[bucket].total++
      if (p.was_correct) buckets[bucket].correct++
    }
    return Object.entries(buckets)
      .map(([conf, d]) => ({
        confidence: +conf,
        accuracy: +(d.correct / d.total * 100).toFixed(1),
        count: d.total,
      }))
      .sort((a, b) => a.confidence - b.confidence)
  }, [history])

  if (data.length < 3) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-1">{t('market:history.calibration').toUpperCase()}</h3>
      <p className="text-text-muted text-[9px] mb-3">{t('market:history.calibrationDesc')}</p>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 5, right: 5, left: -15, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 6" stroke="#1e1e30" />
            <XAxis
              dataKey="confidence" type="number" name={t('common:confidence')}
              domain={[20, 100]} tick={{ fontSize: 9, fill: '#5a5a70' }}
              axisLine={false} tickLine={false}
              label={{ value: `${t('common:confidence')} %`, position: 'insideBottom', offset: -2, fontSize: 9, fill: '#5a5a70' }}
            />
            <YAxis
              dataKey="accuracy" type="number" name={t('market:history.accuracy')}
              domain={[0, 100]} tick={{ fontSize: 9, fill: '#5a5a70' }}
              axisLine={false} tickLine={false}
              tickFormatter={v => `${v}%`}
            />
            <ZAxis dataKey="count" range={[40, 300]} />
            <ReferenceLine y={50} stroke="#ff4d6a" strokeDasharray="3 3" strokeWidth={0.5} />
            {/* Diagonal reference: ideal = confidence matches accuracy */}
            <ReferenceLine segment={[{ x: 20, y: 20 }, { x: 100, y: 100 }]} stroke="#4a9eff" strokeDasharray="4 4" strokeWidth={0.5} />
            <Tooltip
              contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              formatter={(v, name) => {
                if (name === t('market:history.accuracy')) return [`${v}%`, name]
                if (name === t('common:confidence')) return [`${v}%`, name]
                return [v, name]
              }}
            />
            <Scatter data={data} fill="#4a9eff">
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.accuracy >= 60 ? '#00d68f' : entry.accuracy >= 45 ? '#ffb800' : '#ff4d6a'}
                  opacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Win/Loss Distribution Bar ──

function WinLossBar({ history }) {
  const { t } = useTranslation(['market', 'common'])
  const evaluated = (history || []).filter(p => p.was_correct !== null)
  if (!evaluated.length) return null
  const wins = evaluated.filter(p => p.was_correct).length
  const losses = evaluated.length - wins
  const winPct = (wins / evaluated.length) * 100

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:history.win').toUpperCase()} / {t('market:history.loss').toUpperCase()}</h3>
        <StreakBadge history={history} />
      </div>
      <div className="flex h-3 rounded-full overflow-hidden">
        <div className="bg-accent-green transition-all duration-500" style={{ width: `${winPct}%` }} />
        <div className="bg-accent-red transition-all duration-500" style={{ width: `${100 - winPct}%` }} />
      </div>
      <div className="flex justify-between mt-2 text-[10px]">
        <span className="text-accent-green font-bold">{t('market:history.winsLabel', { count: wins, pct: winPct.toFixed(0) })}</span>
        <span className="text-text-muted">{t('market:history.evaluatedLabel', { count: evaluated.length })}</span>
        <span className="text-accent-red font-bold">{t('market:history.lossesLabel', { count: losses, pct: (100 - winPct).toFixed(0) })}</span>
      </div>
    </div>
  )
}

// ── Direction Breakdown ──

function DirectionBreakdown({ history }) {
  const { t } = useTranslation(['market', 'common'])
  const evaluated = (history || []).filter(p => p.was_correct !== null)
  if (!evaluated.length) return null

  const bulls = evaluated.filter(p => p.direction === 'bullish')
  const bears = evaluated.filter(p => p.direction === 'bearish')

  const bullWins = bulls.filter(p => p.was_correct).length
  const bearWins = bears.filter(p => p.was_correct).length

  const bullAcc = bulls.length > 0 ? (bullWins / bulls.length * 100).toFixed(0) : '--'
  const bearAcc = bears.length > 0 ? (bearWins / bears.length * 100).toFixed(0) : '--'

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="bg-bg-card rounded-xl p-3 border border-white/5">
        <div className="text-[9px] text-text-muted font-medium mb-1">{t('market:history.bullishCalls').toUpperCase()}</div>
        <div className="text-accent-green text-lg font-bold tabular-nums">{bullAcc}%</div>
        <div className="text-[9px] text-text-muted">{t('market:history.correctLabel', { correct: bullWins, total: bulls.length })}</div>
      </div>
      <div className="bg-bg-card rounded-xl p-3 border border-white/5">
        <div className="text-[9px] text-text-muted font-medium mb-1">{t('market:history.bearishCalls').toUpperCase()}</div>
        <div className="text-accent-red text-lg font-bold tabular-nums">{bearAcc}%</div>
        <div className="text-[9px] text-text-muted">{t('market:history.correctLabel', { correct: bearWins, total: bears.length })}</div>
      </div>
    </div>
  )
}

// ── Prediction Row (Expanded) ──

function PredictionRow({ p, tf }) {
  const { t } = useTranslation(['market', 'common'])
  const [expanded, setExpanded] = useState(false)
  const priceDelta = p.actual_price && p.current_price
    ? ((p.actual_price - p.current_price) / p.current_price * 100)
    : null

  return (
    <div
      className="bg-bg-card rounded-xl border border-white/5 slide-up cursor-pointer hover:border-white/10 transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="p-3 flex items-center gap-3">
        {/* Result icon */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
          p.was_correct === true
            ? 'bg-accent-green/20 text-accent-green'
            : p.was_correct === false
            ? 'bg-accent-red/20 text-accent-red'
            : 'bg-white/5 text-text-muted'
        }`}>
          {p.was_correct === true ? '✓' : p.was_correct === false ? '✗' : '⏳'}
        </div>

        {/* Direction + confidence */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${getDirectionColor(p.direction)}`}>
              {p.direction === 'bullish' ? '▲' : p.direction === 'bearish' ? '▼' : '◄►'}{' '}
              {p.direction.charAt(0).toUpperCase() + p.direction.slice(1)}
            </span>
            <span className="text-text-muted text-[10px] tabular-nums">{p.confidence?.toFixed(0)}% {t('market:history.conf')}</span>
          </div>
          <div className="text-[10px] text-text-muted mt-0.5 tabular-nums">
            {formatDate(p.timestamp)} {formatTime(p.timestamp)}
          </div>
        </div>

        {/* Prices */}
        <div className="text-right shrink-0">
          <div className="text-[11px] text-text-primary tabular-nums font-medium">
            {formatPrice(p.current_price)}
          </div>
          {p.actual_price ? (
            <div className={`text-[10px] tabular-nums font-medium ${
              priceDelta >= 0 ? 'text-accent-green' : 'text-accent-red'
            }`}>
              → {formatPrice(p.actual_price)} ({priceDelta >= 0 ? '+' : ''}{priceDelta.toFixed(2)}%)
            </div>
          ) : (
            <div className="text-[10px] text-text-muted">{t('market:history.pending')}</div>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-3 pb-3 pt-0 border-t border-white/5">
          <div className="grid grid-cols-3 gap-2 mt-2 text-[10px]">
            <div>
              <span className="text-text-muted">{t('market:history.timeframe')}</span>
              <div className="text-text-primary font-medium">{tf.toUpperCase()}</div>
            </div>
            <div>
              <span className="text-text-muted">{t('market:history.predicted')}</span>
              <div className="text-text-primary font-medium tabular-nums">
                {p.predicted_price ? formatPrice(p.predicted_price) : '--'}
              </div>
            </div>
            <div>
              <span className="text-text-muted">{t('market:history.actualMove')}</span>
              <div className={`font-medium tabular-nums ${
                priceDelta != null ? (priceDelta >= 0 ? 'text-accent-green' : 'text-accent-red') : 'text-text-muted'
              }`}>
                {priceDelta != null ? `${priceDelta >= 0 ? '+' : ''}${priceDelta.toFixed(3)}%` : '--'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Page ──

export default function History() {
  const { t } = useTranslation(['market', 'common'])
  const [timeframe, setTimeframe] = useState('1h')
  const [days, setDays] = useState(14)
  const [predictions, setPredictions] = useState([])
  const [allTfData, setAllTfData] = useState({})
  const [loading, setLoading] = useState(true)

  // Fetch per-timeframe data for accuracy rings
  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const results = await Promise.all(
        TIMEFRAMES.map(tf => api.getPredictionHistory(tf, days))
      )
      const tfMap = {}
      TIMEFRAMES.forEach((tf, i) => {
        tfMap[tf] = results[i]
      })
      setAllTfData(tfMap)
      setPredictions(tfMap[timeframe]?.history || [])
    } catch {
      setPredictions([])
    }
    setLoading(false)
  }, [days, timeframe])

  useEffect(() => { fetchAll() }, [fetchAll])

  // When timeframe tab changes, use cached data
  useEffect(() => {
    if (allTfData[timeframe]) {
      setPredictions(allTfData[timeframe]?.history || [])
    }
  }, [timeframe, allTfData])

  const currentTfData = allTfData[timeframe]

  return (
    <div className="px-4 pt-4 pb-20 space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">{t('market:history.title')}</h1>
        <select
          value={days}
          onChange={e => setDays(+e.target.value)}
          className="bg-bg-card text-text-primary text-xs rounded-lg px-2 py-1 border border-white/10"
        >
          {DAY_OPTIONS.map(d => (
            <option key={d} value={d}>{d}d</option>
          ))}
        </select>
      </div>

      {/* Per-Timeframe Accuracy Rings */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-4">{t('market:history.byTimeframe').toUpperCase()}</h3>
        <div className="flex justify-around">
          {TIMEFRAMES.map(tf => {
            const d = allTfData[tf]
            const correct = d?.correct || 0
            const total = d?.evaluated || 0
            return (
              <div key={tf} className="relative">
                <AccuracyRing label={tf.toUpperCase()} correct={correct} total={total} />
              </div>
            )
          })}
        </div>
      </div>

      {/* Timeframe Tabs */}
      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5">
        {TIMEFRAMES.map(tf => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              timeframe === tf
                ? 'bg-accent-blue text-white shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tf.toUpperCase()}
            {allTfData[tf]?.accuracy_pct != null && (
              <span className="ml-1 opacity-60">{allTfData[tf].accuracy_pct}%</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-20 bg-bg-card rounded-2xl" />
          <div className="h-[200px] bg-bg-card rounded-2xl" />
          <div className="h-40 bg-bg-card rounded-2xl" />
        </div>
      ) : (
        <>
          {/* Win/Loss Bar */}
          <WinLossBar history={predictions} />

          {/* Direction Breakdown */}
          <DirectionBreakdown history={predictions} />

          {/* Accuracy Trend Chart */}
          <AccuracyTrendChart history={predictions} timeframe={timeframe} />

          {/* Confidence vs Accuracy */}
          <ConfidenceChart history={predictions} />

          {/* Prediction List */}
          <div>
            <h3 className="text-text-secondary text-xs font-semibold mb-2">
              {timeframe.toUpperCase()} {t('market:history.records').toUpperCase()} ({predictions.length})
            </h3>
            {predictions.length === 0 ? (
              <div className="text-center text-text-muted py-10 text-sm">
                {t('common:app.noData')}
              </div>
            ) : (
              <div className="space-y-2">
                {predictions.map(p => (
                  <PredictionRow key={p.id} p={p} tf={timeframe} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
