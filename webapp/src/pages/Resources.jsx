import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'

const CATEGORIES = [
  { key: 'exchanges', labelKey: 'resources:categories.exchanges' },
  { key: 'analysis', labelKey: 'resources:categories.analysis' },
  { key: 'onchain', labelKey: 'resources:categories.onChain' },
  { key: 'portfolio', labelKey: 'resources:categories.portfolio' },
  { key: 'bots', labelKey: 'resources:categories.bots' },
  { key: 'learn', labelKey: 'resources:categories.learn' },
]

const RESOURCES = {
  exchanges: {
    title: 'EXCHANGES & TRADING PLATFORMS',
    description: 'Where to trade. Ranked by experts for reliability, fees, and features.',
    items: [
      {
        name: 'Binance',
        url: 'https://binance.com',
        tier: 'Pro',
        tags: ['Low fees', 'Deep liquidity', 'Futures'],
        desc: '#1 by volume worldwide. Full trading suite with leverage, automation, and 600+ pairs. Best for active traders.',
      },
      {
        name: 'Coinbase',
        url: 'https://coinbase.com',
        tier: 'Beginner',
        tags: ['Regulated', 'Easy UI', 'Staking'],
        desc: 'Best for beginners. US-regulated, insured, simple buy/sell. Coinbase Advanced for experienced traders.',
      },
      {
        name: 'Kraken',
        url: 'https://kraken.com',
        tier: 'Pro',
        tags: ['Reliable', 'Low fees', 'Futures'],
        desc: 'Rock-solid reliability since 2011. Kraken Pro offers institutional-grade features. Great for day traders.',
      },
      {
        name: 'Bybit',
        url: 'https://bybit.com',
        tier: 'Pro',
        tags: ['Derivatives', 'Copy trading', 'High leverage'],
        desc: 'Top derivatives exchange. Copy trading, advanced order types, and deep liquidity for non-US users.',
      },
      {
        name: 'OKX',
        url: 'https://okx.com',
        tier: 'Pro',
        tags: ['DeFi', 'Web3 wallet', 'DEX aggregator'],
        desc: 'CEX + DEX hybrid. Built-in Web3 wallet, DEX aggregator, and NFT marketplace. Full ecosystem.',
      },
      {
        name: 'BYDFi',
        url: 'https://bydfi.com',
        tier: 'All',
        tags: ['CEX+DEX', 'Copy trading', 'Grid bots'],
        desc: 'Most feature-rich for 2026. CEX+DEX, copy trading, grid bots, broad asset support. Active trader favorite.',
      },
    ],
  },
  analysis: {
    title: 'CHARTING & ANALYSIS TOOLS',
    description: 'Technical analysis, charting, and market research platforms.',
    items: [
      {
        name: 'TradingView',
        url: 'https://tradingview.com',
        tier: 'Essential',
        tags: ['Charts', '100+ indicators', 'Community'],
        desc: 'The #1 charting platform. 100+ indicators, community-shared strategies, real-time data. Used by 90% of traders.',
      },
      {
        name: 'CoinGlass',
        url: 'https://coinglass.com',
        tier: 'Essential',
        tags: ['Liquidations', 'OI', 'Funding rates'],
        desc: 'Best for derivatives data. Liquidation heatmaps, open interest, funding rates, order flow, and whale tracking.',
      },
      {
        name: 'CoinMarketCap',
        url: 'https://coinmarketcap.com',
        tier: 'Beginner',
        tags: ['Prices', 'Rankings', 'Fear & Greed'],
        desc: 'Go-to for market overview. Price tracking, market cap rankings, Fear & Greed index, crypto calendar.',
      },
      {
        name: 'TrendSpider',
        url: 'https://trendspider.com',
        tier: 'Pro',
        tags: ['Auto trendlines', 'Backtesting', 'Alerts'],
        desc: 'AI-powered technical analysis. Automated trendline detection, multi-timeframe analysis, strategy backtesting.',
      },
      {
        name: 'Coinalyze',
        url: 'https://coinalyze.net',
        tier: 'Pro',
        tags: ['Futures data', 'OI', 'Aggregated'],
        desc: 'Aggregated futures data across all major exchanges. Open interest, funding, volume, and basis analytics.',
      },
      {
        name: 'Bitcoin Magazine Pro',
        url: 'https://bitcoinmagazinepro.com',
        tier: 'All',
        tags: ['BTC charts', 'Cycle analysis', 'MVRV'],
        desc: 'BTC-specific charts: MVRV Z-Score, Pi Cycle, Puell Multiple, Stock-to-Flow. Best Bitcoin cycle tools.',
      },
    ],
  },
  onchain: {
    title: 'ON-CHAIN ANALYTICS',
    description: 'Blockchain data, whale tracking, and smart money analysis.',
    items: [
      {
        name: 'Glassnode',
        url: 'https://glassnode.com',
        tier: 'Pro',
        tags: ['MVRV', 'SOPR', 'Supply metrics'],
        desc: 'Industry standard for on-chain. MVRV Z-Score, SOPR, NVT, holder behavior, exchange flows. Free tier available.',
      },
      {
        name: 'CryptoQuant',
        url: 'https://cryptoquant.com',
        tier: 'Pro',
        tags: ['Exchange flows', 'Miner data', 'Alerts'],
        desc: 'Best for exchange flow analysis. Tracks whale deposits/withdrawals, miner behavior, and market stress signals.',
      },
      {
        name: 'Nansen',
        url: 'https://nansen.ai',
        tier: 'Pro',
        tags: ['Smart money', 'Wallet labels', 'DeFi'],
        desc: 'Wallet intelligence platform. Track smart money, fund movements, whale wallets. Labels 250M+ wallets.',
      },
      {
        name: 'Santiment',
        url: 'https://santiment.net',
        tier: 'Pro',
        tags: ['Social data', 'Dev activity', 'On-chain'],
        desc: 'Combines on-chain + social sentiment. Developer activity tracking, social volume, holder distribution.',
      },
      {
        name: 'DeFiLlama',
        url: 'https://defillama.com',
        tier: 'Free',
        tags: ['TVL', 'DeFi', 'Yields'],
        desc: 'Best free DeFi analytics. TVL across all protocols, yield tracking, fee revenue. 100% free, no account needed.',
      },
      {
        name: 'Whale Alert',
        url: 'https://whale-alert.io',
        tier: 'Free',
        tags: ['Large txs', 'Real-time', 'Multi-chain'],
        desc: 'Real-time large transaction tracker. Monitors BTC, ETH, and major blockchains for whale movements.',
      },
      {
        name: 'Dune Analytics',
        url: 'https://dune.com',
        tier: 'All',
        tags: ['Custom queries', 'Dashboards', 'SQL'],
        desc: 'Build custom on-chain dashboards with SQL. Community-shared dashboards for every protocol. Free tier available.',
      },
    ],
  },
  portfolio: {
    title: 'PORTFOLIO & TAX TOOLS',
    description: 'Track your holdings, calculate taxes, and manage your portfolio.',
    items: [
      {
        name: 'CoinTracker',
        url: 'https://cointracker.io',
        tier: 'All',
        tags: ['Tax', 'Portfolio', 'DeFi'],
        desc: 'Leading integrated portfolio + tax solution. 300+ exchange integrations, auto DeFi tracking, TurboTax compatible.',
      },
      {
        name: 'Koinly',
        url: 'https://koinly.io',
        tier: 'All',
        tags: ['Tax', '100+ countries', 'DeFi/NFT'],
        desc: 'Best for international users. Supports 100+ countries, DeFi, NFT, and margin trades. Simple tax reporting.',
      },
      {
        name: 'CoinTracking',
        url: 'https://cointracking.info',
        tier: 'Pro',
        tags: ['Tax', 'Analytics', '300+ exchanges'],
        desc: 'Power user favorite. Deep historical data imports, comprehensive analytics, and detailed tax reports.',
      },
      {
        name: 'CoinLedger',
        url: 'https://coinledger.io',
        tier: 'Beginner',
        tags: ['Tax', 'US-focused', 'TurboTax'],
        desc: 'Best for US-based users. Direct TurboTax and TaxAct integration. Simple, straightforward tax reporting.',
      },
      {
        name: 'DeBank',
        url: 'https://debank.com',
        tier: 'Free',
        tags: ['DeFi portfolio', 'Multi-chain', 'Free'],
        desc: 'Best free DeFi portfolio tracker. Tracks all wallet positions across all chains. No signup required.',
      },
      {
        name: 'ZenLedger',
        url: 'https://zenledger.io',
        tier: 'Pro',
        tags: ['DeFi tax', 'Staking', 'LP'],
        desc: 'Best for heavy DeFi users. Excels at staking rewards, liquidity pool tracking, and complex DeFi tax scenarios.',
      },
    ],
  },
  bots: {
    title: 'TRADING BOTS & AUTOMATION',
    description: 'Automated trading, grid bots, copy trading, and algorithmic strategies.',
    items: [
      {
        name: 'Cryptohopper',
        url: 'https://cryptohopper.com',
        tier: 'All',
        tags: ['Cloud-based', 'Strategy marketplace', 'DCA bots'],
        desc: 'Most versatile bot platform. Cloud-based, works with Binance/Coinbase/Kraken. Strategy marketplace for beginners.',
      },
      {
        name: '3Commas',
        url: 'https://3commas.io',
        tier: 'All',
        tags: ['Smart trades', 'Grid bots', 'DCA'],
        desc: 'Popular for smart trade terminals. Grid bots, DCA bots, and portfolio rebalancing across major exchanges.',
      },
      {
        name: 'Pionex',
        url: 'https://pionex.com',
        tier: 'Beginner',
        tags: ['Free bots', 'Grid trading', 'Built-in'],
        desc: 'Exchange with free built-in bots. 16+ bot types including grid, DCA, and rebalancing. No extra fees.',
      },
      {
        name: 'HaasOnline',
        url: 'https://haasonline.com',
        tier: 'Pro',
        tags: ['Custom scripts', 'Backtesting', 'Advanced'],
        desc: 'For advanced algorithmic traders. Custom scripting language, extensive backtesting, and strategy optimization.',
      },
    ],
  },
  learn: {
    title: 'LEARNING RESOURCES',
    description: 'Education, courses, communities, and research for all levels.',
    items: [
      {
        name: 'Investopedia',
        url: 'https://investopedia.com/cryptocurrency-4427699',
        tier: 'Beginner',
        tags: ['Education', 'Guides', 'Free'],
        desc: 'Best free crypto education. Comprehensive guides on trading, technical analysis, and investing fundamentals.',
      },
      {
        name: 'Binance Academy',
        url: 'https://academy.binance.com',
        tier: 'Beginner',
        tags: ['Free courses', 'Videos', 'Quizzes'],
        desc: 'Free structured crypto education. Beginner to advanced courses on blockchain, trading, DeFi, and security.',
      },
      {
        name: 'CoinBureau',
        url: 'https://coinbureau.com',
        tier: 'All',
        tags: ['Reviews', 'Research', 'YouTube'],
        desc: 'Trusted crypto research and reviews. In-depth analysis, project reviews, and educational YouTube content.',
      },
      {
        name: 'Messari',
        url: 'https://messari.io',
        tier: 'Pro',
        tags: ['Research', 'Data', 'Reports'],
        desc: 'Institutional-grade crypto research. Sector reports, token profiles, governance data, and fundraising intel.',
      },
      {
        name: 'The Block',
        url: 'https://theblock.co',
        tier: 'All',
        tags: ['News', 'Data', 'Research'],
        desc: 'Premium crypto news and data dashboards. Industry-leading reporting on institutional adoption and market structure.',
      },
      {
        name: 'r/Bitcoin & r/CryptoCurrency',
        url: 'https://reddit.com/r/bitcoin',
        tier: 'Free',
        tags: ['Community', 'Discussion', 'News'],
        desc: 'Largest crypto communities on Reddit. Real-time discussion, sentiment gauge, and community-vetted information.',
      },
    ],
  },
}

