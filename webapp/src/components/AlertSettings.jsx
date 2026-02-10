import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'

export default function AlertSettings() {
  const { t } = useTranslation('settings')
  const { tg } = useTelegram()
  const [selectedInterval, setSelectedInterval] = useState('4h')
  const [subscribed, setSubscribed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [dirty, setDirty] = useState(false)

  const INTERVALS = [
    { value: '1h', label: t('alerts.intervals.1h', '1 Hour'), description: t('alerts.intervals.1hDesc', 'Every hour') },
    { value: '4h', label: t('alerts.intervals.4h', '4 Hours'), description: t('alerts.intervals.4hDesc', 'Every 4 hours') },
    { value: '24h', label: t('alerts.intervals.24h', '24 Hours'), description: t('alerts.intervals.24hDesc', 'Once daily') },
  ]

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  // Load saved preferences from backend
  useEffect(() => {
    if (!tg?.initData) {
      setLoading(false)
      return
    }
    api.getAlertPreferences(tg.initData)
      .then((data) => {
        setSubscribed(data.subscribed)
        setSelectedInterval(data.alert_interval)
      })
      .catch(() => {
        // Defaults are fine — user may not be registered yet
      })
      .finally(() => setLoading(false))
  }, [tg])

  const handleToggle = useCallback(() => {
    setSubscribed((prev) => !prev)
    setDirty(true)
  }, [])

  const handleIntervalChange = useCallback((value) => {
    setSelectedInterval(value)
    setDirty(true)
  }, [])

  const handleSave = useCallback(async () => {
    if (!tg?.initData) {
      showToast(t('alerts.openInTelegram', 'Open in Telegram to save'), 'error')
      return
    }
    setSaving(true)
    try {
      await api.updateAlertPreferences(tg.initData, subscribed, selectedInterval)
      setDirty(false)
      if (subscribed) {
        showToast(t('alerts.alertsSet', 'Alerts set to {{interval}} interval', { interval: selectedInterval }))
      } else {
        showToast(t('alerts.alertsDisabled', 'Alerts disabled'), 'info')
      }
    } catch {
      showToast(t('alerts.saveFailed'), 'error')
    } finally {
      setSaving(false)
    }
  }, [tg, subscribed, selectedInterval, t])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-5 w-32 bg-bg-hover rounded mb-4" />
        <div className="h-12 bg-bg-hover rounded mb-3" />
        <div className="h-10 bg-bg-hover rounded" />
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up relative">
      <h3 className="text-text-primary font-semibold text-sm mb-1">
        {t('alerts.title')}
      </h3>
      <p className="text-text-muted text-xs mb-4">
        {t('alerts.subtitle', 'Get prediction alerts via Telegram')}
      </p>

      {/* Subscribe toggle */}
      <div className="flex items-center justify-between mb-4 bg-bg-secondary rounded-xl p-3">
        <div>
          <p className="text-text-primary text-sm font-medium">
            {t('alerts.enable')}
          </p>
          <p className="text-text-muted text-xs mt-0.5">
            {t('alerts.enableDesc', 'Receive prediction notifications')}
          </p>
        </div>
        <button
          onClick={handleToggle}
          className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
            subscribed ? 'bg-accent-green' : 'bg-bg-hover'
          }`}
          aria-label={subscribed ? t('alerts.disableLabel', 'Disable alerts') : t('alerts.enableLabel', 'Enable alerts')}
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
          {t('alerts.interval')}
        </p>
        {INTERVALS.map((interval) => {
          const isSelected = selectedInterval === interval.value
          return (
            <button
              key={interval.value}
              onClick={() => handleIntervalChange(interval.value)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-accent-blue/10 border-accent-blue/40'
                  : 'bg-bg-secondary border-transparent hover:border-text-muted/20'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                  isSelected ? 'border-accent-blue' : 'border-text-muted'
                }`}
              >
                {isSelected && (
                  <div className="w-2 h-2 rounded-full bg-accent-blue" />
                )}
              </div>
              <div className="text-left">
                <p className={`text-sm font-medium ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
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
        disabled={saving || !dirty}
        className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all ${
          saving || !dirty
            ? 'bg-accent-blue/30 text-white/40 cursor-not-allowed'
            : 'bg-accent-blue text-white active:scale-[0.98]'
        }`}
      >
        {saving ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {t('alerts.saving', 'Saving...')}
          </span>
        ) : (
          t('alerts.savePreferences', 'Save Preferences')
        )}
      </button>

      {/* Toast notification */}
      {toast && (
        <div
          className={`absolute bottom-[-52px] left-0 right-0 mx-4 px-4 py-2.5 rounded-xl text-sm font-medium text-center shadow-lg slide-up ${
            toast.type === 'error'
              ? 'bg-accent-red/15 text-accent-red border border-accent-red/30'
              : toast.type === 'info'
                ? 'bg-accent-blue/15 text-accent-blue border border-accent-blue/30'
                : 'bg-accent-green/15 text-accent-green border border-accent-green/30'
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  )
}
