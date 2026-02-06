import { useState } from 'react'

const INTERVALS = [
  { value: '1h', label: '1 Hour', description: 'Frequent updates' },
  { value: '4h', label: '4 Hours', description: 'Balanced frequency' },
  { value: '24h', label: '24 Hours', description: 'Daily digest' },
]

export default function AlertSettings() {
  const [selectedInterval, setSelectedInterval] = useState('4h')
  const [subscribed, setSubscribed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSave = async () => {
    setSaving(true)
    // Simulate API call delay
    await new Promise((resolve) => setTimeout(resolve, 600))
    setSaving(false)

    if (subscribed) {
      showToast(`Alerts set to ${selectedInterval} interval`)
    } else {
      showToast('Alerts unsubscribed', 'info')
    }
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up relative">
      <h3 className="text-text-primary font-semibold text-sm mb-1">
        Alert Settings
      </h3>
      <p className="text-text-muted text-xs mb-4">
        Configure prediction alert notifications
      </p>

      {/* Subscribe toggle */}
      <div className="flex items-center justify-between mb-4 bg-bg-secondary rounded-xl p-3">
        <div>
          <p className="text-text-primary text-sm font-medium">
            Enable Alerts
          </p>
          <p className="text-text-muted text-xs mt-0.5">
            Receive prediction notifications
          </p>
        </div>
        <button
          onClick={() => setSubscribed(!subscribed)}
          className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
            subscribed ? 'bg-accent-green' : 'bg-bg-hover'
          }`}
          aria-label={subscribed ? 'Disable alerts' : 'Enable alerts'}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 ${
              subscribed ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Interval selection */}
      <div className={`space-y-2 mb-4 transition-opacity ${subscribed ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
        <p className="text-text-secondary text-xs font-medium mb-2">
          Alert Interval
        </p>
        {INTERVALS.map((interval) => {
          const isSelected = selectedInterval === interval.value
          return (
            <button
              key={interval.value}
              onClick={() => setSelectedInterval(interval.value)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-accent-blue/10 border-accent-blue/40'
                  : 'bg-bg-secondary border-transparent hover:border-text-muted/20'
              }`}
            >
              {/* Radio circle */}
              <div
                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                  isSelected
                    ? 'border-accent-blue'
                    : 'border-text-muted'
                }`}
              >
                {isSelected && (
                  <div className="w-2 h-2 rounded-full bg-accent-blue" />
                )}
              </div>

              {/* Label */}
              <div className="text-left">
                <p
                  className={`text-sm font-medium ${
                    isSelected ? 'text-text-primary' : 'text-text-secondary'
                  }`}
                >
                  {interval.label}
                </p>
                <p className="text-text-muted text-xs">
                  {interval.description}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all ${
          saving
            ? 'bg-accent-blue/50 text-white/50 cursor-not-allowed'
            : 'bg-accent-blue text-white active:scale-[0.98]'
        }`}
      >
        {saving ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Saving...
          </span>
        ) : (
          'Save Preferences'
        )}
      </button>

      {/* Toast notification */}
      {toast && (
        <div
          className={`absolute bottom-[-52px] left-0 right-0 mx-4 px-4 py-2.5 rounded-xl text-sm font-medium text-center shadow-lg slide-up ${
            toast.type === 'success'
              ? 'bg-accent-green/15 text-accent-green border border-accent-green/30'
              : 'bg-accent-blue/15 text-accent-blue border border-accent-blue/30'
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  )
}
