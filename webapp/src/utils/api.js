const API_BASE = import.meta.env.VITE_API_URL || '/api'

// ── Client-side TTL cache + in-flight dedup ──
const _cache = new Map()
const _inflight = new Map()

function cachedFetch(endpoint, ttl, options = {}) {
  const key = endpoint
  // Only cache GET requests (no body, no method or method=GET)
  if (options.method && options.method !== 'GET') {
    return fetchAPI(endpoint, options)
  }

  // Check cache
  const entry = _cache.get(key)
  if (entry && Date.now() < entry.expiry) {
    return Promise.resolve(entry.data)
  }

  // Deduplicate in-flight requests
  if (_inflight.has(key)) {
    return _inflight.get(key)
  }

  const promise = fetchAPI(endpoint, options)
    .then((data) => {
      _cache.set(key, { data, expiry: Date.now() + ttl })
      _inflight.delete(key)
      return data
    })
    .catch((err) => {
      _inflight.delete(key)
      throw err
    })

  _inflight.set(key, promise)
  return promise
}

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const { headers: extraHeaders, ...rest } = options
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
    ...rest,
  })
  if (!res.ok) {
    let detail = `API error: ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// TTL constants (ms)
const T15 = 15_000   // 15s — fast-changing (price)
const T30 = 30_000   // 30s — predictions, signals, indicators
const T60 = 60_000   // 60s — news, events, liquidations
const T120 = 120_000 // 2min — macro, onchain, supply, dominance, power law
const T300 = 300_000 // 5min — fear & greed, supply

export const api = {
  // Predictions
  getCurrentPredictions: () => cachedFetch('/predictions/current', T30),
  getQuantPrediction: () => cachedFetch('/predictions/quant', T30),
  getQuantHistory: (days = 7) => cachedFetch(`/predictions/quant/history?days=${days}`, T60),
  getPredictionHistory: (timeframe = '1h', days = 7) =>
    cachedFetch(`/predictions/history?timeframe=${timeframe}&days=${days}`, T60),

  // Signals
  getCurrentSignals: () => cachedFetch('/signals/current', T30),
  getSignalHistory: (timeframe = '1h', days = 7) =>
    cachedFetch(`/signals/history?timeframe=${timeframe}&days=${days}`, T60),

  // News
  getLatestNews: (limit = 20) => cachedFetch(`/news/latest?limit=${limit}`, T60),
  getNewsSentiment: (hours = 24) => cachedFetch(`/news/sentiment?hours=${hours}`, T60),

  // Market
  getCurrentPrice: () => cachedFetch('/market/price', T15),
  getPriceStats: (timeframe = '1d') => cachedFetch(`/market/stats?timeframe=${timeframe}`, T15),
  getCandles: (hours = 168) => cachedFetch(`/market/candles?hours=${hours}`, T30),
  getIndicators: () => cachedFetch('/market/indicators', T30),
  getMacroData: () => cachedFetch('/market/macro', T120),
  getOnchainData: () => cachedFetch('/market/onchain', T120),
  getFundingHistory: (hours = 168) => cachedFetch(`/market/funding?hours=${hours}`, T60),
  getDominanceData: (days = 30) => cachedFetch(`/market/dominance?days=${days}`, T120),
  getBtcSupply: () => cachedFetch('/market/supply', T300),

  // Influencers
  getInfluencerTweets: (limit = 20, category = null) => {
    let url = `/influencers/latest?limit=${limit}`
    if (category) url += `&category=${category}`
    return cachedFetch(url, T60)
  },
  getInfluencerSentiment: (hours = 24) => cachedFetch(`/influencers/sentiment?hours=${hours}`, T60),
  getTopInfluencers: (hours = 24) => cachedFetch(`/influencers/top-influencers?hours=${hours}`, T60),

  // History
  getAccuracy: (days = 30) => cachedFetch(`/history/accuracy?days=${days}`, T120),

  // Power Law
  getPowerLawCurrent: () => cachedFetch('/powerlaw/current', T120),
  getPowerLawHistorical: (days = 365) => cachedFetch(`/powerlaw/historical?days=${days}`, T120),

  // Liquidations
  getLiquidationMap: () => cachedFetch('/liquidations/map', T60),
  getLiquidationLevels: () => cachedFetch('/liquidations/levels', T60),
  getLiquidationStats: () => cachedFetch('/liquidations/stats', T60),

  // Events
  getRecentEvents: (hours = 24) => cachedFetch(`/events/recent?hours=${hours}`, T60),
  getEventCategoryStats: () => cachedFetch('/events/category-stats', T60),
  getEventMemory: () => cachedFetch('/events/memory', T120),

  // Advisor (user-specific, no cache)
  getPortfolio: (telegramId) => fetchAPI(`/advisor/portfolio/${telegramId}`),
  getActiveTrades: (telegramId) => fetchAPI(`/advisor/trades/${telegramId}`),
  getTradeHistory: (telegramId) => fetchAPI(`/advisor/trades/${telegramId}/history`),
  openTrade: (tradeId) => fetchAPI(`/advisor/trades/${tradeId}/opened`, { method: 'POST' }),
  closeTrade: (tradeId, exitPrice, reason = 'manual_close') =>
    fetchAPI(`/advisor/trades/${tradeId}/close`, {
      method: 'POST',
      body: JSON.stringify({ exit_price: exitPrice, reason }),
    }),

  // Mock/Paper Trading (user-specific, no cache)
  getMockTrades: (telegramId) => fetchAPI(`/advisor/trades/${telegramId}?mock=true`),
  getMockHistory: (telegramId) => fetchAPI(`/advisor/trades/${telegramId}/history?mock=true`),
  createMockTrade: (telegramId, trade) =>
    fetchAPI(`/advisor/trades/${telegramId}/mock`, {
      method: 'POST',
      body: JSON.stringify(trade),
    }),

  // Admin (no cache — needs fresh data)
  getAdminStats: (initData) => fetchAPI('/admin/stats', { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminUsers: (initData, page = 1, search = '') =>
    fetchAPI(`/admin/users?page=${page}&search=${encodeURIComponent(search)}`, { headers: { 'X-Telegram-Init-Data': initData } }),
  adminBanUser: (initData, telegramId, reason) =>
    fetchAPI(`/admin/users/${telegramId}/ban`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify({ reason }),
    }),
  adminUnbanUser: (initData, telegramId) =>
    fetchAPI(`/admin/users/${telegramId}/unban`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
    }),
  adminGrantPremium: (initData, telegramId, days) =>
    fetchAPI(`/admin/users/${telegramId}/grant-premium`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': initData },
      body: JSON.stringify({ days }),
    }),
  getAdminPredictions: (initData, limit = 50) =>
    fetchAPI(`/admin/predictions?limit=${limit}`, { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminSystem: (initData) => fetchAPI('/admin/system', { headers: { 'X-Telegram-Init-Data': initData } }),
  getAdminBotStatus: (initData) => fetchAPI('/admin/bot-status', { headers: { 'X-Telegram-Init-Data': initData } }),

  // Auth (no cache)
  registerUser: (initData) => fetchAPI('/auth/register', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  getCurrentUser: (initData) => fetchAPI('/auth/me', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Alert Preferences (no cache — user-specific)
  getAlertPreferences: (initData) => fetchAPI('/auth/alerts/preferences', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),
  updateAlertPreferences: (initData, subscribed, alertInterval) => fetchAPI('/auth/alerts/preferences', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': initData },
    body: JSON.stringify({ subscribed, alert_interval: alertInterval }),
  }),

  // Subscription (no cache)
  createInvoice: (tier) => fetchAPI(`/subscription/create-invoice?tier=${tier}`),
  getSubscriptionStatus: (initData) => fetchAPI('/subscription/status', {
    headers: { 'X-Telegram-Init-Data': initData },
  }),

  // Fear & Greed
  getFearGreed: (days = 30) => cachedFetch(`/market/fear-greed?days=${days}`, T300),

  // Indicator History
  getIndicatorHistory: () => cachedFetch('/market/indicator-history', T60),

  // Public API (no cache)
  getApiUsage: (apiKey) => fetchAPI('/v1/usage', { headers: { 'X-API-Key': apiKey } }),

  // Elliott Wave
  getElliottWaveCurrent: (timeframe = '4h') => cachedFetch(`/elliott-wave/current?timeframe=${timeframe}`, T120),
  getElliottWaveHistorical: (days = 90, timeframe = '4h') => cachedFetch(`/elliott-wave/historical?days=${days}&timeframe=${timeframe}`, T120),

  // Coins
  getTrackedCoins: () => cachedFetch('/coins/tracked', T60),
  getCoinDetail: (coinId) => cachedFetch(`/coins/${coinId}/detail`, T30),
  getCoinChart: (coinId, days = 7) => cachedFetch(`/coins/${coinId}/chart?days=${days}`, T60),
  searchCoins: (query) => fetchAPI(`/coins/search?q=${encodeURIComponent(query)}`),
  searchCoinByAddress: (address) => fetchAPI('/coins/search-address', {
    method: 'POST',
    body: JSON.stringify({ address }),
  }),
  getCoinReport: (address) => cachedFetch(`/coins/report/${address}`, T120),
}
