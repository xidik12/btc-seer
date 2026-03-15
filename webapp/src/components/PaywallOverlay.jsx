import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSubscription } from '../contexts/SubscriptionContext'

const FEATURES = [
  { key: 'paywall.features.predictions', icon: '🧠' },
  { key: 'paywall.features.signals', icon: '📡' },
  { key: 'paywall.features.smartMoney', icon: '🐋' },
  { key: 'paywall.features.advisor', icon: '🎯' },
  { key: 'paywall.features.alerts', icon: '🔔' },
  { key: 'paywall.features.whales', icon: '💰' },
]

const TIERS_DISPLAY = [
  { labelKey: 'paywall.monthly', stars: 500, save: null },
  { labelKey: 'paywall.quarterly', stars: 1250, popular: true, save: '17%' },
  { labelKey: 'paywall.yearly', stars: 4500, save: '25%' },
]

export default function PaywallOverlay() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { tier } = useSubscription()

  const hadTrial = tier === 'expired' || tier === 'trial_expired'

  return (
    <div className="px-4 pt-6 pb-24 flex flex-col items-center text-center">
      {/* Hero */}
      <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 flex items-center justify-center mb-5">
        <div className="absolute inset-0 rounded-full bg-accent-blue/10 animate-ping opacity-30" />
        <svg className="w-10 h-10 text-accent-blue relative z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0110 0v4" />
        </svg>
      </div>

      <h1 className="text-2xl font-bold text-text-primary mb-2">{t('paywall.title')}</h1>
      <p className="text-text-muted text-sm mb-6 max-w-xs leading-relaxed">{t('paywall.subtitle')}</p>

      {hadTrial && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-card-sm px-4 py-2.5 mb-5 w-full max-w-sm">
          <p className="text-accent-red text-xs font-medium">{t('paywall.trialExpired')}</p>
        </div>
      )}

      {/* Features — 2-col grid */}
      <div className="w-full max-w-sm mb-6">
        <div className="grid grid-cols-2 gap-2">
          {FEATURES.map(({ key, icon }) => (
            <div key={key} className="flex items-center gap-2 bg-bg-card rounded-card-sm border border-white/5 px-3 py-2.5">
              <span className="text-base">{icon}</span>
              <span className="text-xs text-text-secondary font-medium">{t(key)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing tiers */}
      <div className="w-full max-w-sm space-y-2.5 mb-6">
        {TIERS_DISPLAY.map((t_item) => (
          <button
            key={t_item.labelKey}
            onClick={() => navigate('/settings')}
            className={`w-full flex items-center justify-between rounded-card px-4 py-3.5 border transition-all active:scale-[0.98] ${
              t_item.popular
                ? 'bg-accent-blue/10 border-accent-blue/40 shadow-[0_0_20px_rgba(59,130,246,0.1)]'
                : 'bg-bg-card border-white/5 hover:border-white/10'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-text-primary text-sm font-semibold">
                {t(t_item.labelKey)}
              </span>
              {t_item.popular && (
                <span className="text-[10px] bg-accent-blue text-white px-2 py-0.5 rounded-full font-bold uppercase tracking-wide">
                  BEST
                </span>
              )}
              {t_item.save && !t_item.popular && (
                <span className="text-[10px] bg-accent-green/15 text-accent-green px-1.5 py-0.5 rounded-full font-semibold">
                  Save {t_item.save}
                </span>
              )}
            </div>
            <span className="text-accent-yellow font-bold text-sm">{t_item.stars} Stars</span>
          </button>
        ))}
      </div>

      {/* Primary CTA */}
      <button
        onClick={() => navigate('/settings')}
        className="w-full max-w-sm py-3.5 rounded-card text-sm font-bold text-white bg-accent-blue hover:bg-accent-blue/90 active:scale-[0.97] transition-all mb-3 shadow-[0_4px_16px_rgba(59,130,246,0.3)]"
      >
        {hadTrial ? t('paywall.subscribe') : t('paywall.startTrial')}
      </button>
      <button
        onClick={() => navigate('/subscription')}
        className="text-accent-blue text-xs font-medium mb-6 hover:underline"
      >
        {t('paywall.viewPlans')}
      </button>

      {/* Community CTA */}
      <button
        onClick={() => {
          const tg = window.Telegram?.WebApp
          if (tg?.openTelegramLink) {
            tg.openTelegramLink('https://t.me/+-72wnR04tPUyZmIy')
          } else {
            window.open('https://t.me/+-72wnR04tPUyZmIy', '_blank')
          }
        }}
        className="w-full max-w-sm flex items-center gap-3 bg-bg-card rounded-card border border-accent-blue/15 p-4 hover:border-accent-blue/30 active:scale-[0.98] transition-all text-left"
      >
        <div className="w-10 h-10 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
          <p className="text-text-muted text-xs">{t('paywall.councilDesc')}</p>
        </div>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  )
}