const TIER_COLORS = {
  Essential: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  Pro: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  Beginner: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  Free: 'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/30',
  All: 'bg-white/10 text-text-secondary border-white/20',
}

function ResourceCard({ item }) {
  const tierClass = TIER_COLORS[item.tier] || TIER_COLORS.All

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-bg-card rounded-xl p-3 border border-white/5 hover:border-white/15 active:scale-[0.98] transition-all"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-text-primary text-sm font-bold">{item.name}</span>
        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${tierClass}`}>
          {item.tier}
        </span>
      </div>
      <p className="text-text-muted text-[10px] leading-relaxed mb-2">{item.desc}</p>
      <div className="flex flex-wrap gap-1">
        {item.tags.map(tag => (
          <span key={tag} className="text-[8px] bg-white/5 text-text-muted px-1.5 py-0.5 rounded">
            {tag}
          </span>
        ))}
      </div>
    </a>
  )
}

export default function Resources() {
  const { t } = useTranslation(['resources', 'common'])
  const [activeCategory, setActiveCategory] = useState('exchanges')
  const category = RESOURCES[activeCategory]

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <h1 className="text-lg font-bold">Resources & Tools</h1>
      <p className="text-text-muted text-[11px]">
        Expert-curated platforms and tools used by professional traders. Based on community recommendations, expert reviews, and real-world performance.
      </p>

      {/* Category tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {CATEGORIES.map(c => (
          <button key={c.key} onClick={() => setActiveCategory(c.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
              activeCategory === c.key
                ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                : 'text-text-muted border border-white/5'
            }`}>
            {t(c.labelKey)}
          </button>
        ))}
      </div>

      {/* Category content */}
      <div>
        <h2 className="text-text-secondary text-xs font-semibold mb-1">{category.title}</h2>
        <p className="text-text-muted text-[10px] mb-3">{category.description}</p>
        <div className="space-y-2">
          {category.items.map(item => (
            <ResourceCard key={item.name} item={item} />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('resources:tierGuide').toUpperCase()}</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { tier: 'Essential', desc: 'Must-have tools every trader needs' },
            { tier: 'Beginner', desc: 'Easy to use, great starting point' },
            { tier: 'Pro', desc: 'Advanced features for experienced traders' },
            { tier: 'Free', desc: 'No cost, no account required' },
          ].map(t => (
            <div key={t.tier} className="flex items-start gap-2">
              <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border flex-shrink-0 mt-0.5 ${TIER_COLORS[t.tier]}`}>
                {t.tier}
              </span>
              <span className="text-text-muted text-[10px]">{t.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Getting started guide */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('resources:gettingStarted.title').toUpperCase()}</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          <div className="flex gap-2">
            <span className="text-accent-green font-bold text-xs w-4">1</span>
            <p><span className="text-text-secondary font-semibold">Beginner:</span> Start with Coinbase (exchange) + TradingView (charts) + CoinMarketCap (research). Learn the basics.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold text-xs w-4">2</span>
            <p><span className="text-text-secondary font-semibold">Intermediate:</span> Add CoinGlass (liquidations/funding) + Glassnode free tier (on-chain) + a portfolio tracker. Start using indicators.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-purple-400 font-bold text-xs w-4">3</span>
            <p><span className="text-text-secondary font-semibold">Advanced:</span> Layer in Nansen (smart money) + Dune (custom analytics) + trading bots. Build systematic strategies.</p>
          </div>
        </div>
      </div>

      {/* Key metrics everyone should track */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">KEY METRICS EVERY TRADER SHOULD TRACK</h3>
        <div className="space-y-2">
          {[
            { name: 'Fear & Greed Index', source: 'CoinMarketCap / Alternative.me', why: 'Market sentiment at a glance. Extreme fear = potential buy, extreme greed = potential sell.' },
            { name: 'MVRV Z-Score', source: 'Glassnode / Bitcoin Magazine Pro', why: 'Identifies market tops (>7) and bottoms (<0.1) based on on-chain valuation.' },
            { name: 'Funding Rates', source: 'CoinGlass / Coinalyze', why: 'Shows derivatives market positioning. Extreme funding = potential reversal signal.' },
            { name: 'Exchange Netflows', source: 'CryptoQuant / Glassnode', why: 'BTC flowing into exchanges = potential selling. Flowing out = accumulation.' },
            { name: 'Open Interest', source: 'CoinGlass / Coinalyze', why: 'Rising OI + rising price = strong trend. Rising OI + falling price = bearish pressure.' },
            { name: 'RSI + MACD Combo', source: 'TradingView / BTC Seer', why: 'Most reliable indicator combination. RSI for overbought/oversold, MACD for trend confirmation.' },
            { name: 'BTC Dominance', source: 'CoinMarketCap / BTC Seer', why: 'Rising dominance = money flowing to BTC safety. Falling = alt season potential.' },
            { name: 'DXY (Dollar Index)', source: 'TradingView / BTC Seer', why: 'BTC often inversely correlates with dollar strength. Weak dollar = bullish BTC.' },
          ].map((m, i) => (
            <div key={i} className="bg-white/[0.02] rounded-lg p-2.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-text-primary text-[11px] font-semibold">{m.name}</span>
                <span className="text-text-muted text-[8px]">{m.source}</span>
              </div>
              <p className="text-text-muted text-[10px]">{m.why}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
