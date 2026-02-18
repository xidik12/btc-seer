import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { formatPrice, formatTimeAgo } from '../utils/format'
import { getBotUsernameSync } from '../utils/botConfig'

function StatCard({ label, value, sub, color = 'text-text-primary' }) {
  return (
    <div className="bg-bg-card rounded-xl border border-white/5 p-3 text-center">
      <div className="text-text-muted text-[9px] font-medium">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {sub && <div className="text-text-muted text-[9px]">{sub}</div>}
    </div>
  )
}

function OverviewTab({ stats }) {
  if (!stats) return <div className="animate-pulse"><div className="h-32 bg-bg-card rounded-2xl" /></div>

  return (
    <div className="space-y-3">
      <div className="text-text-secondary text-xs font-semibold">Users</div>
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Total" value={stats.users.total} />
        <StatCard label="Premium" value={stats.users.premium} color="text-accent-blue" />
        <StatCard label="Banned" value={stats.users.banned} color="text-accent-red" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Joined 24h" value={stats.users.joined_24h} color="text-accent-green" />
        <StatCard label="Joined 7d" value={stats.users.joined_7d} color="text-accent-green" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Active 24h" value={stats.users.active_24h} color="text-accent-blue" />
        <StatCard label="Active 7d" value={stats.users.active_7d} color="text-accent-yellow" />
      </div>

      <div className="text-text-secondary text-xs font-semibold mt-4">Predictions</div>
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Total" value={stats.predictions.total} />
        <StatCard
          label="Accuracy"
          value={`${stats.predictions.accuracy_pct}%`}
          sub={`${stats.predictions.correct}/${stats.predictions.evaluated}`}
          color={stats.predictions.accuracy_pct > 55 ? 'text-accent-green' : 'text-accent-yellow'}
        />
      </div>

      <div className="text-text-secondary text-xs font-semibold mt-4">Trades</div>
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Trades" value={stats.trades.total} />
        <StatCard label="Results" value={stats.trades.results} />
        <StatCard
          label="Win Rate"
          value={`${stats.trades.win_rate_pct}%`}
          color={stats.trades.win_rate_pct > 50 ? 'text-accent-green' : 'text-accent-red'}
        />
      </div>
    </div>
  )
}

