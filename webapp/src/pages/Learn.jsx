import { useState } from 'react'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', label: 'Liquidations' },
  { path: '/powerlaw', label: 'Power Law' },
  { path: '/elliott-wave', label: 'Elliott Wave' },
  { path: '/events', label: 'Events' },
  { path: '/tools', label: 'Tools' },
  { path: '/learn', label: 'Learn' },
]

const SECTIONS = [
  { key: 'basics', label: 'Basics' },
  { key: 'orders', label: 'Orders' },
  { key: 'indicators', label: 'Indicators' },
  { key: 'strategies', label: 'Strategies' },
  { key: 'glossary', label: 'Glossary' },
]

function Accordion({ title, children, color }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-bg-card rounded-xl border border-white/5 overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-3 text-left">
        <span className={`text-xs font-semibold ${color || 'text-text-secondary'}`}>{title}</span>
        <span className="text-text-muted text-[10px]">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="px-3 pb-3 text-text-muted text-[11px] leading-relaxed space-y-2">{children}</div>}
    </div>
  )
}

function Basics() {
  return (
    <div className="space-y-2">
      <Accordion title="What is Bitcoin?">
        <p>Bitcoin is a decentralized digital currency that operates without a central bank or single administrator. It was created in 2009 by an anonymous person/group known as Satoshi Nakamoto.</p>
        <p>Key properties: <span className="text-text-secondary font-semibold">Fixed supply</span> (21 million max), <span className="text-text-secondary font-semibold">decentralized</span> (no single point of control), <span className="text-text-secondary font-semibold">transparent</span> (all transactions on public blockchain).</p>
      </Accordion>
      <Accordion title="How Does Trading Work?">
        <p>Trading means buying and selling Bitcoin to profit from price changes. You buy when you think the price will go up, and sell when you think it will go down.</p>
        <p><span className="text-text-secondary font-semibold">Spot trading:</span> Buy/sell actual Bitcoin. You own the asset.</p>
        <p><span className="text-text-secondary font-semibold">Futures/Derivatives:</span> Trade contracts that track Bitcoin's price. Can use leverage (borrowed money) to amplify gains — and losses.</p>
        <p><span className="text-text-secondary font-semibold">Long:</span> Betting price goes UP. <span className="text-text-secondary font-semibold">Short:</span> Betting price goes DOWN.</p>
      </Accordion>
      <Accordion title="What Moves Bitcoin's Price?">
        <p><span className="text-text-secondary font-semibold">Supply & Demand:</span> More buyers than sellers = price up. More sellers = price down.</p>
        <p><span className="text-text-secondary font-semibold">Halvings:</span> Every ~4 years, new BTC created per block is cut in half. Reduces supply, historically bullish.</p>
        <p><span className="text-text-secondary font-semibold">Macro events:</span> Interest rates, inflation, dollar strength (DXY), geopolitical events.</p>
        <p><span className="text-text-secondary font-semibold">Sentiment:</span> News, social media, fear & greed. Markets are driven by human emotion.</p>
        <p><span className="text-text-secondary font-semibold">Whale activity:</span> Large holders (1000+ BTC) moving coins to/from exchanges can signal buying or selling.</p>
      </Accordion>
      <Accordion title="What is Market Cap?">
        <p><span className="text-text-secondary font-semibold">Market Cap</span> = Price x Circulating Supply. It measures the total value of all coins in circulation.</p>
        <p>BTC at $97,000 with 19.8M coins = ~$1.92 trillion market cap.</p>
        <p>Higher market cap = more established, lower volatility. Lower market cap = more speculative, higher risk/reward.</p>
      </Accordion>
      <Accordion title="What is a Wallet?">
        <p>A crypto wallet stores your private keys — the passwords that prove you own your Bitcoin.</p>
        <p><span className="text-text-secondary font-semibold">Hot wallet:</span> Connected to internet (exchange accounts, mobile apps). Convenient but less secure.</p>
        <p><span className="text-text-secondary font-semibold">Cold wallet:</span> Offline hardware devices (Ledger, Trezor). Most secure for large holdings.</p>
        <p className="text-accent-yellow">"Not your keys, not your coins" — if the exchange gets hacked, you lose your funds. Self-custody is safest for large amounts.</p>
      </Accordion>
    </div>
  )
}

