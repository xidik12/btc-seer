import { useTranslation } from 'react-i18next'

const SOURCE_LABELS = {
  binance: 'Binance',
  coingecko: 'CoinGecko',
  alphavantage: 'Alpha Vantage',
  yahoo: 'Yahoo Finance',
  fred: 'FRED',
  blockchain: 'Blockchain.com',
  mempool: 'Mempool.space',
  blockchair: 'Blockchair',
  feargreed: 'Fear & Greed',
  coinglass: 'Coinglass',
  defillama: 'DeFi Llama',
  deribit: 'Deribit',
  cryptopanic: 'CryptoPanic',
  reddit: 'Reddit',
  rss: 'RSS Feeds',
  ols: 'OLS Regression',
  ta: 'Technical Analysis',
  ai: 'AI Models',
}

export default function DataSourceFooter({ sources = [] }) {
  const { t } = useTranslation('common')

  if (!sources.length) return null

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-3.5 h-3.5 text-accent-blue/60 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
        <span className="text-text-secondary text-xs font-semibold">{t('dataSources.title')}</span>
      </div>
      <p className="text-text-muted text-[10px] mb-2.5">{t('dataSources.liveData')}</p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((key) => (
          <span
            key={key}
            className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-text-muted border border-white/5 font-medium"
          >
            {t(`dataSources.${key}`, SOURCE_LABELS[key] || key)}
          </span>
        ))}
      </div>
    </div>
  )
}
