import { useState, useCallback } from 'react'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'
import AlertSettings from '../components/AlertSettings'

const TIERS = [
  {
    key: 'monthly',
    name: 'Monthly',
    duration: '30 days',
    stars: 500,
    usd: '$9.99',
    perMonth: '$9.99/mo',
    savings: null,
    popular: false,
  },
  {
    key: 'quarterly',
    name: '3 Months',
    duration: '90 days',
    stars: 1250,
    usd: '$24.99',
    perMonth: '$8.33/mo',
    savings: 'Save 17%',
    popular: true,
  },
  {
    key: 'yearly',
    name: 'Yearly',
    duration: '365 days',
    stars: 4500,
    usd: '$89.99',
    perMonth: '$7.50/mo',
    savings: 'Save 25%',
    popular: false,
  },
]

const PREMIUM_FEATURES = [
  'AI-powered price predictions (1h, 4h, 24h)',
  'Full trading signals with entry/target/SL',
  'Trading Advisor with auto-sized plans',
  'Real-time news sentiment analysis',
  'Custom price alerts',
  'On-chain & macro analytics',
  'Elliott Wave analysis',
  'Power Law deviation tracking',
]

function ConfirmModal({ tier, onConfirm, onCancel, loading }) {
  if (!tier) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-6" onClick={onCancel}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-bg-card border border-white/10 rounded-2xl p-5 w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-center mb-4">
          <div className="text-2xl mb-2">&#11088;</div>
          <h3 className="text-text-primary font-bold text-base">Subscribe to Premium</h3>
          <p className="text-text-muted text-xs mt-1">
            {tier.name} plan &middot; {tier.duration}
          </p>
        </div>

        <div className="bg-bg-secondary rounded-xl p-3 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary text-sm font-medium">{tier.name}</span>
            <div className="text-right">
              <span className="text-text-primary font-bold text-lg">{tier.stars}</span>
              <span className="text-text-muted text-xs ml-1">Stars</span>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-text-muted text-[10px]">{tier.perMonth}</span>
            <span className="text-text-muted text-[10px]">~{tier.usd}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-text-muted bg-bg-secondary active:scale-95 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl text-sm font-bold text-white bg-accent-blue active:scale-95 transition-all disabled:opacity-50"
          >
            {loading ? 'Processing...' : 'Subscribe'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SuccessMessage() {
  return (
    <div className="bg-accent-green/10 border border-accent-green/30 rounded-xl p-4 text-center">
      <div className="text-xl mb-1">&#10003;</div>
      <p className="text-accent-green font-semibold text-sm">Payment Successful!</p>
      <p className="text-text-muted text-xs mt-1">Your Premium access is now active.</p>
    </div>
  )
}

export default function Settings() {
  const { tg } = useTelegram()
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
            setError('Payment failed. Please try again.')
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
      setError('Could not start payment. Please try again later.')
      setSelectedTier(null)
      setLoading(false)
    }
  }, [selectedTier, tg])

  const handleCancel = useCallback(() => {
    if (!loading) {
      setSelectedTier(null)
    }
  }, [loading])

  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Settings</h1>

      <AlertSettings />

      {/* Subscription Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Premium Plans</h2>
        <p className="text-text-muted text-xs">
          Tap a plan to subscribe instantly via Telegram Stars.
        </p>

        {success && <SuccessMessage />}

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
                  <span className="text-text-primary font-semibold text-sm">{tier.name}</span>
                  {tier.popular && (
                    <span className="text-[8px] bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded-full font-semibold uppercase">
                      Best Value
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {tier.savings && (
                    <span className="text-[9px] text-accent-green font-semibold bg-accent-green/10 px-1.5 py-0.5 rounded-full">
                      {tier.savings}
                    </span>
                  )}
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-text-muted">
                    <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-text-primary text-lg font-bold">{tier.stars} Stars</span>
                <span className="text-text-muted text-xs">~{tier.usd}</span>
              </div>
              <div className="text-text-muted text-[10px] mt-0.5">{tier.duration} &middot; {tier.perMonth}</div>
            </button>
          ))}
        </div>

        {/* Features List */}
        <div className="bg-bg-card rounded-xl border border-white/5 p-3">
          <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">
            What you get
          </div>
          <ul className="space-y-1.5">
            {PREMIUM_FEATURES.map((feat) => (
              <li key={feat} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="text-accent-green mt-0.5 text-[10px]">&#10003;</span>
                {feat}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-text-muted text-[10px] text-center">
          Payment via Telegram Stars. Secure & instant.
        </p>
      </div>

      {/* Confirm Modal */}
      <ConfirmModal
        tier={selectedTier}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        loading={loading}
      />
    </div>
  )
}