function Orders() {
  return (
    <div className="space-y-2">
      <Accordion title="Market Order" color="text-accent-green">
        <p>Buys or sells <span className="text-text-secondary font-semibold">immediately</span> at the current market price.</p>
        <p>Pros: Instant execution, guaranteed fill.</p>
        <p>Cons: You may get a slightly different price than expected (slippage), especially in volatile markets.</p>
        <p className="text-text-secondary">Use when: You need to enter/exit NOW and price precision doesn't matter much.</p>
      </Accordion>
      <Accordion title="Limit Order" color="text-accent-blue">
        <p>Sets a <span className="text-text-secondary font-semibold">specific price</span> at which you want to buy or sell. Only executes if the market reaches that price.</p>
        <p>Pros: You control the exact price. No slippage.</p>
        <p>Cons: May never fill if price doesn't reach your level.</p>
        <p className="text-text-secondary">Use when: You have a specific target price and can wait for it.</p>
      </Accordion>
      <Accordion title="Stop-Loss Order" color="text-accent-red">
        <p>Automatically sells when price drops to a set level, <span className="text-text-secondary font-semibold">limiting your loss</span>.</p>
        <p>Example: Buy at $97,000, set stop-loss at $95,000. If price drops to $95K, it auto-sells. Max loss = $2,000 per BTC.</p>
        <p className="text-text-secondary">Use when: ALWAYS. Every trade should have a stop-loss. No exceptions.</p>
      </Accordion>
      <Accordion title="Take-Profit Order" color="text-accent-green">
        <p>Automatically sells when price <span className="text-text-secondary font-semibold">rises to your target</span>, locking in profit.</p>
        <p>Example: Buy at $97,000, set take-profit at $103,000. Locks in $6,000 profit per BTC.</p>
        <p className="text-text-secondary">Use when: Always set alongside stop-loss. Have BOTH exit points before entering.</p>
      </Accordion>
      <Accordion title="Stop-Limit Order">
        <p>Combines stop and limit: when price hits the stop price, a <span className="text-text-secondary font-semibold">limit order is placed</span> (not a market order).</p>
        <p>Pros: More price control than a regular stop-loss.</p>
        <p>Cons: In fast crashes, the limit order may not fill, leaving you exposed.</p>
      </Accordion>
      <Accordion title="Trailing Stop">
        <p>A stop-loss that <span className="text-text-secondary font-semibold">moves up with the price</span>. Locks in profit as price rises, triggers if price drops by a set amount.</p>
        <p>Example: Set 3% trailing stop. Price rises from $97K to $103K, stop follows to $99,910. If price drops 3%, it sells at ~$99,910.</p>
        <p className="text-text-secondary">Use when: You're in a winning trade and want to ride the trend while protecting gains.</p>
      </Accordion>
    </div>
  )
}

