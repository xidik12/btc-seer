/**
 * Shared bot config — resolves bot_username from the backend API.
 * Caches the result so only one fetch happens per session.
 */
import { api } from './api'

let _botUsername = null
let _promise = null

export async function getBotUsername() {
  if (_botUsername) return _botUsername
  if (!_promise) {
    _promise = api.getPublicConfig()
      .then((cfg) => { _botUsername = cfg.bot_username || 'BTC_Seer_Bot'; return _botUsername })
      .catch(() => { _botUsername = 'BTC_Seer_Bot'; return _botUsername })
  }
  return _promise
}

/** Synchronous getter — returns cached value or fallback. */
export function getBotUsernameSync() {
  return _botUsername || 'BTC_Seer_Bot'
}

// Pre-fetch on module load
getBotUsername()
