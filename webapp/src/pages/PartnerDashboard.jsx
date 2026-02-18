import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../utils/api'

function StatCard({ label, value, sub, color = 'text-text-primary' }) {
  return (
    <div className="bg-bg-card rounded-xl border border-white/5 p-3 text-center">
      <div className="text-text-muted text-[9px] font-medium">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {sub && <div className="text-text-muted text-[9px]">{sub}</div>}
    </div>
  )
}

export default function PartnerDashboard() {
  const { code } = useParams()
  const [stats, setStats] = useState(null)
  const [referrals, setReferrals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!code) return
    setLoading(true)
    Promise.all([
      api.getPartnerStats(code),
      api.getPartnerReferrals(code),
    ])
      .then(([statsData, refData]) => {
        setStats(statsData)
        setReferrals(refData.referrals || [])
      })
      .catch((err) => setError(err.message || 'Partner not found'))
      .finally(() => setLoading(false))
  }, [code])

  const copyLink = () => {
    if (!stats?.referral_link) return
    navigator.clipboard.writeText(stats.referral_link).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Partner Dashboard</h1>
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Partner Dashboard</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm">{error}</p>
        </div>
      </div>
    )
  }

  const s = stats?.stats || {}

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Partner Dashboard</h1>
        <span className="text-[10px] px-2 py-1 rounded bg-accent-blue/15 text-accent-blue font-medium">
          {stats?.partner_name}
        </span>
      </div>

      {/* Share Link */}
      <div className="bg-bg-card rounded-xl border border-accent-blue/20 p-3">
        <p className="text-text-muted text-[10px] mb-1">Your Referral Link</p>
        <div className="flex items-center gap-2">
          <code className="text-[10px] text-text-primary bg-white/5 px-2 py-1 rounded flex-1 break-all">
            {stats?.referral_link}
          </code>
          <button
            onClick={copyLink}
            className="text-[10px] px-3 py-1.5 bg-accent-blue/15 text-accent-blue rounded-lg hover:bg-accent-blue/25 shrink-0"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <p className="text-text-muted text-[9px] mt-1">
          Commission rate: <span className="text-accent-green font-bold">{stats?.commission_pct}%</span>
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Users Referred" value={s.total_referrals || 0} color="text-accent-blue" />
        <StatCard label="Conversions" value={s.conversions || 0} color="text-accent-green" />
        <StatCard
          label="Conversion Rate"
          value={`${s.conversion_rate || 0}%`}
          color={s.conversion_rate > 10 ? 'text-accent-green' : 'text-text-primary'}
        />
        <StatCard label="Total Stars Earned" value={s.total_stars_earned || 0} />
      </div>

      {/* Commission Summary */}
      <div className="bg-bg-card rounded-xl border border-white/5 p-3">
        <p className="text-text-muted text-[10px] mb-2">Commission</p>
        <div className="flex justify-between items-center">
          <div>
            <p className="text-text-primary text-sm font-bold">
              {(s.total_commission || 0).toFixed(1)} Stars
            </p>
            <p className="text-text-muted text-[9px]">Total earned</p>
          </div>
          <div className="text-right">
            <p className="text-accent-yellow text-sm font-bold">
              {(s.pending_commission || 0).toFixed(1)} Stars
            </p>
            <p className="text-text-muted text-[9px]">Pending payout</p>
          </div>
        </div>
      </div>

      {/* Referred Users */}
      <div>
        <p className="text-text-secondary text-xs font-semibold mb-2">
          Referred Users ({referrals.length})
        </p>
        {referrals.length === 0 ? (
          <div className="bg-bg-card rounded-xl border border-white/5 p-4 text-center">
            <p className="text-text-muted text-xs">No referrals yet. Share your link to get started!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {referrals.map((r, i) => (
              <div key={i} className="bg-bg-card rounded-xl border border-white/5 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-text-primary text-xs font-semibold">{r.user_label}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                    r.subscribed
                      ? 'bg-accent-green/15 text-accent-green'
                      : 'bg-white/5 text-text-muted'
                  }`}>
                    {r.subscribed ? 'PREMIUM' : 'FREE'}
                  </span>
                </div>
                <div className="text-text-muted text-[9px] mt-1">
                  Joined: {r.signed_up_at ? new Date(r.signed_up_at).toLocaleDateString() : '--'}
                  {r.subscription_tier && ` | Tier: ${r.subscription_tier}`}
                  {r.commission_earned != null && (
                    <span className="text-accent-green"> | Commission: {r.commission_earned.toFixed(1)} Stars</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
