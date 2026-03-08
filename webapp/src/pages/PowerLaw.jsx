import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatPrice } from '../utils/format'
import { useChartZoom } from '../hooks/useChartZoom'
import CardShareButton from '../components/CardShareButton'
import SubTabBar from '../components/SubTabBar'
import DataSourceFooter from '../components/DataSourceFooter'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

// Lazy load sub-components
const PLDashboard = lazy(() => import('../components/powerlaw/PLDashboard'))
const PLCurve = lazy(() => import('../components/powerlaw/PLCurve'))
const PLGold = lazy(() => import('../components/powerlaw/PLGold'))
const PLM2 = lazy(() => import('../components/powerlaw/PLM2'))
const PLSPX = lazy(() => import('../components/powerlaw/PLSPX'))
const PLAssets = lazy(() => import('../components/powerlaw/PLAssets'))
const PLCalculator = lazy(() => import('../components/powerlaw/PLCalculator'))
const PLMilestones = lazy(() => import('../components/powerlaw/PLMilestones'))

const POLL_INTERVAL = 60_000

const VALUATION_COLORS = {
  'Extremely Undervalued': { text: 'text-accent-green', bg: 'bg-accent-green/15', border: 'border-accent-green/30' },
  'Undervalued': { text: 'text-accent-green', bg: 'bg-accent-green/10', border: 'border-accent-green/20' },
  'Below Fair Value': { text: 'text-accent-green', bg: 'bg-accent-green/8', border: 'border-accent-green/15' },
  'Above Fair Value': { text: 'text-accent-yellow', bg: 'bg-accent-yellow/8', border: 'border-accent-yellow/15' },
  'Overvalued': { text: 'text-accent-red', bg: 'bg-accent-red/10', border: 'border-accent-red/20' },
}

const PL_TABS = ['main', 'curve', 'gold', 'm2', 'spx', 'assets', 'calculator', 'milestones']

function TabBar({ activeTab, setActiveTab, t }) {
  return (
    <div className="flex overflow-x-auto gap-1 pb-1 -mx-1 px-1 scrollbar-hide">
      {PL_TABS.map((tab) => (
        <button
          key={tab}
          onClick={() => setActiveTab(tab)}
          className={`whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            activeTab === tab
              ? 'bg-accent-blue text-white'
              : 'bg-bg-card text-text-muted hover:text-text-secondary border border-white/5'
          }`}
        >
          {t(`market:powerLaw.tabs.${tab}`)}
        </button>
      ))}
    </div>
  )
}

function LoadingPlaceholder() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-24 bg-bg-card rounded-2xl" />
      <div className="h-64 bg-bg-card rounded-2xl" />
      <div className="h-16 bg-bg-card rounded-2xl" />
    </div>
  )
}

function CorridorGauge({ position, bands, currentPrice, t }) {
  const pct = Math.max(0, Math.min(100, position * 100))

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('market:powerLaw.corridorPosition').toUpperCase()}</h3>
      <div className="relative h-4 bg-gradient-to-r from-accent-green/30 via-accent-yellow/30 to-accent-red/30 rounded-full">
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg border-2 border-accent-blue transition-all duration-700"
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-text-muted">
        <span>{t('market:powerLaw.support')} {bands?.support ? `$${bands.support.toLocaleString()}` : ''}</span>
        <span>{t('market:powerLaw.fairValue')} {bands?.fair ? `$${bands.fair.toLocaleString()}` : ''}</span>
        <span>{t('market:powerLaw.resistance')} {bands?.top_resistance ? `$${bands.top_resistance.toLocaleString()}` : ''}</span>
      </div>
    </div>
  )
}

