import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'

const TIER_COLORS = {
  premium: { bg: 'bg-accent-blue/15', border: 'border-accent-blue/40', text: 'text-accent-blue', labelKey: 'subscriptionPage.premium' },
  trial:   { bg: 'bg-accent-yellow/15', border: 'border-accent-yellow/40', text: 'text-accent-yellow', labelKey: 'subscriptionPage.trial' },
  free:    { bg: 'bg-white/10', border: 'border-white/20', text: 'text-text-muted', labelKey: 'subscriptionPage.free' },
}

const PROGRESS_COLORS = {
  premium: 'bg-accent-blue',
  trial:   'bg-accent-yellow',
  free:    'bg-white/20',
}

function formatDate(iso) {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function Subscription() {
  const navigate = useNavigate()
  const { tg } = useTelegram()
  const { t } = useTranslation('settings')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!tg?.initData) return
    api.getSubscriptionStatus(tg.initData)
      .then(setData)
      .catch(() => setError(t('subscription.couldNotStart')))
      .finally(() => setLoading(false))
  }, [tg, t])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="px-4 pt-4">
        <h1 className="text-lg font-bold mb-4">{t('subscriptionPage.title')}</h1>
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl px-3 py-2">
          <p className="text-accent-red text-xs">{error || t('app.noData', { ns: 'common' })}</p>
        </div>
      </div>
    )
  }

  const tier = TIER_COLORS[data.tier] || TIER_COLORS.free
  const progressColor = PROGRESS_COLORS[data.tier] || PROGRESS_COLORS.free

  const actionLabel = data.tier === 'free' ? t('subscription.subscribe') : data.tier === 'trial' ? t('subscription.subscribe') : data.days_remaining <= 7 ? t('subscription.subscribe') : t('subscription.subscribe')

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">{t('subscriptionPage.title')}</h1>

      {/* Status Card */}
      <div className={`rounded-xl border p-4 ${tier.bg} ${tier.border}`}>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${tier.bg} ${tier.text} border ${tier.border}`}>
            {t(tier.labelKey)}
          </span>
          {data.is_premium && (
            <svg className="w-5 h-5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          )}
        </div>

        <p className="text-text-primary text-sm font-medium mb-1">{data.status_text}</p>

        {data.tier !== 'free' && (
          <>
            <p className="text-text-muted text-xs mb-2">
              {data.tier === 'premium' ? `Expires ${formatDate(data.subscription_end)}` : `Trial ends ${formatDate(data.trial_end)}`}
              {' '}&middot; {data.days_remaining}{t('subscriptionPage.daysRemaining')}
            </p>

            {/* Progress bar */}
            <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${progressColor}`}
                style={{ width: `${data.progress_pct}%` }}
              />
            </div>
          </>
        )}
      </div>

      {/* Action Button */}
      <button
        onClick={() => navigate('/settings')}
        className="w-full py-3 rounded-xl text-sm font-bold text-white bg-accent-blue active:scale-[0.98] transition-all"
      >
        {actionLabel}
      </button>

      {/* Payment History */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-text-primary">{t('subscriptionPage.paymentHistory')}</h2>
        {data.payments.length === 0 ? (
          <div className="bg-bg-card rounded-xl border border-white/5 p-4 text-center">
            <p className="text-text-muted text-xs">{t('subscriptionPage.noPayments')}</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {data.payments.map((p) => (
              <div key={p.id} className="flex items-center gap-3 bg-bg-card rounded-xl border border-white/5 p-3">
                <div className="w-8 h-8 rounded-lg bg-accent-blue/10 flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-text-primary text-xs font-medium capitalize">{p.tier} &middot; {p.days}d</p>
                  <p className="text-text-muted text-[10px]">{formatDate(p.created_at)}</p>
                </div>
                <span className="text-text-primary text-xs font-semibold shrink-0">{p.stars_amount} {t('subscription.stars')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Member Since */}
      {data.joined_at && (
        <div className="bg-bg-card rounded-xl border border-white/5 p-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-green/10 flex items-center justify-center shrink-0">
            <svg className="w-4 h-4 text-accent-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <div>
            <p className="text-text-muted text-[10px]">{t('subscriptionPage.memberSince')}</p>
            <p className="text-text-primary text-xs font-medium">{formatDate(data.joined_at)}</p>
          </div>
        </div>
      )}
    </div>
  )
}
