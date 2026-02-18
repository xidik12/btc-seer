/**
 * Share text templates for all shareable content.
 * All include "Powered by BTC Seer" + referral tracking param.
 */

const BOT_USERNAME = 'BTCSeerBot'

function refLink(refCode) {
  return refCode
    ? `https://t.me/${BOT_USERNAME}?start=ref_${refCode}`
    : `https://t.me/${BOT_USERNAME}`
}

export function predictionShareText(prediction, refCode) {
  if (!prediction) return ''
  const dir = prediction.direction === 'bullish' ? '🟢 Bullish' : prediction.direction === 'bearish' ? '🔴 Bearish' : '🟡 Neutral'
  const conf = prediction.confidence ? ` (${Math.round(prediction.confidence)}%)` : ''
  const price = prediction.current_price ? ` | BTC $${Number(prediction.current_price).toLocaleString()}` : ''
  return `${prediction.timeframe?.toUpperCase() || ''} Prediction: ${dir}${conf}${price}\n\nPowered by BTC Seer\n${refLink(refCode)}`
}

export function signalShareText(signal, refCode) {
  if (!signal) return ''
  const action = (signal.action || '').replace('_', ' ').toUpperCase()
  const entry = signal.entry_price ? `Entry: $${Number(signal.entry_price).toLocaleString()}` : ''
  const tp = signal.target_price ? `TP: $${Number(signal.target_price).toLocaleString()}` : ''
  const sl = signal.stop_loss ? `SL: $${Number(signal.stop_loss).toLocaleString()}` : ''
  return `📈 Signal: ${action}\n${entry} | ${tp} | ${sl}\n\nPowered by BTC Seer\n${refLink(refCode)}`
}

export function arbitrageShareText(arb, refCode) {
  if (!arb) return ''
  const symbol = (arb.coin_id || 'BTC').toUpperCase().slice(0, 6)
  return `💱 ${symbol} Arbitrage: ${arb.net_profit_pct?.toFixed(2)}% profit\nBuy ${arb.buy_exchange} → Sell ${arb.sell_exchange}\n\nPowered by BTC Seer\n${refLink(refCode)}`
}

export function gameShareText(prediction, profile, refCode) {
  if (!profile) return ''
  const streak = profile.current_streak || 0
  const points = profile.total_points || 0
  const acc = profile.accuracy_pct ? `${Math.round(profile.accuracy_pct)}%` : '0%'
  const dir = prediction?.direction === 'up' ? '🟢 UP' : prediction?.direction === 'down' ? '🔴 DOWN' : ''
  return `🎮 BTC Prediction Game\n${dir ? `My pick: ${dir}\n` : ''}🔥 Streak: ${streak} | Points: ${points} | Accuracy: ${acc}\n\nPowered by BTC Seer\n${refLink(refCode)}`
}

export function coinShareText(coin, refCode) {
  if (!coin) return ''
  const name = coin.name || coin.symbol || ''
  const price = coin.price_usd ? `$${Number(coin.price_usd).toLocaleString()}` : ''
  const change = coin.change_24h != null ? ` (${coin.change_24h > 0 ? '+' : ''}${coin.change_24h.toFixed(1)}% 24h)` : ''
  return `${name}: ${price}${change}\n\nPowered by BTC Seer\n${refLink(refCode)}`
}
