import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import { useLanguageSwitch } from '../i18n/useLanguage'
import AlertSettings from '../components/AlertSettings'
import ReferralCard from '../components/ReferralCard'

const TIERS = [
  {
    key: 'monthly',
    nameKey: 'subscription.monthly',
    durationKey: 'subscription.days30',
    stars: 500,
    usdKey: 'subscription.pricing.monthly',
    perMonthKey: 'subscription.pricing.monthlyPerMonth',
    savingsKey: null,
    popular: false,
  },
  {
    key: 'quarterly',
    nameKey: 'subscription.quarterly',
    durationKey: 'subscription.days90',
    stars: 1250,
    usdKey: 'subscription.pricing.quarterly',
    perMonthKey: 'subscription.pricing.quarterlyPerMonth',
    savingsKey: 'subscription.save17',
    popular: true,
  },
  {
    key: 'yearly',
    nameKey: 'subscription.yearly',
    durationKey: 'subscription.days365',
    stars: 4500,
    usdKey: 'subscription.pricing.yearly',
    perMonthKey: 'subscription.pricing.yearlyPerMonth',
    savingsKey: 'subscription.save25',
    popular: false,
  },
]

const PREMIUM_FEATURE_KEYS = [
  'subscription.features.predictions',
  'subscription.features.signals',
  'subscription.features.advisor',
  'subscription.features.sentiment',
  'subscription.features.alerts',
  'subscription.features.analytics',
  'subscription.features.elliott',
  'subscription.features.powerlaw',
]

function ConfirmModal({ tier, onConfirm, onCancel, loading, t }) {
  if (!tier) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-6" onClick={onCancel}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-bg-card border border-white/10 rounded-2xl p-5 w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-center mb-4">
          <div className="mb-2">
            <svg className="w-7 h-7 mx-auto text-accent-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <h3 className="text-text-primary font-bold text-base">{t('subscription.subscribeTo')}</h3>
          <p className="text-text-muted text-xs mt-1">
            {t(tier.nameKey)} &middot; {t(tier.durationKey)}
          </p>
        </div>

        <div className="bg-bg-secondary rounded-xl p-3 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary text-sm font-medium">{t(tier.nameKey)}</span>
            <div className="text-right">
              <span className="text-text-primary font-bold text-lg">{tier.stars}</span>
              <span className="text-text-muted text-xs ml-1">{t('subscription.stars')}</span>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-text-muted text-[10px]">{t(tier.perMonthKey)}{t('subscription.perMonth')}</span>
            <span className="text-text-muted text-[10px]">~{t(tier.usdKey)}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-text-muted bg-bg-secondary active:scale-95 transition-all"
          >
            {t('subscription.cancel')}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl text-sm font-bold text-white bg-accent-blue active:scale-95 transition-all disabled:opacity-50"
          >
            {loading ? t('subscription.processing') : t('subscription.subscribe')}
          </button>
        </div>
      </div>
    </div>
  )
}

function SuccessMessage({ t }) {
  return (
    <div className="bg-accent-green/10 border border-accent-green/30 rounded-xl p-4 text-center">
      <div className="mb-1">
        <svg className="w-6 h-6 mx-auto text-accent-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <p className="text-accent-green font-semibold text-sm">{t('subscription.paymentSuccess')}</p>
      <p className="text-text-muted text-xs mt-1">{t('subscription.premiumActive')}</p>
    </div>
  )
}

