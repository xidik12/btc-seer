import AlertSettings from '../components/AlertSettings'

const TIERS = [
  {
    name: 'Monthly',
    duration: '30 days',
    stars: 500,
    usd: '$9.99',
    savings: null,
    popular: false,
  },
  {
    name: '3 Months',
    duration: '90 days',
    stars: 1250,
    usd: '$24.99',
    savings: 'Save 17%',
    popular: true,
  },
  {
    name: 'Yearly',
    duration: '365 days',
    stars: 4500,
    usd: '$89.99',
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

export default function Settings() {
  return (
    <div className="px-4 pt-4 space-y-4 pb-20">
      <h1 className="text-lg font-bold">Settings</h1>

      <AlertSettings />

      {/* Subscription Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Premium Plans</h2>
        <p className="text-text-muted text-xs">
          Unlock all BTC Seer features. Subscribe via the Telegram bot with <code className="text-accent-blue">/subscribe</code>.
        </p>

        {/* Pricing Cards */}
        <div className="space-y-2">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`bg-bg-card rounded-xl border p-3 ${
                tier.popular ? 'border-accent-blue' : 'border-white/5'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-text-primary font-semibold text-sm">{tier.name}</span>
                  {tier.popular && (
                    <span className="text-[8px] bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded-full font-semibold uppercase">
                      Popular
                    </span>
                  )}
                </div>
                {tier.savings && (
                  <span className="text-[9px] text-accent-green font-semibold">{tier.savings}</span>
                )}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-text-primary text-lg font-bold">{tier.stars} Stars</span>
                <span className="text-text-muted text-xs">~{tier.usd}</span>
              </div>
              <div className="text-text-muted text-[10px] mt-0.5">{tier.duration}</div>
            </div>
          ))}
        </div>

        {/* Features List */}
        <div className="bg-bg-card rounded-xl border border-white/5 p-3">
          <div className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">
            Premium Features
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
          Open the Telegram bot and use <code className="text-accent-blue">/subscribe</code> to purchase.
          Payment via Telegram Stars.
        </p>
      </div>
    </div>
  )
}
