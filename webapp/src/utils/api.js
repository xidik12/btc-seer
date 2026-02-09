const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  // Predictions
  getCurrentPredictions: () => fetchAPI('/predictions/current'),
  getQuantPrediction: () => fetchAPI('/predictions/quant'),
  getQuantHistory: (days = 7) => fetchAPI(`/predictions/quant/history?days=${days}`),
  getPredictionHistory: (timeframe = '1h', days = 7) =>
    fetchAPI(`/predictions/history?timeframe=${timeframe}&days=${days}`),

  // Signals
  getCurrentSignals: () => fetchAPI('/signals/current'),
  getSignalHistory: (timeframe = '1h', days = 7) =>
    fetchAPI(`/signals/history?timeframe=${timeframe}&days=${days}`),

  // News
  getLatestNews: (limit = 20) => fetchAPI(`/news/latest?limit=${limit}`),
  getNewsSentiment: (hours = 24) => fetchAPI(`/news/sentiment?hours=${hours}`),

  // Market
  getCurrentPrice: () => fetchAPI('/market/price'),
  getPriceStats: (timeframe = '1d') => fetchAPI(`/market/stats?timeframe=${timeframe}`),
  getCandles: (hours = 168) => fetchAPI(`/market/candles?hours=${hours}`),
  getIndicators: () => fetchAPI('/market/indicators'),
  getMacroData: () => fetchAPI('/market/macro'),
  getOnchainData: () => fetchAPI('/market/onchain'),

  // Influencers
  getInfluencerTweets: (limit = 20, category = null) => {
    let url = `/influencers/latest?limit=${limit}`
    if (category) url += `&category=${category}`
    return fetchAPI(url)
  },
  getInfluencerSentiment: (hours = 24) => fetchAPI(`/influencers/sentiment?hours=${hours}`),
  getTopInfluencers: (hours = 24) => fetchAPI(`/influencers/top-influencers?hours=${hours}`),

  // History
  getAccuracy: (days = 30) => fetchAPI(`/history/accuracy?days=${days}`),

  // Power Law
  getPowerLawCurrent: () => fetchAPI('/powerlaw/current'),
  getPowerLawHistorical: (days = 365) => fetchAPI(`/powerlaw/historical?days=${days}`),

  // Public API
  getApiUsage: (apiKey) => fetchAPI('/v1/usage', { headers: { 'X-API-Key': apiKey } }),
}
