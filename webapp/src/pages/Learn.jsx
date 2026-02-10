import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', labelKey: 'common:link.liquidations' },
  { path: '/powerlaw', labelKey: 'common:link.powerLaw' },
  { path: '/elliott-wave', labelKey: 'common:link.elliottWave' },
  { path: '/events', labelKey: 'common:link.events' },
  { path: '/tools', labelKey: 'common:link.tools' },
  { path: '/learn', labelKey: 'common:link.learn' },
]

const SECTIONS = [
  { key: 'basics', labelKey: 'learn:sections.basics' },
  { key: 'orders', labelKey: 'learn:sections.orders' },
  { key: 'indicators', labelKey: 'learn:sections.indicators' },
  { key: 'strategies', labelKey: 'learn:sections.strategies' },
  { key: 'risk', labelKey: 'learn:sections.risk' },
  { key: 'psychology', labelKey: 'learn:sections.psychology' },
  { key: 'patterns', labelKey: 'learn:sections.patterns' },
  { key: 'glossary', labelKey: 'learn:sections.glossary' },
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

function RiskManagement() {
  return (
    <div className="space-y-2">
      <Accordion title="The 1% Rule (Expanded)" color="text-accent-red">
        <p>Never risk more than <span className="text-text-secondary font-semibold">1% of your total account</span> on any single trade. This is the foundation of survival in trading.</p>
        <p><span className="text-text-secondary font-semibold">Formula:</span> Max Risk = Account Size x 0.01</p>
        <p><span className="text-text-secondary font-semibold">Worked example:</span></p>
        <p>Account: $10,000. Max risk per trade: $10,000 x 0.01 = <span className="text-accent-red font-semibold">$100</span>.</p>
        <p>Entry: $97,000. Stop-loss: $96,000. Risk per BTC = $1,000.</p>
        <p>Position size: $100 / $1,000 = <span className="text-accent-blue font-semibold">0.1 BTC</span> ($9,700 position).</p>
        <p className="text-accent-yellow">Even 10 consecutive losses = only -10%. You survive. Without the 1% rule, one bad trade can end your career.</p>
      </Accordion>

      <Accordion title="Risk-to-Reward Ratio" color="text-accent-blue">
        <p>The ratio between how much you risk (stop-loss distance) and how much you stand to gain (take-profit distance).</p>
        <p><span className="text-text-secondary font-semibold">Minimum target: 1:2</span> — risk $1 to make $2. This means you only need to win 34% of trades to be profitable.</p>
        <p><span className="text-text-secondary font-semibold">How to calculate:</span></p>
        <p>Entry: $97,000. Stop-loss: $96,000 (risk = $1,000). Take-profit: $99,000 (reward = $2,000).</p>
        <p>R:R = $1,000 : $2,000 = <span className="text-accent-green font-semibold">1:2</span>.</p>
        <p className="text-accent-yellow">Never take a trade with R:R below 1:1.5. If the setup doesn't offer good R:R, skip it — there will always be another trade.</p>
      </Accordion>

      <Accordion title="Stop-Loss Placement" color="text-accent-red">
        <p>Where you place your stop-loss matters more than whether you use one. A badly placed stop gets hit by normal market noise.</p>
        <p><span className="text-text-secondary font-semibold">Below support:</span> Place stop just below a key support level, not at an arbitrary %. If support is at $95,000, set stop at $94,800.</p>
        <p><span className="text-text-secondary font-semibold">ATR-based:</span> Use the Average True Range indicator. Stop = Entry - (1.5 x ATR). This adapts to current volatility.</p>
        <p><span className="text-text-secondary font-semibold">Never do:</span> "I'll set my stop at -5% because that feels right." Random percentages have no relation to market structure.</p>
        <p className="text-accent-yellow">A good stop-loss is placed where your trade thesis is invalidated — if price reaches that level, your reason for entering no longer holds.</p>
      </Accordion>

      <Accordion title="Position Sizing" color="text-accent-blue">
        <p>The exact formula to calculate how big your position should be:</p>
        <p className="text-text-secondary font-semibold text-xs">Position Size = Risk Amount / (Entry Price - Stop-Loss Price)</p>
        <p><span className="text-text-secondary font-semibold">Example:</span></p>
        <p>Account: $20,000. Risk: 1% = $200.</p>
        <p>Entry: $97,000. Stop-loss: $95,500. Distance = $1,500.</p>
        <p>Position: $200 / $1,500 = <span className="text-accent-blue font-semibold">0.133 BTC</span> (~$12,933).</p>
        <p>This means you're using ~65% of your account but only risking 1%. The stop-loss controls the risk, not the position size alone.</p>
      </Accordion>

      <Accordion title="Portfolio Heat" color="text-accent-yellow">
        <p><span className="text-text-secondary font-semibold">Portfolio heat</span> = the total risk across ALL your open positions combined.</p>
        <p><span className="text-text-secondary font-semibold">Max recommended:</span> 6% total portfolio risk at any time.</p>
        <p>If you risk 1% per trade, that means maximum 6 open trades. But if your trades are correlated (e.g., all crypto), the real risk is higher.</p>
        <p><span className="text-text-secondary font-semibold">Correlated positions:</span> If you're long BTC and long ETH, those aren't truly separate bets — they tend to move together. Count them as 1.5-2x risk.</p>
        <p className="text-accent-yellow">Most blown accounts come from having too many positions open at once during a market crash. Portfolio heat is your defense.</p>
      </Accordion>

      <Accordion title="Leverage Dangers" color="text-accent-red">
        <p>Leverage amplifies both gains AND losses. Here's the math most people ignore:</p>
        <p><span className="text-text-secondary font-semibold">2x leverage:</span> 50% drop = liquidation. BTC drops 50% roughly once per cycle.</p>
        <p><span className="text-text-secondary font-semibold">5x leverage:</span> 20% drop = liquidation. BTC drops 20% several times per year.</p>
        <p><span className="text-text-secondary font-semibold">10x leverage:</span> 10% drop = liquidation. BTC moves 10% in a single week regularly.</p>
        <p><span className="text-text-secondary font-semibold">25x leverage:</span> 4% drop = liquidation. This can happen in minutes.</p>
        <p><span className="text-text-secondary font-semibold">100x leverage:</span> 1% drop = liquidation. You are gambling, not trading.</p>
        <p className="text-accent-yellow">Safe leverage: 2-5x maximum, with tight stop-losses. Most professional traders use 1-3x. If you need high leverage to make money, your position sizing is wrong.</p>
      </Accordion>

      <Accordion title="Drawdown Recovery" color="text-accent-red">
        <p>Losses are not symmetrical. Recovering from a loss requires a <span className="text-text-secondary font-semibold">larger percentage gain</span> than the percentage you lost:</p>
        <div className="mt-1 space-y-0.5">
          {[
            ['10%', '11%'],
            ['20%', '25%'],
            ['30%', '43%'],
            ['40%', '67%'],
            ['50%', '100%'],
            ['60%', '150%'],
            ['70%', '233%'],
            ['80%', '400%'],
            ['90%', '900%'],
          ].map(([loss, gain]) => (
            <div key={loss} className="flex gap-2 text-[10px]">
              <span className="text-accent-red w-16">-{loss} loss</span>
              <span className="text-text-muted">=</span>
              <span className="text-accent-green">+{gain} needed to recover</span>
            </div>
          ))}
        </div>
        <p className="text-accent-yellow mt-2">This is why protecting capital is more important than making gains. A 50% loss requires a 100% gain just to break even. Prevention &gt; cure.</p>
      </Accordion>
    </div>
  )
}

function Psychology() {
  return (
    <div className="space-y-2">
      <Accordion title="FOMO (Fear of Missing Out)" color="text-accent-yellow">
        <p>That painful feeling when price is pumping and you're not in the trade. Your brain screams "BUY NOW before it goes higher!"</p>
        <p><span className="text-text-secondary font-semibold">Why it's dangerous:</span> FOMO makes you buy at the top. The best entries happen when the market is quiet and boring — not when everyone is excited.</p>
        <p><span className="text-text-secondary font-semibold">How to fight it:</span></p>
        <p>1. Remind yourself: if you missed the move, you missed the move. There will be another one.</p>
        <p>2. Never chase a green candle. Wait for a pullback to support before entering.</p>
        <p>3. If you feel intense urgency to buy, that's usually the worst time to buy.</p>
        <p className="text-accent-yellow">The market is open 24/7, 365 days a year. There is ALWAYS another opportunity. Missing one trade is nothing — buying the top is everything.</p>
      </Accordion>

      <Accordion title="Revenge Trading" color="text-accent-red">
        <p>You just lost money. You feel angry, frustrated, humiliated. Your instinct is to immediately open a bigger trade to "win it back."</p>
        <p><span className="text-text-secondary font-semibold">Why it's the #1 account killer:</span> Revenge trades are emotional, not strategic. You increase size, ignore your plan, and usually lose again — now even more. This spiral has destroyed more accounts than any market crash.</p>
        <p><span className="text-text-secondary font-semibold">How to fight it:</span></p>
        <p>1. Set a <span className="text-accent-red font-semibold">daily loss limit</span> (e.g., max 3% per day). Hit it = done for the day. No exceptions.</p>
        <p>2. After a loss, take at least 30 minutes away from the screen.</p>
        <p>3. Never increase position size after a loss. If anything, reduce it.</p>
        <p className="text-accent-yellow">Professional traders have a rule: after 2-3 consecutive losses, stop trading for the day. The market will be there tomorrow. Your capital might not be.</p>
      </Accordion>

      <Accordion title="Confirmation Bias" color="text-accent-yellow">
        <p>When you have a position, your brain automatically filters information to support your view and ignores evidence against it.</p>
        <p><span className="text-text-secondary font-semibold">Example:</span> You're long BTC. You read 10 bullish tweets and feel great. You see a bearish analysis and dismiss it as "FUD." Meanwhile, the bearish analysis was right.</p>
        <p><span className="text-text-secondary font-semibold">How to fight it:</span></p>
        <p>1. Actively seek out the opposite view before entering any trade.</p>
        <p>2. Ask yourself: "What would make this trade wrong?" Write that down.</p>
        <p>3. Follow analysts who disagree with you — they'll catch what you miss.</p>
        <p className="text-accent-yellow">The best traders are always looking for reasons they might be wrong. The worst traders only look for reasons they're right.</p>
      </Accordion>

      <Accordion title="Overtrading" color="text-accent-blue">
        <p>More trades does NOT mean more profit. Each trade has fees, slippage, and emotional cost. Most traders would be more profitable making fewer, higher-quality trades.</p>
        <p><span className="text-text-secondary font-semibold">Signs you're overtrading:</span></p>
        <p>- Trading out of boredom when there's no clear setup</p>
        <p>- Opening positions just to "be in the market"</p>
        <p>- Feeling anxious when you don't have an open trade</p>
        <p>- Taking setups that don't meet all your criteria</p>
        <p><span className="text-text-secondary font-semibold">Fix:</span> Quality over quantity. 2-3 high-conviction trades per week beat 20 random trades. If there's no clear setup, doing nothing IS a valid position.</p>
      </Accordion>

      <Accordion title="The Trading Plan" color="text-accent-green">
        <p>Write your plan <span className="text-text-secondary font-semibold">BEFORE</span> you enter the trade, while you're thinking clearly. Once money is on the line, emotions take over.</p>
        <p><span className="text-text-secondary font-semibold">Every trade plan must include:</span></p>
        <p>1. <span className="text-text-secondary">Entry reason:</span> Why are you entering? What's the setup?</p>
        <p>2. <span className="text-text-secondary">Entry price:</span> Exact price or zone.</p>
        <p>3. <span className="text-text-secondary">Stop-loss:</span> Where is your thesis invalidated?</p>
        <p>4. <span className="text-text-secondary">Take-profit:</span> Where do you take gains?</p>
        <p>5. <span className="text-text-secondary">Position size:</span> Based on 1% rule and stop distance.</p>
        <p>6. <span className="text-text-secondary">Max daily loss:</span> When do you stop for the day?</p>
        <p className="text-accent-yellow">If you can't write a plan for a trade, don't take the trade. "I just feel like it'll go up" is not a plan.</p>
      </Accordion>

      <Accordion title="Emotional Detachment" color="text-accent-blue">
        <p>Every trade is a probability, not a certainty. Even the best setups fail 30-40% of the time. Treating trades as statistics instead of personal wins/losses is the key to longevity.</p>
        <p><span className="text-text-secondary font-semibold">Mindset shift:</span></p>
        <p>- Don't say "I lost" — say "The trade was stopped out." It's not personal.</p>
        <p>- Don't celebrate winning trades — you might have won for the wrong reason.</p>
        <p>- Focus on whether you followed your plan, not the outcome. A losing trade executed well is better than a winning trade based on luck.</p>
        <p className="text-accent-yellow">Think of yourself as a casino, not a gambler. The casino doesn't celebrate every hand — it trusts the math over thousands of hands.</p>
      </Accordion>

      <Accordion title="When NOT to Trade" color="text-accent-red">
        <p>Some of the best trades are the ones you don't take. Knowing when to stay out is a skill:</p>
        <p><span className="text-accent-red font-semibold">Don't trade when:</span></p>
        <p>- You're tired, sick, or sleep-deprived</p>
        <p>- You're emotional (angry, euphoric, stressed, or sad)</p>
        <p>- Right after a big win (overconfidence)</p>
        <p>- Right after a big loss (revenge trading urge)</p>
        <p>- There's no clear setup in the market</p>
        <p>- Major uncertain news events are about to drop (FOMC, CPI)</p>
        <p>- You're checking your P&L every 30 seconds</p>
        <p className="text-accent-yellow">The market rewards patience. Sitting in cash waiting for a perfect setup IS trading. The best traders spend most of their time doing nothing.</p>
      </Accordion>
    </div>
  )
}

function Patterns() {
  return (
    <div className="space-y-2">
      <Accordion title="Support & Resistance" color="text-accent-green">
        <p><span className="text-text-secondary font-semibold">Support</span> = a price level where buying pressure is strong enough to prevent the price from falling further. The price "bounces" off this level.</p>
        <p><span className="text-text-secondary font-semibold">Resistance</span> = a price level where selling pressure prevents the price from rising further. The price gets "rejected" here.</p>
        <p><span className="text-text-secondary font-semibold">Key rules:</span></p>
        <p>1. The more times a level is tested, the stronger it is.</p>
        <p>2. When support breaks, it becomes resistance (and vice versa) — this is called a "flip."</p>
        <p>3. Round numbers ($50K, $100K) act as psychological S/R levels.</p>
        <p>4. S/R levels are zones, not exact prices. Think $94,800-$95,200, not $95,000 exactly.</p>
        <p className="text-accent-yellow">S/R is the single most important concept in trading. Master this before anything else.</p>
      </Accordion>

      <Accordion title="Double Top / Double Bottom" color="text-accent-blue">
        <p>A <span className="text-text-secondary font-semibold">reversal pattern</span> where price tests the same level twice and fails to break through.</p>
        <p><span className="text-text-secondary font-semibold">Double Top (bearish):</span> Price hits resistance twice, forming an "M" shape. Signals a potential drop. Sell/short when price breaks below the neckline (the low between the two peaks).</p>
        <p><span className="text-text-secondary font-semibold">Double Bottom (bullish):</span> Price hits support twice, forming a "W" shape. Signals a potential rise. Buy when price breaks above the neckline (the high between the two dips).</p>
        <p><span className="text-text-secondary font-semibold">Target:</span> Measure the distance from peak to neckline — that's your expected move from the breakout point.</p>
        <p className="text-accent-yellow">Wait for the neckline break with volume confirmation. Many double tops/bottoms fail — the break is the signal, not the second touch.</p>
      </Accordion>

      <Accordion title="Head & Shoulders" color="text-accent-blue">
        <p>One of the most reliable <span className="text-text-secondary font-semibold">reversal patterns</span>. Three peaks: left shoulder, head (highest), right shoulder.</p>
        <p><span className="text-text-secondary font-semibold">Regular H&S (bearish):</span> After an uptrend. The neckline connects the lows between the three peaks. Break below the neckline = sell signal.</p>
        <p><span className="text-text-secondary font-semibold">Inverse H&S (bullish):</span> After a downtrend. Three troughs with the middle being the lowest. Break above the neckline = buy signal.</p>
        <p><span className="text-text-secondary font-semibold">Target:</span> Distance from head to neckline, projected from the breakout point.</p>
        <p className="text-accent-yellow">The neckline doesn't have to be perfectly horizontal — it can be slightly angled. Volume should decrease on the right shoulder and spike on the neckline break.</p>
      </Accordion>

      <Accordion title="Triangles (Ascending, Descending, Symmetrical)" color="text-accent-blue">
        <p>Price consolidates between converging trendlines, building pressure before a breakout.</p>
        <p><span className="text-text-secondary font-semibold">Ascending Triangle (bullish bias):</span> Flat top resistance + rising lower trendline. Buyers are getting more aggressive. Usually breaks upward.</p>
        <p><span className="text-text-secondary font-semibold">Descending Triangle (bearish bias):</span> Flat bottom support + falling upper trendline. Sellers are getting more aggressive. Usually breaks downward.</p>
        <p><span className="text-text-secondary font-semibold">Symmetrical Triangle (neutral):</span> Both trendlines converging equally. Can break either way — wait for direction confirmation.</p>
        <p><span className="text-text-secondary font-semibold">Entry:</span> Trade the breakout direction with a stop-loss on the other side of the triangle.</p>
        <p className="text-accent-yellow">Breakouts in the last 25% of the triangle (near the apex) are weaker. The best breakouts happen in the first 50-75% of the pattern.</p>
      </Accordion>

      <Accordion title="Flags & Pennants" color="text-accent-green">
        <p>Short consolidation patterns after a strong, sharp move (the "flagpole"). They signal <span className="text-text-secondary font-semibold">continuation</span> of the previous trend.</p>
        <p><span className="text-text-secondary font-semibold">Bull Flag:</span> Strong move up (flagpole), then price drifts down in a small parallel channel (flag). Breakout upward continues the move.</p>
        <p><span className="text-text-secondary font-semibold">Bear Flag:</span> Strong move down, then price drifts up in a small channel. Breakout downward continues the move.</p>
        <p><span className="text-text-secondary font-semibold">Pennant:</span> Same as a flag but the consolidation forms a small symmetrical triangle instead of a channel.</p>
        <p><span className="text-text-secondary font-semibold">Target:</span> Measure the flagpole length and project it from the breakout point.</p>
        <p className="text-accent-yellow">Flags should form quickly (5-15 candles). If consolidation takes too long, the pattern weakens and may not work.</p>
      </Accordion>

      <Accordion title="Cup & Handle" color="text-accent-green">
        <p>A <span className="text-text-secondary font-semibold">bullish continuation</span> pattern that looks like a tea cup from the side. Usually forms over weeks to months.</p>
        <p><span className="text-text-secondary font-semibold">Cup:</span> A U-shaped (not V-shaped) decline and recovery. Price drops, rounds out at a bottom, and recovers back to the starting level.</p>
        <p><span className="text-text-secondary font-semibold">Handle:</span> A small pullback/consolidation near the right side of the cup. This is the final shakeout before breakout.</p>
        <p><span className="text-text-secondary font-semibold">Entry:</span> Buy when price breaks above the rim of the cup (the resistance level) with volume.</p>
        <p><span className="text-text-secondary font-semibold">Target:</span> Depth of the cup projected upward from the breakout.</p>
        <p className="text-accent-yellow">The handle should NOT drop more than 50% of the cup's depth. If it does, the pattern is weakening.</p>
      </Accordion>

      <Accordion title="Candlestick Basics" color="text-accent-blue">
        <p>Individual candles can signal reversals or continuation. Here are the most important ones:</p>
        <p><span className="text-text-secondary font-semibold">Doji:</span> Open and close at nearly the same price. Body is tiny or nonexistent. Shows indecision — neither buyers nor sellers won. At the top of a trend = potential reversal.</p>
        <p><span className="text-text-secondary font-semibold">Hammer:</span> Small body at the top, long lower wick (2x+ body length). Appears at bottoms — buyers rejected the low. Bullish reversal signal.</p>
        <p><span className="text-text-secondary font-semibold">Shooting Star:</span> Small body at the bottom, long upper wick. Appears at tops — sellers rejected the high. Bearish reversal signal.</p>
        <p><span className="text-text-secondary font-semibold">Engulfing:</span> A candle that completely covers the previous candle's body. Bullish engulfing = green candle swallows red. Bearish engulfing = red swallows green. Strong reversal signal.</p>
        <p className="text-accent-yellow">Single candles are weak signals alone. Always combine with S/R levels and volume. A hammer AT support with high volume = strong. A hammer in the middle of nowhere = meaningless.</p>
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
  const { t } = useTranslation(['learn', 'common'])
  const tabs = useMemo(() => MARKET_TABS.map(tab => ({ ...tab, label: t(tab.labelKey) })), [t])
  const sections = useMemo(() => SECTIONS.map(s => ({ ...s, label: t(s.labelKey) })), [t])
  const [section, setSection] = useState('basics')

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={tabs} />
      <h1 className="text-lg font-bold">{t('learn:title')}</h1>
      <p className="text-text-muted text-[11px]">
        {t('learn:subtitle')}
      </p>

      {/* Section tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {sections.map(s => (
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
      {section === 'risk' && <RiskManagement />}
      {section === 'psychology' && <Psychology />}
      {section === 'patterns' && <Patterns />}
      {section === 'glossary' && <Glossary />}

      <div className="bg-bg-card rounded-2xl p-4 border border-accent-yellow/15">
        <h3 className="text-accent-yellow text-xs font-semibold mb-2">{t('learn:remember.title')}</h3>
        <div className="text-text-muted text-[10px] space-y-1">
          <p>{t('learn:remember.rule1')}</p>
          <p>{t('learn:remember.rule2')}</p>
          <p>{t('learn:remember.rule3')}</p>
          <p>{t('learn:remember.rule4')}</p>
          <p>{t('learn:remember.rule5')}</p>
        </div>
      </div>
    </div>
  )
}