function StatsGrid({ data, t }) {
  const stats = [
    { labelKey: 'daysGenesis', value: data?.days_since_genesis?.toLocaleString() },
    { labelKey: 'fairValue', value: data?.fair_value ? `$${data.fair_value.toLocaleString()}` : '--' },
    { labelKey: 'deviation', value: data?.deviation_pct ? `${data.deviation_pct > 0 ? '+' : ''}${data.deviation_pct.toFixed(1)}%` : '--' },
    { labelKey: 'toSupport', value: data?.distance_to_support_pct ? `${data.distance_to_support_pct.toFixed(1)}%` : '--' },
    { labelKey: 'toResistance', value: data?.distance_to_resistance_pct ? `${data.distance_to_resistance_pct.toFixed(1)}%` : '--' },
    { labelKey: 'corridorPos', value: data?.corridor_position ? `${(data.corridor_position * 100).toFixed(0)}%` : '--' },
  ]

  const labelMap = {
    daysGenesis: t('market:powerLaw.daysGenesis'),
    fairValue: t('market:powerLaw.fairValue'),
    deviation: t('market:powerLaw.deviation'),
    toSupport: t('market:powerLaw.support'),
    toResistance: t('market:powerLaw.resistance'),
    corridorPos: t('market:powerLaw.corridorPosition'),
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {stats.map((s) => (
        <div key={s.labelKey} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] font-medium mb-1">{labelMap[s.labelKey]}</div>
          <div className="text-text-primary text-sm font-bold tabular-nums">{s.value || '--'}</div>
        </div>
      ))}
    </div>
  )
}

function PowerLawChart({ historicalData, t }) {
  if (!historicalData?.points?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5 h-64 flex items-center justify-center">
        <span className="text-text-muted text-sm">{t('common:chart.loadingChart')}</span>
      </div>
    )
  }

  const chartData = historicalData.points
    .filter((_, i) => i % 7 === 0)
    .map((p) => ({
      date: p.date,
      fairValue: p.fair_value,
      support: p.support,
      topResistance: p.top_resistance,
      actualPrice: p.actual_price,
    }))

  const { data: visibleData, bindGestures, isZoomed, resetZoom } = useChartZoom(chartData)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:powerLaw.title').toUpperCase()}</h3>
        {isZoomed && (
          <button onClick={resetZoom} className="text-[10px] text-accent-blue">{t('common:btn.resetZoom')}</button>
        )}
      </div>
      <div {...bindGestures}>
      <ResponsiveContainer width="100%" height={310}>
        <ComposedChart data={visibleData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => v?.slice(5, 10)}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            domain={['auto', 'auto']}
            scale="log"
          />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v, name) => [v ? `$${v.toLocaleString()}` : '--', name]}
          />
          <Area
            dataKey="topResistance"
            stroke="none"
            fill="rgba(255,77,106,0.08)"
            name={t('market:powerLaw.resistance')}
          />
          <Area
            dataKey="support"
            stroke="none"
            fill="rgba(0,200,83,0.08)"
            name={t('market:powerLaw.support')}
          />
          <Line
            dataKey="fairValue"
            stroke="#4a9eff"
            strokeWidth={2}
            dot={false}
            name={t('market:powerLaw.fairValue')}
          />
          <Line
            dataKey="support"
            stroke="#00c853"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name={t('market:powerLaw.support')}
          />
          <Line
            dataKey="topResistance"
            stroke="#ff4d6a"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name={t('market:powerLaw.resistance')}
          />
          <Line
            dataKey="actualPrice"
            stroke="#ffc107"
            strokeWidth={1.5}
            dot={false}
            name={t('common:price.btcPrice')}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-[9px] text-center mt-2">{t('common:chart.pinchZoom')}</p>
    </div>
  )
}

const SIGNAL_STYLES = {
  high_accumulation: { label: 'High Accumulation', color: 'text-accent-green', dot: 'bg-accent-green' },
  moderate: { label: 'Moderate', color: 'text-accent-yellow', dot: 'bg-accent-yellow' },
  distribution: { label: 'Distribution', color: 'text-accent-red', dot: 'bg-accent-red' },
}

const BUCKET_COLORS = [
  'bg-slate-500/20 text-slate-400',
  'bg-zinc-500/20 text-zinc-400',
  'bg-blue-500/20 text-blue-400',
  'bg-cyan-500/20 text-cyan-400',
  'bg-teal-500/20 text-teal-400',
  'bg-green-500/20 text-green-400',
  'bg-lime-500/20 text-lime-400',
  'bg-yellow-500/20 text-yellow-400',
  'bg-orange-500/20 text-orange-400',
  'bg-red-500/20 text-red-400',
  'bg-purple-500/20 text-purple-400',
]

