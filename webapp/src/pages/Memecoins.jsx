import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { formatCoinPrice } from '../utils/format'

const RISK_COLORS = {
  low: { bg: 'bg-accent-green/20', text: 'text-accent-green', border: 'border-accent-green/20' },
  medium: { bg: 'bg-accent-yellow/20', text: 'text-accent-yellow', border: 'border-accent-yellow/20' },
  high: { bg: 'bg-accent-orange/20', text: 'text-accent-orange', border: 'border-accent-orange/20' },
  critical: { bg: 'bg-accent-red/20', text: 'text-accent-red', border: 'border-accent-red/20' },
}

function getRiskLevel(score) {
  if (score < 25) return 'low'
  if (score < 50) return 'medium'
  if (score < 75) return 'high'
  return 'critical'
}

function RiskBadge({ score }) {
  const level = getRiskLevel(score)
  const style = RISK_COLORS[level]
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${style.bg} ${style.text}`}>
      {score}/100 {level.toUpperCase()}
    </span>
  )
}

function RiskBar({ score }) {
  const pct = Math.min(100, score)
  const color = pct < 25 ? '#22c55e' : pct < 50 ? '#eab308' : pct < 75 ? '#f97316' : '#ef4444'

  return (
    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  )
}

function MemeCard({ token }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`bg-bg-card rounded-xl p-3 border ${RISK_COLORS[getRiskLevel(token.rug_pull_score)].border} slide-up cursor-pointer`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-text-primary">{token.symbol || '???'}</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-white/5 text-text-muted rounded capitalize">{token.chain}</span>
        </div>
        <RiskBadge score={token.rug_pull_score} />
      </div>

      {token.name && (
        <p className="text-xs text-text-secondary mb-1">{token.name}</p>
      )}

      <RiskBar score={token.rug_pull_score} />

      <div className="flex items-center gap-4 text-[10px] text-text-muted mt-2">
        {token.price_usd && <span>Price: {formatCoinPrice(token.price_usd)}</span>}
        {token.volume_24h && <span>Vol: ${(token.volume_24h / 1000).toFixed(1)}K</span>}
        {token.liquidity && <span>Liq: ${(token.liquidity / 1000).toFixed(1)}K</span>}
        {token.volume_acceleration && (
          <span className="text-accent-yellow">{token.volume_acceleration.toFixed(1)}x vol</span>
        )}
      </div>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-white/5 space-y-1">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="flex justify-between">
              <span className="text-text-muted">Top Holder:</span>
              <span className={token.top_holder_pct > 50 ? 'text-accent-red' : 'text-text-primary'}>
                {token.top_holder_pct != null ? `${token.top_holder_pct.toFixed(1)}%` : '--'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Contract:</span>
              <span className={token.contract_verified ? 'text-accent-green' : 'text-accent-red'}>
                {token.contract_verified == null ? '--' : token.contract_verified ? 'Verified' : 'Unverified'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Liq Lock:</span>
              <span className={token.liquidity_locked ? 'text-accent-green' : 'text-accent-red'}>
                {token.liquidity_locked == null ? '--' : token.liquidity_locked ? 'Locked' : 'Unlocked'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Honeypot:</span>
              <span className={token.honeypot_risk ? 'text-accent-red' : 'text-accent-green'}>
                {token.honeypot_risk == null ? '--' : token.honeypot_risk ? 'YES' : 'No'}
              </span>
            </div>
          </div>
          <p className="text-[9px] text-text-muted font-mono truncate">{token.address}</p>
        </div>
      )}
    </div>
  )
}

export default function Memecoins() {
  const { t } = useTranslation('common')
  const [tokens, setTokens] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('trending')

  useEffect(() => {
    setLoading(true)
    const fetch = async () => {
      try {
        let result
        if (tab === 'trending') {
          result = await api.getTrendingMemecoins()
          setTokens(result?.tokens || [])
        } else {
          result = await api.getMemecoinLeaderboard()
          setTokens(result?.top_volume || [])
        }
      } catch (err) {
        console.error('Memecoins fetch error:', err)
        setTokens([])
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [tab])

  const safeCount = tokens.filter(t => t.rug_pull_score < 25).length
  const riskyCount = tokens.filter(t => t.rug_pull_score >= 50).length

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Memecoin Scanner</h1>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Tracked</p>
          <p className="text-text-primary text-lg font-bold">{tokens.length}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Safe</p>
          <p className="text-accent-green text-lg font-bold">{safeCount}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <p className="text-text-muted text-[10px]">Risky</p>
          <p className="text-accent-red text-lg font-bold">{riskyCount}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {['trending', 'leaderboard'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors capitalize ${
              tab === t
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'bg-bg-card border-white/5 text-text-muted'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Token List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : tokens.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-text-muted text-sm">No memecoins discovered yet</p>
          <div className="bg-bg-card rounded-xl p-4 border border-white/5 max-w-sm mx-auto text-left space-y-2">
            <p className="text-text-secondary text-xs leading-relaxed">
              The scanner searches DexScreener for trending memecoins every 10 minutes across Solana, Ethereum, BSC and more.
            </p>
            <p className="text-text-muted text-[10px]">
              Tokens must have &gt;$10K volume and &gt;$5K liquidity to qualify. New tokens typically appear within 30 minutes of launch.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {tokens.map((token, i) => (
            <MemeCard key={token.id || token.address || i} token={token} />
          ))}
        </div>
      )}

      <p className="text-text-muted text-[9px] text-center leading-relaxed">
        Risk scores are algorithmic estimates. DYOR. This is not financial advice.
        Tap a card to expand risk details.
      </p>
    </div>
  )
}
