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
  getCandles: (hours = 168) => fetchAPI(`/market/candles?hours=${hours}`),
  getMacroData: () => fetchAPI('/market/macro'),
  getOnchainData: () => fetchAPI('/market/onchain'),

  // History
  getAccuracy: (days = 30) => fetchAPI(`/history/accuracy?days=${days}`),
}