function Indicators() {
  const items = [
    { name: 'RSI (Relative Strength Index)', level: 'Learn first', desc: 'Measures momentum on a 0-100 scale. Above 70 = overbought (potential drop). Below 30 = oversold (potential bounce). Most reliable on higher timeframes (4h, 1D).', tip: 'Don\'t buy just because RSI is low. Wait for RSI to turn UP from oversold.' },
    { name: 'MACD', level: 'Learn first', desc: 'Shows trend direction and momentum. The MACD line crossing above the signal line = bullish. Crossing below = bearish. Histogram shows the gap between the two lines.', tip: 'MACD + RSI together is the most popular combo. MACD for trend, RSI for timing.' },
    { name: 'Moving Averages (EMA/SMA)', level: 'Learn first', desc: 'Smooth out price data to show trends. EMA 9 & 21 for short-term, EMA 50 & 200 for long-term. Price above the average = bullish trend.', tip: 'Golden Cross (50 crosses above 200) = very bullish. Death Cross (50 below 200) = bearish.' },
    { name: 'Bollinger Bands', level: 'Essential', desc: 'Shows volatility range. Price near upper band = potentially overbought. Near lower band = oversold. Bands narrowing = big move coming (breakout).', tip: 'Best used WITH volume. Breakout + high volume = real move. Low volume = likely fakeout.' },
    { name: 'Volume', level: 'Essential', desc: 'Number of coins traded. High volume = strong conviction. Low volume = weak move. Volume precedes price — watch for volume spikes before big moves.', tip: 'Price up + volume up = strong trend. Price up + volume down = weakening, potential reversal.' },
    { name: 'Support & Resistance', level: 'Essential', desc: 'Price levels where buying (support) or selling (resistance) pressure is strong. Price bounces off these levels repeatedly.', tip: 'Once support breaks, it becomes resistance (and vice versa). These are the most important levels to watch.' },
    { name: 'Fibonacci Retracement', level: 'Intermediate', desc: 'Key levels (23.6%, 38.2%, 50%, 61.8%) where price often bounces during pullbacks. Based on the golden ratio.', tip: 'The 0.618 level is the most important. If price holds there during a pullback, the trend is likely intact.' },
    { name: 'Ichimoku Cloud', level: 'Advanced', desc: 'All-in-one indicator showing support/resistance, trend direction, and momentum. Price above cloud = bullish. Below = bearish.', tip: 'The cloud itself acts as support/resistance. Thick cloud = strong. Thin cloud = weak, breakout likely.' },
    { name: 'Fear & Greed Index', level: 'Essential', desc: 'Market sentiment score 0-100. Extreme Fear (0-25) = potential buy. Extreme Greed (75-100) = potential sell. Uses volatility, volume, social media, and dominance.', tip: '"Be fearful when others are greedy, greedy when others are fearful" — Warren Buffett.' },
    { name: 'Funding Rate', level: 'Intermediate', desc: 'Shows if the derivatives market is over-leveraged long or short. High positive = too many longs (bearish signal). Negative = too many shorts (bullish signal).', tip: 'Extreme funding rates often precede liquidation cascades and sharp reversals.' },
  ]

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <Accordion key={item.name} title={`${item.name}`} color={item.level === 'Learn first' ? 'text-accent-green' : item.level === 'Advanced' ? 'text-purple-400' : 'text-accent-blue'}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
              item.level === 'Learn first' ? 'bg-accent-green/15 text-accent-green border-accent-green/30' :
              item.level === 'Essential' ? 'bg-accent-blue/15 text-accent-blue border-accent-blue/30' :
              item.level === 'Intermediate' ? 'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/30' :
              'bg-purple-500/15 text-purple-400 border-purple-500/30'
            }`}>{item.level}</span>
          </div>
          <p>{item.desc}</p>
          <p className="text-accent-yellow mt-1">Pro tip: {item.tip}</p>
        </Accordion>
      ))}
    </div>
  )
}

function Strategies() {
  return (
    <div className="space-y-2">
      <Accordion title="HODLing (Buy & Hold)" color="text-accent-green">
        <p>The simplest strategy. Buy Bitcoin and hold for years regardless of short-term price swings.</p>
        <p><span className="text-text-secondary font-semibold">Best for:</span> Beginners. Historically, anyone who held BTC for 4+ years has been profitable.</p>
        <p><span className="text-text-secondary font-semibold">Risk:</span> Low (if you can handle seeing -50% drops without panic selling).</p>
      </Accordion>
      <Accordion title="Dollar Cost Averaging (DCA)" color="text-accent-green">
        <p>Invest a fixed amount at regular intervals (weekly/monthly) regardless of price. Removes the stress of timing the market.</p>
        <p><span className="text-text-secondary font-semibold">Best for:</span> Beginners and long-term investors. Proven to outperform most timing strategies.</p>
        <p><span className="text-text-secondary font-semibold">Example:</span> $100/week for 2 years. You buy more BTC when cheap, less when expensive. Average cost smooths out.</p>
      </Accordion>
      <Accordion title="Swing Trading" color="text-accent-blue">
        <p>Hold positions for days to weeks, capturing medium-term price swings using technical analysis.</p>
        <p><span className="text-text-secondary font-semibold">Best for:</span> Intermediate traders. Requires understanding of charts, indicators, and risk management.</p>
        <p><span className="text-text-secondary font-semibold">Key tools:</span> Support/resistance, RSI, MACD, volume. Enter at support, exit at resistance.</p>
      </Accordion>
      <Accordion title="Day Trading" color="text-accent-red">
        <p>Open and close positions within the same day. Requires constant monitoring and fast execution.</p>
        <p><span className="text-text-secondary font-semibold">Best for:</span> Advanced traders only. 95% of day traders lose money — this is a statistical fact.</p>
        <p><span className="text-text-secondary font-semibold">Warning:</span> High stress, high fees, requires discipline. Start with paper trading (practice with fake money).</p>
      </Accordion>
      <Accordion title="The 1% Risk Rule">
        <p>Never risk more than 1% of your total portfolio on a single trade. This is THE most important rule in trading.</p>
        <p><span className="text-text-secondary font-semibold">Example:</span> $10,000 account = max $100 risk per trade. If your stop-loss is 2% below entry, your position size = $5,000.</p>
        <p>With the 1% rule, you can lose 10 trades in a row and only be down 10%. Without it, one bad trade can destroy your account.</p>
      </Accordion>
      <Accordion title="Support/Resistance Trading">
        <p>Identify key price levels where BTC repeatedly bounces (support) or gets rejected (resistance).</p>
        <p><span className="text-text-secondary font-semibold">Strategy:</span> Buy near support with stop-loss just below. Sell near resistance or set take-profit there.</p>
        <p><span className="text-text-secondary font-semibold">Confirmation:</span> Wait for a bounce (don't buy into a falling knife). Volume + RSI turning up = stronger signal.</p>
      </Accordion>
    </div>
  )
}

function Glossary() {
  const terms = [
    ['ATH', 'All-Time High — the highest price ever reached'],
    ['ATL', 'All-Time Low — the lowest price ever recorded'],
    ['Bearish', 'Expecting price to go DOWN'],
    ['Bullish', 'Expecting price to go UP'],
    ['Candle', 'A chart bar showing open, high, low, close price for a time period'],
    ['DCA', 'Dollar Cost Averaging — buying fixed amounts at regular intervals'],
    ['DeFi', 'Decentralized Finance — financial services on blockchain without banks'],
    ['DYOR', 'Do Your Own Research — never blindly follow others\' advice'],
    ['FOMO', 'Fear Of Missing Out — emotional buying during rallies'],
    ['FUD', 'Fear, Uncertainty, Doubt — negative news/sentiment (sometimes manufactured)'],
    ['Gas', 'Transaction fees paid to blockchain miners/validators'],
    ['Halving', 'Bitcoin event every ~4 years that cuts block rewards in half'],
    ['HODL', 'Hold On for Dear Life — long-term holding strategy'],
    ['Leverage', 'Borrowing money to trade larger positions (amplifies gains AND losses)'],
    ['Liquidation', 'Forced closing of a leveraged position when losses exceed margin'],
    ['Long', 'A trade betting the price will go UP'],
    ['MACD', 'Moving Average Convergence Divergence — trend/momentum indicator'],
    ['Market Cap', 'Total value = Price x Circulating Supply'],
    ['MVRV', 'Market Value to Realized Value — on-chain valuation metric'],
    ['OI', 'Open Interest — total value of open futures/derivatives contracts'],
    ['RSI', 'Relative Strength Index — momentum oscillator (0-100)'],
    ['Satoshi', 'Smallest BTC unit (0.00000001 BTC). Named after creator.'],
    ['Short', 'A trade betting the price will go DOWN'],
    ['Slippage', 'Difference between expected and actual execution price'],
    ['Stop-Loss', 'Order that auto-sells if price drops to a set level'],
    ['Support', 'Price level where buying pressure prevents further drops'],
    ['Resistance', 'Price level where selling pressure prevents further rises'],
    ['Take-Profit', 'Order that auto-sells when price reaches your profit target'],
    ['TVL', 'Total Value Locked — money deposited in DeFi protocols'],
    ['Whale', 'Entity holding large amounts of crypto (1000+ BTC)'],
  ]

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="space-y-1.5">
        {terms.map(([term, def]) => (
          <div key={term} className="flex gap-2 py-1 border-b border-white/[0.03] last:border-0">
            <span className="text-accent-blue text-[11px] font-bold w-20 flex-shrink-0">{term}</span>
            <span className="text-text-muted text-[11px]">{def}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Learn() {
  const [section, setSection] = useState('basics')

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <h1 className="text-lg font-bold">Learn Trading</h1>
      <p className="text-text-muted text-[11px]">
        Everything you need to know to start trading Bitcoin, from zero to confident. Built from expert guides, community wisdom, and professional best practices.
      </p>

      {/* Section tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {SECTIONS.map(s => (
          <button key={s.key} onClick={() => setSection(s.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
              section === s.key
                ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                : 'text-text-muted border border-white/5'
            }`}>
            {s.label}
          </button>
        ))}
      </div>

      {section === 'basics' && <Basics />}
      {section === 'orders' && <Orders />}
      {section === 'indicators' && <Indicators />}
      {section === 'strategies' && <Strategies />}
      {section === 'glossary' && <Glossary />}

      <div className="bg-bg-card rounded-2xl p-4 border border-accent-yellow/15">
        <h3 className="text-accent-yellow text-xs font-semibold mb-2">REMEMBER</h3>
        <div className="text-text-muted text-[10px] space-y-1">
          <p>1. Never invest more than you can afford to lose</p>
          <p>2. Always use a stop-loss on every trade</p>
          <p>3. Start small — learn with amounts that don't cause stress</p>
          <p>4. Paper trade first — practice without real money until consistent</p>
          <p>5. The market will always be there tomorrow — no trade is worth your mental health</p>
        </div>
      </div>
    </div>
  )
}
