import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSubscription } from '../contexts/SubscriptionContext'

const FEATURES = [
  'paywall.features.predictions',
  'paywall.features.signals',
  'paywall.features.smartMoney',
  'paywall.features.advisor',
  'paywall.features.alerts',
  'paywall.features.whales',
]

const TIERS_DISPLAY = [
  { labelKey: 'paywall.monthly', stars: 500 },
  { labelKey: 'paywall.quarterly', stars: 1250, popular: true },
  { labelKey: 'paywall.yearly', stars: 4500 },
]

export default function PaywallOverlay() {
  const navigate = useNavigate()
  const { t } = useTranslation('common')
  const { tier } = useSubscription()

  const hadTrial = tier === 'expired' || tier === 'trial_expired'

  return (
    <div className="px-4 pt-8 pb-24 flex flex-col items-center text-center">
      {/* Lock Icon */}
      <div className="w-16 h-16 rounded-full bg-accent-yellow/10 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-accent-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0110 0v4" />
        </svg>
      </div>

      <h1 className="text-xl font-bold text-text-primary mb-1">{t('paywall.title')}</h1>
      <p className="text-text-muted text-sm mb-6 max-w-xs">{t('paywall.subtitle')}</p>

      {hadTrial && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-xl px-4 py-2 mb-4 w-full max-w-sm">
          <p className="text-accent-red text-xs font-medium">{t('paywall.trialExpired')}</p>
        </div>
      )}

      {/* Features */}
      <div className="bg-bg-card rounded-xl border border-white/5 p-4 w-full max-w-sm mb-5">
        <ul className="space-y-2.5 text-left">
          {FEATURES.map((key) => (
            <li key={key} className="flex items-center gap-2.5 text-sm text-text-secondary">
              <svg className="w-4 h-4 text-accent-green shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              {t(key)}
            </li>
          ))}
        </ul>
      </div>

      {/* Pricing */}
      <div className="w-full max-w-sm space-y-2 mb-5">
        {TIERS_DISPLAY.map((tier) => (
          <div
            key={tier.labelKey}
            className={`flex items-center justify-between rounded-xl px-4 py-3 border ${
              tier.popular
                ? 'bg-accent-blue/10 border-accent-blue/30'
                : 'bg-bg-card border-white/5'
            }`}
          >
            <span className="text-text-primary text-sm font-medium">
              {t(tier.labelKey)}
              {tier.popular && (
                <span className="ml-2 text-[8px] bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded-full font-semibold uppercase">
                  BEST
                </span>
              )}
            </span>
            <span className="text-accent-yellow font-bold text-sm">{tier.stars} Stars</span>
          </div>
        ))}
      </div>

      {/* CTA Buttons */}
      <button
        onClick={() => navigate('/settings')}
        className="w-full max-w-sm py-3 rounded-xl text-sm font-bold text-white bg-accent-blue active:scale-95 transition-all mb-2"
      >
        {hadTrial ? t('paywall.subscribe') : t('paywall.startTrial')}
      </button>
      <button
        onClick={() => navigate('/subscription')}
        className="text-accent-blue text-xs font-medium mb-5"
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
        className="w-full max-w-sm flex items-center gap-3 bg-bg-card rounded-xl border border-accent-blue/15 p-4 hover:border-accent-blue/30 transition-colors text-left"
      >
        <div className="w-9 h-9 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-text-primary text-sm font-medium">{t('paywall.joinCouncil')}</p>
          <p className="text-text-muted text-[10px]">{t('paywall.councilDesc')}</p>
        </div>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  )
}
