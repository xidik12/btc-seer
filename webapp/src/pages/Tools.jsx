import { useState } from 'react'
import SubTabBar from '../components/SubTabBar'

const MARKET_TABS = [
  { path: '/liquidations', label: 'Liquidations' },
  { path: '/powerlaw', label: 'Power Law' },
  { path: '/elliott-wave', label: 'Elliott Wave' },
  { path: '/events', label: 'Events' },
  { path: '/tools', label: 'Tools' },
]

function PositionSizeCalc() {
  const [capital, setCapital] = useState('')
  const [riskPct, setRiskPct] = useState('2')
  const [entry, setEntry] = useState('')
  const [stopLoss, setStopLoss] = useState('')

  const capitalNum = parseFloat(capital) || 0
  const riskNum = parseFloat(riskPct) || 0
  const entryNum = parseFloat(entry) || 0
  const slNum = parseFloat(stopLoss) || 0

  const riskAmount = capitalNum * (riskNum / 100)
  const stopDist = Math.abs(entryNum - slNum)
  const positionSize = stopDist > 0 ? riskAmount / stopDist : 0
  const positionValue = positionSize * entryNum

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">POSITION SIZE CALCULATOR</h3>
      <p className="text-text-muted text-[10px] mb-3">
        Calculate your ideal position size based on account risk. Pros risk 1-2% per trade.
      </p>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Account Balance ($)</label>
          <input type="number" value={capital} onChange={e => setCapital(e.target.value)}
            placeholder="10000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Risk Per Trade (%)</label>
          <input type="number" value={riskPct} onChange={e => setRiskPct(e.target.value)}
            placeholder="2" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Entry Price ($)</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="97000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Stop Loss ($)</label>
          <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)}
            placeholder="95000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {capitalNum > 0 && entryNum > 0 && slNum > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <ResultBox label="Risk Amount" value={`$${riskAmount.toFixed(2)}`} />
          <ResultBox label="Stop Distance" value={`$${stopDist.toFixed(2)}`} />
          <ResultBox label="Position Size" value={`${positionSize.toFixed(6)} BTC`} highlight />
          <ResultBox label="Position Value" value={`$${positionValue.toFixed(2)}`} highlight />
        </div>
      )}
    </div>
  )
}