function AdoptionOverlay({ data, t }) {
  if (!data) return null
  const signal = SIGNAL_STYLES[data.whale_signal] || SIGNAL_STYLES.moderate
  const maxCount = Math.max(...(data.buckets || []).map(b => b.count || 0), 1)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-xs font-semibold">{t('market:powerLaw.adoption.title').toUpperCase()}</h3>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${signal.dot} animate-pulse`} />
          <span className={`text-[10px] font-semibold ${signal.color}`}>
            {t(`market:powerLaw.adoption.signal.${data.whale_signal}`, signal.label)}
          </span>
        </div>
      </div>

      {/* Summary row */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('market:powerLaw.adoption.totalAddresses')}</div>
          <div className="text-text-primary text-sm font-bold tabular-nums">{data.total_addresses?.toLocaleString()}</div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('market:powerLaw.adoption.whaleCount')}</div>
          <div className="text-text-primary text-sm font-bold tabular-nums">{data.whale_count?.toLocaleString()}</div>
        </div>
        <div className="text-center">
          <div className="text-text-muted text-[9px]">{t('market:powerLaw.adoption.shrimpDominance')}</div>
          <div className="text-text-primary text-sm font-bold tabular-nums">{data.shrimp_dominance_pct}%</div>
        </div>
      </div>

      {/* Full bucket breakdown */}
      {data.buckets?.length > 0 && (
        <div className="space-y-1.5">
          {data.buckets.map((b, i) => (
            <div key={b.label} className="flex items-center gap-2">
              <span className={`text-[9px] font-semibold w-[70px] text-right shrink-0 ${BUCKET_COLORS[i]?.split(' ')[1] || 'text-text-muted'}`}>
                {b.label}
              </span>
              <span className="text-text-muted text-[9px] w-[65px] shrink-0">{b.btc_range} BTC</span>
              <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${BUCKET_COLORS[i]?.split(' ')[0] || 'bg-accent-blue/20'}`}
                  style={{ width: `${Math.max(1, Math.log10(b.count + 1) / Math.log10(maxCount + 1) * 100)}%` }}
                />
              </div>
              <span className="text-text-primary text-[10px] font-bold tabular-nums w-[72px] text-right shrink-0">
                {b.count?.toLocaleString()}
              </span>
              <span className="text-text-muted text-[9px] w-[38px] text-right shrink-0">{b.pct}%</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-text-muted text-[9px] mt-3">
        {t('market:powerLaw.adoption.explain')}
      </p>
    </div>
  )
}

function MainTab({ current, historical, dashboard, t }) {
  const valStyle = VALUATION_COLORS[current?.valuation] || VALUATION_COLORS['Above Fair Value']
  const valuationRef = useRef(null)

  return (
    <>
      {/* Valuation Card */}
      {current && (
        <div ref={valuationRef} className="bg-bg-card rounded-2xl p-4 border border-white/5 slide-up">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-text-muted text-[10px] font-medium">{t('market:powerLaw.currentPrice').toUpperCase()}</div>
              <div className="text-text-primary text-xl font-bold tabular-nums">
                {current.current_price ? formatPrice(current.current_price) : '--'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-text-muted text-[10px] font-medium">{t('market:powerLaw.fairValue').toUpperCase()}</div>
              <div className="text-accent-blue text-xl font-bold tabular-nums">
                {current.fair_value ? `$${current.fair_value.toLocaleString()}` : '--'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className={`text-xs font-bold px-2 py-1 rounded border ${valStyle.bg} ${valStyle.border} ${valStyle.text}`}>
              {t(`market:powerLaw.valuation.${current.valuation}`, current.valuation)}
            </span>
            <div className="flex items-center gap-2">
              <CardShareButton cardRef={valuationRef} label="Power Law" filename="powerlaw.png" />
              <span className={`text-sm font-bold tabular-nums ${current.deviation_pct > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                {current.deviation_pct > 0 ? '+' : ''}{current.deviation_pct?.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <PowerLawChart historicalData={historical} t={t} />

      {/* Corridor Gauge */}
      {current && (
        <CorridorGauge
          position={current.corridor_position}
          bands={current.corridor}
          currentPrice={current.current_price}
          t={t}
        />
      )}

      {/* Stats Grid */}
      {current && <StatsGrid data={current} t={t} />}

      {/* On-Chain Adoption Overlay */}
      <AdoptionOverlay data={dashboard?.address_distribution} t={t} />

      {/* Educational Section */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('market:powerLaw.title').toUpperCase()}</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p>{t('market:powerLaw.description')}</p>
          <p>{t('market:powerLaw.howItWorks')}</p>
          <p>{t('market:powerLaw.limitations')}</p>
        </div>
      </div>
    </>
  )
}

export default function PowerLaw() {
  const { t } = useTranslation(['market', 'common'])
  const [activeTab, setActiveTab] = useState('main')
  const [current, setCurrent] = useState(null)
  const [historical, setHistorical] = useState(null)
  const [tabData, setTabData] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const MARKET_TABS = [
    { path: '/liquidations', label: t('common:link.liquidations') },
    { path: '/powerlaw', label: t('common:link.powerLaw') },
    { path: '/elliott-wave', label: t('common:link.elliottWave') },
    { path: '/events', label: t('common:link.events') },
    { path: '/tools', label: t('common:link.tools') },
    { path: '/learn', label: t('common:link.learn') },
  ]

  // Fetch main tab data (dashboard + legacy current/historical)
  const fetchMainData = useCallback(async () => {
    try {
      setError(null)
      const [curr, hist, dashboard] = await Promise.all([
        api.getPowerLawCurrent(),
        api.getPowerLawHistorical(365),
        api.getPowerLawDashboard(),
      ])
      setCurrent(curr)
      setHistorical(hist)
      setTabData((prev) => ({ ...prev, dashboard }))
    } catch (err) {
      console.error('Power Law fetch error:', err)
      setError(err.message || t('common:widget.failedToLoad', { name: t('market:powerLaw.title') }))
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch tab-specific data when tab changes
  useEffect(() => {
    if (activeTab === 'main') return
    if (tabData[activeTab]) return // Already loaded

    const fetchMap = {
      curve: api.getPowerLawCurve,
      gold: api.getPowerLawGold,
      m2: api.getPowerLawM2,
      spx: api.getPowerLawSPX,
      assets: api.getPowerLawAssets,
      milestones: api.getPowerLawMilestones,
    }

    const fetcher = fetchMap[activeTab]
    if (!fetcher) return

    fetcher()
      .then((data) => setTabData((prev) => ({ ...prev, [activeTab]: data })))
      .catch((err) => console.error(`${activeTab} fetch error:`, err))
  }, [activeTab, tabData])

  useEffect(() => {
    fetchMainData()
    const interval = setInterval(fetchMainData, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchMainData])

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('market:powerLaw.title')}</h1>
        <LoadingPlaceholder />
      </div>
    )
  }

  if (error && !current) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">{t('market:powerLaw.title')}</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{t('common:widget.failedToLoad', { name: t('market:powerLaw.title') })}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button onClick={fetchMainData} className="text-accent-blue text-xs hover:underline">{t('common:app.retry')}</button>
        </div>
      </div>
    )
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'main':
        return <MainTab current={current} historical={historical} dashboard={tabData.dashboard} t={t} />
      case 'curve':
        return <PLCurve data={tabData.curve} />
      case 'gold':
        return <PLGold data={tabData.gold} />
      case 'm2':
        return <PLM2 data={tabData.m2} />
      case 'spx':
        return <PLSPX data={tabData.spx} />
      case 'assets':
        return <PLAssets data={tabData.assets} />
      case 'calculator':
        return <PLCalculator />
      case 'milestones':
        return <PLMilestones data={tabData.milestones} />
      default:
        return <PLDashboard data={tabData.dashboard} />
    }
  }

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <h1 className="text-lg font-bold">{t('market:powerLaw.title')}</h1>

      {/* Internal Power Law Tab Bar */}
      <TabBar activeTab={activeTab} setActiveTab={setActiveTab} t={t} />

      {/* Tab Content */}
      <Suspense fallback={<LoadingPlaceholder />}>
        {renderTab()}
      </Suspense>

      <DataSourceFooter sources={['binance', 'coingecko', 'alphavantage', 'yahoo', 'fred', 'ols']} />
    </div>
  )
}
