import i18n from '../i18n'

const LOCALE_MAP = { en: 'en-US', ru: 'ru-RU', zh: 'zh-CN' }

function getLocale() {
  return LOCALE_MAP[i18n.language] || 'en-US'
}

function isBadNumber(n) {
  return n == null || !isFinite(n)
}

export function formatPrice(price) {
  if (isBadNumber(price) && price !== 0) return '--'
  return new Intl.NumberFormat(getLocale(), {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatPricePrecise(price) {
  if (isBadNumber(price) && price !== 0) return '--'
  return new Intl.NumberFormat(getLocale(), {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

export function formatPercent(pct) {
  if (isBadNumber(pct) && pct !== 0) return '--'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function formatNumber(num) {
  if (isBadNumber(num) && num !== 0) return '--'
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`
  return num.toFixed(0)
}

// Ensure ISO strings from the backend (which are UTC but may lack Z) are parsed as UTC
function toUTC(isoString) {
  if (!isoString) return null
  // If the string has no timezone info (no Z, no +/-), append Z for UTC
  if (!/[Z+\-]/.test(isoString.slice(-6))) return isoString + 'Z'
  return isoString
}

export function formatTime(isoString) {
  if (!isoString) return '--'
  const date = new Date(toUTC(isoString))
  return date.toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(isoString) {
  if (!isoString) return '--'
  const date = new Date(toUTC(isoString))
  return date.toLocaleDateString(getLocale(), { month: 'short', day: 'numeric' })
}

export function formatTimeAgo(isoString) {
  if (!isoString) return '--'
  const seconds = Math.floor((Date.now() - new Date(toUTC(isoString))) / 1000)
  if (seconds < 0) return i18n.t('time.justNow')
  if (seconds < 60) return i18n.t('time.justNow')
  if (seconds < 3600) return i18n.t('time.mAgo', { count: Math.floor(seconds / 60) })
  if (seconds < 86400) return i18n.t('time.hAgo', { count: Math.floor(seconds / 3600) })
  return i18n.t('time.dAgo', { count: Math.floor(seconds / 86400) })
}

export function getDirectionColor(direction) {
  if (direction === 'bullish') return 'text-accent-green'
  if (direction === 'bearish') return 'text-accent-red'
  return 'text-accent-yellow'
}

export function getActionColor(action) {
  if (action?.includes('buy')) return 'text-accent-green'
  if (action?.includes('sell')) return 'text-accent-red'
  return 'text-accent-yellow'
}

export function getActionBg(action) {
  if (action?.includes('buy')) return 'bg-accent-green/10 border-accent-green/30'
  if (action?.includes('sell')) return 'bg-accent-red/10 border-accent-red/30'
  return 'bg-accent-yellow/10 border-accent-yellow/30'
}

export function formatCoinPrice(price) {
  if (isBadNumber(price) && price !== 0) return '--'
  const locale = getLocale()
  if (price >= 1000) return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(price)
  if (price >= 1) return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(price)
  if (price >= 0.01) return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(price)
  return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', minimumFractionDigits: 6, maximumFractionDigits: 6 }).format(price)
}

export function formatMarketCap(value) {
  if (isBadNumber(value) && value !== 0) return '--'
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export function safeFixed(val, digits = 2, fallback = '--') {
  if (val == null || !isFinite(val)) return fallback
  return val.toFixed(digits)
}

export function formatSupply(value, symbol) {
  if (isBadNumber(value) && value !== 0) return '--'
  const formatted = formatNumber(value)
  return symbol ? `${formatted} ${symbol}` : formatted
}