function PnLCalc() {
  const [entry, setEntry] = useState('')
  const [exit, setExit] = useState('')
  const [amount, setAmount] = useState('')
  const [direction, setDirection] = useState('long')
  const [leverage, setLeverage] = useState('1')

  const entryNum = parseFloat(entry) || 0
  const exitNum = parseFloat(exit) || 0
  const amountNum = parseFloat(amount) || 0
  const leverageNum = parseFloat(leverage) || 1

  let pnl = 0
  let pnlPct = 0
  if (entryNum > 0 && exitNum > 0) {
    const diff = direction === 'long' ? exitNum - entryNum : entryNum - exitNum
    pnlPct = (diff / entryNum) * 100 * leverageNum
    pnl = amountNum * (pnlPct / 100)
  }

  const liqPrice = direction === 'long'
    ? entryNum * (1 - 1 / leverageNum)
    : entryNum * (1 + 1 / leverageNum)

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">PROFIT / LOSS CALCULATOR</h3>
      <div className="flex gap-1 mb-3">
        {['long', 'short'].map(d => (
          <button key={d} onClick={() => setDirection(d)}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              direction === d
                ? d === 'long' ? 'bg-accent-green/20 text-accent-green border border-accent-green/30' : 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                : 'text-text-muted border border-white/5'
            }`}>
            {d.toUpperCase()}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Entry Price ($)</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="97000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Exit Price ($)</label>
          <input type="number" value={exit} onChange={e => setExit(e.target.value)}
            placeholder="100000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Investment ($)</label>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="1000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Leverage (x)</label>
          <input type="number" value={leverage} onChange={e => setLeverage(e.target.value)}
            placeholder="1" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {entryNum > 0 && exitNum > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <ResultBox label="P&L" value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`}
            color={pnl >= 0 ? 'text-accent-green' : 'text-accent-red'} highlight />
          <ResultBox label="ROI" value={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`}
            color={pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red'} highlight />
          {leverageNum > 1 && (
            <ResultBox label="Liquidation Price" value={`$${liqPrice.toFixed(2)}`} color="text-accent-red" />
          )}
          <ResultBox label="Break-Even" value={`$${entryNum.toFixed(2)}`} />
        </div>
      )}
    </div>
  )
}

function RiskRewardCalc() {
  const [entry, setEntry] = useState('')
  const [target, setTarget] = useState('')
  const [stopLoss, setStopLoss] = useState('')

  const entryNum = parseFloat(entry) || 0
  const targetNum = parseFloat(target) || 0
  const slNum = parseFloat(stopLoss) || 0

  const reward = Math.abs(targetNum - entryNum)
  const risk = Math.abs(entryNum - slNum)
  const rrRatio = risk > 0 ? reward / risk : 0
  const winRateNeeded = risk > 0 ? (1 / (1 + rrRatio)) * 100 : 0

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">RISK / REWARD CALCULATOR</h3>
      <p className="text-text-muted text-[10px] mb-3">
        Pros aim for at least 1:2 R:R. Higher ratios mean you can be wrong more often and still profit.
      </p>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Entry ($)</label>
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="97000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Target ($)</label>
          <input type="number" value={target} onChange={e => setTarget(e.target.value)}
            placeholder="103000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Stop ($)</label>
          <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)}
            placeholder="95000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {entryNum > 0 && targetNum > 0 && slNum > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-3 bg-accent-red/20 rounded-full overflow-hidden">
              <div className="h-full bg-accent-red rounded-full" style={{ width: `${Math.min(risk / (risk + reward) * 100, 100)}%` }} />
            </div>
            <span className="text-accent-red text-[10px] font-bold w-16 text-right">-${risk.toFixed(0)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-3 bg-accent-green/20 rounded-full overflow-hidden">
              <div className="h-full bg-accent-green rounded-full" style={{ width: `${Math.min(reward / (risk + reward) * 100, 100)}%` }} />
            </div>
            <span className="text-accent-green text-[10px] font-bold w-16 text-right">+${reward.toFixed(0)}</span>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-2">
            <ResultBox label="R:R Ratio"
              value={`1:${rrRatio.toFixed(2)}`}
              color={rrRatio >= 2 ? 'text-accent-green' : rrRatio >= 1 ? 'text-accent-yellow' : 'text-accent-red'}
              highlight />
            <ResultBox label="Win Rate Needed" value={`${winRateNeeded.toFixed(1)}%`} />
            <ResultBox label="Quality"
              value={rrRatio >= 3 ? 'Excellent' : rrRatio >= 2 ? 'Good' : rrRatio >= 1 ? 'Fair' : 'Poor'}
              color={rrRatio >= 2 ? 'text-accent-green' : rrRatio >= 1 ? 'text-accent-yellow' : 'text-accent-red'} />
          </div>
        </div>
      )}
    </div>
  )
}

function DCACalc() {
  const [investment, setInvestment] = useState('100')
  const [frequency, setFrequency] = useState('weekly')
  const [months, setMonths] = useState('12')
  const [currentPrice, setCurrentPrice] = useState('97000')

  const invNum = parseFloat(investment) || 0
  const monthsNum = parseInt(months) || 0
  const priceNum = parseFloat(currentPrice) || 0

  const freqMultiplier = { daily: 30, weekly: 4.33, biweekly: 2.17, monthly: 1 }
  const buysPerMonth = freqMultiplier[frequency] || 1
  const totalBuys = Math.round(buysPerMonth * monthsNum)
  const totalInvested = invNum * totalBuys
  const btcAccumulated = priceNum > 0 ? totalInvested / priceNum : 0

  // Simulate scenarios
  const scenarios = [
    { label: 'Bear (-30%)', pct: -30, color: 'text-accent-red' },
    { label: 'Flat (0%)', pct: 0, color: 'text-text-muted' },
    { label: 'Bull (+50%)', pct: 50, color: 'text-accent-green' },
    { label: 'Moon (+100%)', pct: 100, color: 'text-accent-green' },
  ]

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <h3 className="text-text-secondary text-xs font-semibold mb-3">DCA CALCULATOR</h3>
      <p className="text-text-muted text-[10px] mb-3">
        Dollar Cost Averaging reduces timing risk. Consistent buying regardless of price.
      </p>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-text-muted text-[10px]">Amount Per Buy ($)</label>
          <input type="number" value={investment} onChange={e => setInvestment(e.target.value)}
            placeholder="100" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Frequency</label>
          <select value={frequency} onChange={e => setFrequency(e.target.value)}
            className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Bi-Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Duration (months)</label>
          <input type="number" value={months} onChange={e => setMonths(e.target.value)}
            placeholder="12" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
        <div>
          <label className="text-text-muted text-[10px]">Current BTC Price ($)</label>
          <input type="number" value={currentPrice} onChange={e => setCurrentPrice(e.target.value)}
            placeholder="97000" className="w-full bg-bg-hover border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary mt-0.5" />
        </div>
      </div>
      {invNum > 0 && monthsNum > 0 && (
        <>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <ResultBox label="Total Invested" value={`$${totalInvested.toLocaleString()}`} />
            <ResultBox label="Total Buys" value={totalBuys.toString()} />
            <ResultBox label="BTC Accumulated" value={`${btcAccumulated.toFixed(6)}`} highlight />
          </div>
          <div className="text-text-muted text-[9px] font-semibold mb-1.5">PRICE SCENARIOS</div>
          <div className="grid grid-cols-2 gap-2">
            {scenarios.map(s => {
              const futurePrice = priceNum * (1 + s.pct / 100)
              const futureValue = btcAccumulated * futurePrice
              const pnl = futureValue - totalInvested
              return (
                <div key={s.label} className="bg-white/[0.02] rounded-lg p-2">
                  <div className="text-text-muted text-[9px]">{s.label}</div>
                  <div className={`text-xs font-bold ${s.color}`}>
                    ${futureValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                  <div className={`text-[9px] ${pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {pnl >= 0 ? '+' : ''}{((pnl / totalInvested) * 100).toFixed(1)}%
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function ResultBox({ label, value, color, highlight }) {
  return (
    <div className={`rounded-xl p-2.5 text-center ${highlight ? 'bg-accent-blue/5 border border-accent-blue/15' : 'bg-white/[0.02] border border-white/5'}`}>
      <div className="text-text-muted text-[9px] font-medium">{label}</div>
      <div className={`text-sm font-bold tabular-nums ${color || 'text-text-primary'}`}>{value}</div>
    </div>
  )
}

export default function Tools() {
  const [activeCalc, setActiveCalc] = useState('position')

  const calcs = [
    { key: 'position', label: 'Position Size' },
    { key: 'pnl', label: 'P&L' },
    { key: 'rr', label: 'Risk/Reward' },
    { key: 'dca', label: 'DCA' },
  ]

  return (
    <div className="px-4 pt-4 space-y-3 pb-20">
      <SubTabBar tabs={MARKET_TABS} />
      <h1 className="text-lg font-bold">Trading Tools</h1>

      {/* Calculator tabs */}
      <div className="flex gap-1 bg-bg-card rounded-xl p-1 border border-white/5">
        {calcs.map(c => (
          <button key={c.key} onClick={() => setActiveCalc(c.key)}
            className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
              activeCalc === c.key
                ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                : 'text-text-muted'
            }`}>
            {c.label}
          </button>
        ))}
      </div>

      {activeCalc === 'position' && <PositionSizeCalc />}
      {activeCalc === 'pnl' && <PnLCalc />}
      {activeCalc === 'rr' && <RiskRewardCalc />}
      {activeCalc === 'dca' && <DCACalc />}

      {/* Pro tips */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">PRO RISK MANAGEMENT RULES</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold">1</span>
            <p><span className="text-text-secondary font-semibold">1-2% Rule:</span> Never risk more than 1-2% of your total capital on a single trade. This ensures survival through losing streaks.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold">2</span>
            <p><span className="text-text-secondary font-semibold">Portfolio Heat:</span> Keep total capital at risk across all open positions below 6%. More exposure = more risk of ruin.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold">3</span>
            <p><span className="text-text-secondary font-semibold">R:R Minimum 1:2:</span> Only take trades with at least 1:2 risk-to-reward. You can be wrong 60% of the time and still profit.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold">4</span>
            <p><span className="text-text-secondary font-semibold">ATR-Based Stops:</span> Set stop-losses based on ATR (volatility), not arbitrary percentages. Avoids getting stopped out by normal price noise.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-accent-blue font-bold">5</span>
            <p><span className="text-text-secondary font-semibold">Trading Journal:</span> Log every trade with entry reason, exit, and lesson learned. Successful traders review and learn from every trade.</p>
          </div>
        </div>
      </div>

      {/* Common mistakes */}
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/10">
        <h3 className="text-accent-red text-xs font-semibold mb-3">COMMON MISTAKES TO AVOID</h3>
        <div className="space-y-1.5 text-[11px] text-text-muted">
          {[
            'FOMO buying during rallies — if everyone is talking about it, you\'re late',
            'Revenge trading after a loss — step away, reassess, come back with a plan',
            'Moving your stop-loss further away — accept the loss, protect your capital',
            'Over-leveraging — leverage amplifies losses just as much as gains',
            'No exit plan — always know your target AND stop before entering',
            'Trading without a journal — you can\'t improve what you don\'t measure',
            'Ignoring fees — frequent trading eats into profits significantly',
            'All-in on one position — diversify to survive black swan events',
          ].map((m, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-accent-red mt-0.5">x</span>
              <p>{m}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