function UsersTab({ initData }) {
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAdminUsers(initData, page, search)
      setUsers(data.users || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error('Admin users error:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [initData, page, search])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const handleBan = async (telegramId) => {
    const reason = prompt('Ban reason:')
    if (!reason) return
    try {
      await api.adminBanUser(initData, telegramId, reason)
      fetchUsers()
    } catch (err) {
      console.error('Failed to ban:', err.message)
    }
  }

  const handleUnban = async (telegramId) => {
    if (!confirm('Unban this user?')) return
    try {
      await api.adminUnbanUser(initData, telegramId)
      fetchUsers()
    } catch (err) {
      console.error('Failed to unban:', err.message)
    }
  }

  const handleGrantPremium = async (telegramId) => {
    const days = prompt('Days of premium to grant:', '30')
    if (!days) return
    try {
      await api.adminGrantPremium(initData, telegramId, parseInt(days))
      fetchUsers()
    } catch (err) {
      console.error('Failed to grant premium:', err.message)
    }
  }

  return (
    <div className="space-y-3">
      <input
        type="text"
        placeholder="Search username or telegram ID..."
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-muted"
      />

      <div className="text-text-muted text-[9px]">{total} users total</div>

      {error && (
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl px-3 py-2">
          <p className="text-accent-red text-xs">{error}</p>
          <button onClick={fetchUsers} className="text-accent-blue text-[10px] mt-1 hover:underline">Retry</button>
        </div>
      )}

      {loading ? (
        <div className="animate-pulse space-y-2">
          {[1,2,3].map(i => <div key={i} className="h-16 bg-bg-card rounded-xl" />)}
        </div>
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.telegram_id} className={`bg-bg-card rounded-xl border p-3 ${u.is_banned ? 'border-accent-red/30' : 'border-white/5'}`}>
              <div className="flex items-center justify-between mb-1">
                <div>
                  <span className="text-text-primary text-xs font-semibold">
                    @{u.username || 'no_username'}
                  </span>
                  <span className="text-text-muted text-[9px] ml-2">ID: {u.telegram_id}</span>
                </div>
                <div className="flex items-center gap-1">
                  {u.is_banned && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-accent-red/15 text-accent-red">BANNED</span>
                  )}
                  {u.subscription_tier === 'premium' && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-accent-blue/15 text-accent-blue">PREMIUM</span>
                  )}
                </div>
              </div>
              <div className="text-text-muted text-[9px]">
                Joined: {u.joined_at ? formatTimeAgo(u.joined_at) : '--'}
                {u.subscription_end && ` | Sub ends: ${new Date(u.subscription_end).toLocaleDateString()}`}
                {u.ban_reason && ` | Ban: ${u.ban_reason}`}
              </div>
              <div className="flex gap-1.5 mt-2">
                {u.is_banned ? (
                  <button onClick={() => handleUnban(u.telegram_id)}
                    className="text-[9px] px-2 py-1 rounded bg-accent-green/15 text-accent-green hover:bg-accent-green/25">
                    Unban
                  </button>
                ) : (
                  <button onClick={() => handleBan(u.telegram_id)}
                    className="text-[9px] px-2 py-1 rounded bg-accent-red/15 text-accent-red hover:bg-accent-red/25">
                    Ban
                  </button>
                )}
                <button onClick={() => handleGrantPremium(u.telegram_id)}
                  className="text-[9px] px-2 py-1 rounded bg-accent-blue/15 text-accent-blue hover:bg-accent-blue/25">
                  Grant Premium
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2 pt-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="text-xs px-3 py-1 rounded bg-bg-hover text-text-secondary disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-xs text-text-muted py-1">Page {page}</span>
          <button
            disabled={page * 50 >= total}
            onClick={() => setPage(p => p + 1)}
            className="text-xs px-3 py-1 rounded bg-bg-hover text-text-secondary disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

function PredictionsTab({ predictions }) {
  if (!predictions) return <div className="animate-pulse"><div className="h-32 bg-bg-card rounded-2xl" /></div>

  return (
    <div className="space-y-2">
      {predictions.map((p) => (
        <div key={p.id} className={`bg-bg-card rounded-xl border p-3 ${
          p.was_correct === true ? 'border-accent-green/20' :
          p.was_correct === false ? 'border-accent-red/20' :
          'border-white/5'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                p.direction === 'bullish' ? 'bg-accent-green/15 text-accent-green' :
                p.direction === 'bearish' ? 'bg-accent-red/15 text-accent-red' :
                'bg-bg-hover text-text-muted'
              }`}>
                {p.direction?.toUpperCase()}
              </span>
              <span className="text-text-muted text-[9px]">{p.timeframe}</span>
              <span className="text-text-muted text-[9px]">{p.confidence?.toFixed(0)}%</span>
            </div>
            <div>
              {p.was_correct === true && <span className="text-accent-green text-[9px] font-bold">CORRECT</span>}
              {p.was_correct === false && <span className="text-accent-red text-[9px] font-bold">WRONG</span>}
              {p.was_correct === null && <span className="text-text-muted text-[9px]">PENDING</span>}
            </div>
          </div>
          <div className="text-text-muted text-[9px]">
            Price: {formatPrice(p.current_price)}
            {p.predicted_change_pct != null && ` | Predicted: ${p.predicted_change_pct >= 0 ? '+' : ''}${p.predicted_change_pct.toFixed(2)}%`}
            {p.actual_price && ` | Actual: ${formatPrice(p.actual_price)}`}
          </div>
          <div className="text-text-muted text-[9px] mt-0.5">{formatTimeAgo(p.timestamp)}</div>
        </div>
      ))}
    </div>
  )
}

function BotStatusCard({ initData }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAdminBotStatus(initData)
      setStatus(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [initData])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  if (loading) return <div className="animate-pulse h-20 bg-bg-card rounded-xl" />

  return (
    <div className={`bg-bg-card rounded-xl border p-3 ${status?.bot_ok ? 'border-accent-green/20' : 'border-accent-red/20'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-secondary text-xs font-semibold">Bot Status</span>
        <button onClick={fetchStatus} className="text-accent-blue text-[9px] hover:underline">Refresh</button>
      </div>
      {error ? (
        <div className="text-accent-red text-[10px]">{error}</div>
      ) : (
        <div className="space-y-1 text-[10px]">
          <div className="flex justify-between">
            <span className="text-text-muted">Status</span>
            <span className={status.bot_ok ? 'text-accent-green font-bold' : 'text-accent-red font-bold'}>
              {status.bot_ok ? 'CONNECTED' : 'DOWN'}
            </span>
          </div>
          {status.bot_info && (
            <div className="flex justify-between">
              <span className="text-text-muted">Username</span>
              <span className="text-text-primary font-mono">@{status.bot_info.username}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-text-muted">Bot Users in DB</span>
            <span className="text-text-primary font-bold">{status.bot_users_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Token Set</span>
            <span className={status.token_set ? 'text-accent-green' : 'text-accent-red'}>{status.token_set ? 'Yes' : 'No'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">DB</span>
            <span className="text-text-muted font-mono">{status.database_type}</span>
          </div>
          {status.bot_error && (
            <div className="text-accent-red mt-1">{status.bot_error}</div>
          )}
        </div>
      )}
    </div>
  )
}

function SystemTab({ system, initData }) {
  if (!system) return <div className="animate-pulse"><div className="h-32 bg-bg-card rounded-2xl" /></div>

  return (
    <div className="space-y-3">
      <BotStatusCard initData={initData} />

      <div className="text-text-secondary text-xs font-semibold">Latest Price</div>
      <div className="bg-bg-card rounded-xl border border-white/5 p-3">
        <span className="text-text-primary text-lg font-bold">{formatPrice(system.latest_price?.price)}</span>
        <span className="text-text-muted text-[9px] ml-2">{system.latest_price?.timestamp ? formatTimeAgo(system.latest_price.timestamp) : '--'}</span>
      </div>

      <div className="text-text-secondary text-xs font-semibold mt-4">Active Models</div>
      {system.active_models?.length > 0 ? (
        <div className="space-y-2">
          {system.active_models.map((m) => (
            <div key={m.id} className="bg-bg-card rounded-xl border border-white/5 p-3">
              <div className="text-text-primary text-xs font-semibold">{m.model_type} v{m.version}</div>
              <div className="text-text-muted text-[9px]">
                1h: {m.live_accuracy_1h ? `${m.live_accuracy_1h.toFixed(1)}%` : '--'}
                {' | '}
                24h: {m.live_accuracy_24h ? `${m.live_accuracy_24h.toFixed(1)}%` : '--'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-text-muted text-xs">No active models</div>
      )}

      <div className="text-text-secondary text-xs font-semibold mt-4">Table Counts</div>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(system.table_counts || {}).map(([name, count]) => (
          <div key={name} className="bg-bg-card rounded-xl border border-white/5 p-2">
            <div className="text-text-muted text-[9px]">{name}</div>
            <div className="text-text-primary text-sm font-bold">{count.toLocaleString()}</div>
          </div>
        ))}
      </div>

      <div className="text-text-secondary text-xs font-semibold mt-4">Config</div>
      <div className="bg-bg-card rounded-xl border border-white/5 p-3 space-y-1">
        {Object.entries(system.config || {}).map(([key, val]) => (
          <div key={key} className="flex justify-between text-[9px]">
            <span className="text-text-muted">{key}</span>
            <span className="text-text-primary font-mono">{String(val)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function PartnersTab({ initData }) {
  const [partners, setPartners] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [createdLink, setCreatedLink] = useState(null)
  const [form, setForm] = useState({ name: '', code: '', telegram_id: '', commission_pct: 20, contact_email: '', contact_telegram: '' })

  const fetchPartners = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAdminPartners(initData)
      setPartners(data.partners || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [initData])

  useEffect(() => { fetchPartners() }, [fetchPartners])

  const handleCreate = async () => {
    if (!form.name || !form.code) return
    const payload = { ...form, telegram_id: form.telegram_id ? parseInt(form.telegram_id) : null }
    try {
      const result = await api.createAdminPartner(initData, payload)
      setShowCreate(false)
      setCreatedLink(result.referral_link)
      setForm({ name: '', code: '', telegram_id: '', commission_pct: 20, contact_email: '', contact_telegram: '' })
      fetchPartners()
    } catch (err) {
      console.error('Failed:', err.message)
    }
  }

  const handleToggle = async (id, currentActive) => {
    try {
      await api.updateAdminPartner(initData, id, { is_active: !currentActive })
      fetchPartners()
    } catch (err) {
      console.error('Failed:', err.message)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-text-muted text-[9px]">{partners.length} partners total</span>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-[10px] px-3 py-1 rounded-lg bg-accent-blue/15 text-accent-blue hover:bg-accent-blue/25"
        >
          {showCreate ? 'Cancel' : '+ Create Partner'}
        </button>
      </div>

      {createdLink && (
        <div className="bg-bg-card rounded-xl border border-accent-green/30 p-3 space-y-2 slide-up">
          <p className="text-accent-green text-xs font-semibold">Partner Created! Share this link:</p>
          <div className="flex items-center gap-2">
            <code className="text-[10px] text-text-primary bg-white/5 px-2 py-1 rounded flex-1 break-all">{createdLink}</code>
            <button onClick={() => { navigator.clipboard.writeText(createdLink); }}
              className="text-[10px] px-3 py-1.5 bg-accent-green/15 text-accent-green rounded-lg shrink-0">Copy</button>
          </div>
          <button onClick={() => setCreatedLink(null)}
            className="text-[9px] text-text-muted hover:text-text-primary">Dismiss</button>
        </div>
      )}

      {showCreate && (
        <div className="bg-bg-card rounded-xl border border-accent-blue/20 p-3 space-y-2 slide-up">
          <input type="text" placeholder="Partner Name" value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-xs text-text-primary" />
          <input type="text" placeholder="Referral Code (e.g. CRYPTOEDU)" value={form.code}
            onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-xs text-text-primary font-mono" />
          <input type="text" placeholder="Partner's Telegram ID (for dashboard access)" value={form.telegram_id}
            onChange={e => setForm({ ...form, telegram_id: e.target.value.replace(/\D/g, '') })}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-xs text-text-primary font-mono" />
          <div className="flex gap-2">
            <input type="number" placeholder="Commission %" value={form.commission_pct}
              onChange={e => setForm({ ...form, commission_pct: parseFloat(e.target.value) || 0 })}
              className="w-24 bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-xs text-text-primary" />
            <input type="text" placeholder="Email (optional)" value={form.contact_email}
              onChange={e => setForm({ ...form, contact_email: e.target.value })}
              className="flex-1 bg-bg-hover border border-white/10 rounded-lg px-3 py-1.5 text-xs text-text-primary" />
          </div>
          <button onClick={handleCreate}
            className="w-full text-xs py-2 rounded-lg bg-accent-blue text-white font-semibold hover:bg-accent-blue/80">
            Create Partner
          </button>
        </div>
      )}

      {error && (
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl px-3 py-2">
          <p className="text-accent-red text-xs">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="animate-pulse space-y-2">
          {[1,2,3].map(i => <div key={i} className="h-16 bg-bg-card rounded-xl" />)}
        </div>
      ) : partners.length === 0 ? (
        <div className="text-center text-text-muted text-xs py-8">
          No partners yet. Create one to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {partners.map(p => (
            <div key={p.id} className={`bg-bg-card rounded-xl border p-3 ${p.is_active ? 'border-white/5' : 'border-accent-red/20 opacity-60'}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-text-primary text-xs font-semibold">{p.name}</span>
                  <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">{p.code}</span>
                </div>
                <button onClick={() => handleToggle(p.id, p.is_active)}
                  className={`text-[8px] px-2 py-0.5 rounded ${p.is_active ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-red/15 text-accent-red'}`}>
                  {p.is_active ? 'Active' : 'Inactive'}
                </button>
              </div>
              <div className="grid grid-cols-4 gap-2 mt-2">
                <div className="text-center">
                  <div className="text-text-primary text-xs font-bold">{p.total_referrals}</div>
                  <div className="text-text-muted text-[8px]">Referrals</div>
                </div>
                <div className="text-center">
                  <div className="text-accent-green text-xs font-bold">{p.conversions}</div>
                  <div className="text-text-muted text-[8px]">Converts</div>
                </div>
                <div className="text-center">
                  <div className="text-text-primary text-xs font-bold">{p.conversion_rate}%</div>
                  <div className="text-text-muted text-[8px]">Rate</div>
                </div>
                <div className="text-center">
                  <div className="text-accent-yellow text-xs font-bold">{p.total_commission}</div>
                  <div className="text-text-muted text-[8px]">Comm.</div>
                </div>
              </div>
              <div className="text-text-muted text-[8px] mt-1">
                {p.commission_pct}% commission
                {p.telegram_id && <span className="text-accent-blue"> | TG: {p.telegram_id}</span>}
                {!p.telegram_id && <span className="text-accent-yellow"> | No TG linked</span>}
                {p.contact_email && ` | ${p.contact_email}`}
              </div>
              <button onClick={() => { navigator.clipboard.writeText(`https://t.me/${getBotUsernameSync()}?start=partner_${p.code}`) }}
                className="text-[8px] mt-1 px-2 py-0.5 rounded bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20">
                Copy Referral Link
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AdminDashboard() {
  const { tg, user } = useTelegram()
  const initData = tg?.initData || ''

  const [tab, setTab] = useState('overview')
  const [stats, setStats] = useState(null)
  const [predictions, setPredictions] = useState(null)
  const [system, setSystem] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!initData) {
      setError('Admin access requires Telegram login')
      setLoading(false)
      return
    }

    const fetchAll = async () => {
      try {
        const [s, p, sys] = await Promise.all([
          api.getAdminStats(initData),
          api.getAdminPredictions(initData, 50),
          api.getAdminSystem(initData),
        ])
        setStats(s)
        setPredictions(p.predictions || [])
        setSystem(sys)
      } catch (err) {
        setError(err.message || 'Admin access denied')
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [initData])

  if (error) {
    const isExpired = error.includes('expired') || error.includes('Session')
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Admin Dashboard</h1>
        <div className="bg-bg-card rounded-2xl p-6 border border-accent-red/20 text-center">
          <p className="text-accent-red text-sm mb-2">{isExpired ? 'Session Expired' : 'Access Denied'}</p>
          <p className="text-text-muted text-xs mb-3">{error}</p>
          <button
            onClick={() => { setError(null); setLoading(true); window.location.reload() }}
            className="text-accent-blue text-xs hover:underline"
          >
            {isExpired ? 'Reload App' : 'Retry'}
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="px-4 pt-4 space-y-4">
        <h1 className="text-lg font-bold">Admin Dashboard</h1>
        <div className="animate-pulse space-y-3">
          <div className="h-32 bg-bg-card rounded-2xl" />
          <div className="h-20 bg-bg-card rounded-2xl" />
        </div>
      </div>
    )
  }

  const tabs = ['overview', 'users', 'predictions', 'partners', 'system']

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">Admin Dashboard</h1>

      <div className="flex gap-1 bg-bg-secondary/50 rounded-lg p-0.5 overflow-x-auto no-scrollbar">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-shrink-0 whitespace-nowrap px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              tab === t ? 'bg-accent-blue text-white shadow-sm' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab stats={stats} />}
      {tab === 'users' && <UsersTab initData={initData} />}
      {tab === 'predictions' && <PredictionsTab predictions={predictions} />}
      {tab === 'partners' && <PartnersTab initData={initData} />}
      {tab === 'system' && <SystemTab system={system} initData={initData} />}
    </div>
  )
}
