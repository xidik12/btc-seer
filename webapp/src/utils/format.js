export function formatPrice(price) {
  if (!price && price !== 0) return '--'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatPricePrecise(price) {
  if (!price && price !== 0) return '--'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

export function formatPercent(pct) {
  if (!pct && pct !== 0) return '--'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function formatNumber(num) {
  if (!num && num !== 0) return '--'
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
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(isoString) {
  if (!isoString) return '--'
  const date = new Date(toUTC(isoString))
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatTimeAgo(isoString) {
  if (!isoString) return '--'
  const seconds = Math.floor((Date.now() - new Date(toUTC(isoString))) / 1000)
  if (seconds < 0) return 'just now'
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
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