export default function Settings() {
  const navigate = useNavigate()
  const { tg } = useTelegram()
  const { t } = useTranslation('settings')
  const { currentLang, switchLanguage, supported } = useLanguageSwitch()
  const [selectedTier, setSelectedTier] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleTierClick = useCallback((tier) => {
    setError(null)
    setSelectedTier(tier)
  }, [])

  const handleConfirm = useCallback(async () => {
    if (!selectedTier) return
    setLoading(true)
    setError(null)

    try {
      // Get invoice link from backend
      const { invoice_link } = await api.createInvoice(selectedTier.key)

      if (!invoice_link) {
        throw new Error('No invoice link received')
      }

      // Open Telegram's native payment UI
      if (tg?.openInvoice) {
        tg.openInvoice(invoice_link, (status) => {
          setSelectedTier(null)
          setLoading(false)
          if (status === 'paid') {
            setSuccess(true)
          } else if (status === 'cancelled') {
            // User cancelled — do nothing
          } else if (status === 'failed') {
            setError(t('subscription.paymentFailed'))
          }
        })
      } else {
        // Fallback: open link directly (outside Mini App)
        window.open(invoice_link, '_blank')
        setSelectedTier(null)
        setLoading(false)
      }
    } catch (err) {
      console.error('Subscription error:', err)
      setError(t('subscription.couldNotStart'))
      setSelectedTier(null)
      setLoading(false)
    }
  }, [selectedTier, tg, t])

  const handleCancel = useCallback(() => {
    if (!loading) {
      setSelectedTier(null)
    }
  }, [loading])

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">{t('title')}</h1>

      {/* Language Switcher */}
      <div className="bg-bg-card rounded-xl border border-white/5 p-3">
        <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">
          {t('language.title')}
        </div>
        <div className="flex bg-bg-hover rounded-lg p-0.5">
          {supported.map((lang) => (
            <button
              key={lang}
              onClick={() => switchLanguage(lang)}
              className={`flex-1 py-1.5 text-[10px] font-semibold rounded-md transition-all ${
                currentLang === lang ? 'bg-accent-blue text-white' : 'text-text-muted'
              }`}
            >
              {t(`language.${lang}`)}
            </button>
          ))}
        </div>
      </div>

      <AlertSettings />

      <ReferralCard />

      {/* Subscription Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">{t('subscription.title')}</h2>

        {/* Manage Subscription link */}
        <button
          onClick={() => navigate('/subscription')}
          className="w-full flex items-center gap-3 bg-bg-card rounded-xl border border-white/5 p-3 hover:bg-bg-hover transition-colors text-left"
        >
          <div className="w-8 h-8 rounded-lg bg-accent-blue/10 flex items-center justify-center shrink-0">
            <svg className="w-4 h-4 text-accent-blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-text-primary text-xs font-medium">{t('subscription.manage')}</p>
            <p className="text-text-muted text-[10px]">{t('subscription.manageDesc')}</p>
          </div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-muted shrink-0">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>

        <p className="text-text-muted text-xs">
          {t('subscription.tapToPlan')}
        </p>

        {success && <SuccessMessage t={t} />}

        {error && (
          <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl px-3 py-2">
            <p className="text-accent-red text-xs">{error}</p>
          </div>
        )}

        {/* Pricing Cards — tappable */}
        <div className="space-y-2">
          {TIERS.map((tier) => (
            <button
              key={tier.key}
              onClick={() => handleTierClick(tier)}
              className={`w-full text-left bg-bg-card rounded-xl border p-3 active:scale-[0.98] transition-all ${
                tier.popular
                  ? 'border-accent-blue shadow-[0_0_12px_rgba(74,158,255,0.15)]'
                  : 'border-white/5 hover:border-white/15'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-text-primary font-semibold text-sm">{t(tier.nameKey)}</span>
                  {tier.popular && (
                    <span className="text-[8px] bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded-full font-semibold uppercase">
                      {t('subscription.bestValue')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {tier.savingsKey && (
                    <span className="text-[9px] text-accent-green font-semibold bg-accent-green/10 px-1.5 py-0.5 rounded-full">
                      {t(tier.savingsKey)}
                    </span>
                  )}
                  <svg className="w-4 h-4 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-text-primary text-lg font-bold">{tier.stars} {t('subscription.stars')}</span>
                <span className="text-text-muted text-xs">~{t(tier.usdKey)}</span>
              </div>
              <div className="text-text-muted text-[10px] mt-0.5">{t(tier.durationKey)} &middot; {t(tier.perMonthKey)}{t('subscription.perMonth')}</div>
            </button>
          ))}
        </div>

        {/* Features List */}
        <div className="bg-bg-card rounded-xl border border-white/5 p-3">
          <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">
            {t('subscription.whatYouGet')}
          </div>
          <ul className="space-y-1.5">
            {PREMIUM_FEATURE_KEYS.map((featKey) => (
              <li key={featKey} className="flex items-start gap-2 text-xs text-text-secondary">
                <svg className="w-3 h-3 text-accent-green mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {t(featKey)}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-text-muted text-[10px] text-center">
          {t('subscription.paymentVia')}
        </p>
      </div>

      {/* Confirm Modal */}
      <ConfirmModal
        tier={selectedTier}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        loading={loading}
        t={t}
      />
    </div>
  )
}
