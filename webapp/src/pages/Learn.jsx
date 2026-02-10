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
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:basics.whatIsBitcoin.title')}>
        <p>{t('learn:basics.whatIsBitcoin.p1')}</p>
        <p>{t('learn:basics.whatIsBitcoin.p2_prefix')}<span className="text-text-secondary font-semibold">{t('learn:basics.whatIsBitcoin.p2_fixedSupply')}</span>{t('learn:basics.whatIsBitcoin.p2_fixedSupplyDesc')}<span className="text-text-secondary font-semibold">{t('learn:basics.whatIsBitcoin.p2_decentralized')}</span>{t('learn:basics.whatIsBitcoin.p2_decentralizedDesc')}<span className="text-text-secondary font-semibold">{t('learn:basics.whatIsBitcoin.p2_transparent')}</span>{t('learn:basics.whatIsBitcoin.p2_transparentDesc')}</p>
      </Accordion>
      <Accordion title={t('learn:basics.howTrading.title')}>
        <p>{t('learn:basics.howTrading.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.howTrading.spot_label')}</span>{t('learn:basics.howTrading.spot_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.howTrading.futures_label')}</span>{t('learn:basics.howTrading.futures_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.howTrading.long_label')}</span>{t('learn:basics.howTrading.long_desc')}<span className="text-text-secondary font-semibold">{t('learn:basics.howTrading.short_label')}</span>{t('learn:basics.howTrading.short_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:basics.whatMoves.title')}>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.whatMoves.supply_label')}</span>{t('learn:basics.whatMoves.supply_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.whatMoves.halvings_label')}</span>{t('learn:basics.whatMoves.halvings_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.whatMoves.macro_label')}</span>{t('learn:basics.whatMoves.macro_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.whatMoves.sentiment_label')}</span>{t('learn:basics.whatMoves.sentiment_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.whatMoves.whales_label')}</span>{t('learn:basics.whatMoves.whales_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:basics.marketCap.title')}>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.marketCap.p1_label')}</span>{t('learn:basics.marketCap.p1_desc')}</p>
        <p>{t('learn:basics.marketCap.p2')}</p>
        <p>{t('learn:basics.marketCap.p3')}</p>
      </Accordion>
      <Accordion title={t('learn:basics.wallet.title')}>
        <p>{t('learn:basics.wallet.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.wallet.hot_label')}</span>{t('learn:basics.wallet.hot_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:basics.wallet.cold_label')}</span>{t('learn:basics.wallet.cold_desc')}</p>
        <p className="text-accent-yellow">{t('learn:basics.wallet.warning')}</p>
      </Accordion>
    </div>
  )
}

function Orders() {
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:orders.market.title')} color="text-accent-green">
        <p>{t('learn:orders.market.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.market.p1_bold')}</span>{t('learn:orders.market.p1_suffix')}</p>
        <p>{t('learn:orders.market.pros')}</p>
        <p>{t('learn:orders.market.cons')}</p>
        <p className="text-text-secondary">{t('learn:orders.market.useWhen')}</p>
      </Accordion>
      <Accordion title={t('learn:orders.limit.title')} color="text-accent-blue">
        <p>{t('learn:orders.limit.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.limit.p1_bold')}</span>{t('learn:orders.limit.p1_suffix')}</p>
        <p>{t('learn:orders.limit.pros')}</p>
        <p>{t('learn:orders.limit.cons')}</p>
        <p className="text-text-secondary">{t('learn:orders.limit.useWhen')}</p>
      </Accordion>
      <Accordion title={t('learn:orders.stopLoss.title')} color="text-accent-red">
        <p>{t('learn:orders.stopLoss.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.stopLoss.p1_bold')}</span>{t('learn:orders.stopLoss.p1_suffix')}</p>
        <p>{t('learn:orders.stopLoss.example')}</p>
        <p className="text-text-secondary">{t('learn:orders.stopLoss.useWhen')}</p>
      </Accordion>
      <Accordion title={t('learn:orders.takeProfit.title')} color="text-accent-green">
        <p>{t('learn:orders.takeProfit.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.takeProfit.p1_bold')}</span>{t('learn:orders.takeProfit.p1_suffix')}</p>
        <p>{t('learn:orders.takeProfit.example')}</p>
        <p className="text-text-secondary">{t('learn:orders.takeProfit.useWhen')}</p>
      </Accordion>
      <Accordion title={t('learn:orders.stopLimit.title')}>
        <p>{t('learn:orders.stopLimit.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.stopLimit.p1_bold')}</span>{t('learn:orders.stopLimit.p1_suffix')}</p>
        <p>{t('learn:orders.stopLimit.pros')}</p>
        <p>{t('learn:orders.stopLimit.cons')}</p>
      </Accordion>
      <Accordion title={t('learn:orders.trailingStop.title')}>
        <p>{t('learn:orders.trailingStop.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:orders.trailingStop.p1_bold')}</span>{t('learn:orders.trailingStop.p1_suffix')}</p>
        <p>{t('learn:orders.trailingStop.example')}</p>
        <p className="text-text-secondary">{t('learn:orders.trailingStop.useWhen')}</p>
      </Accordion>
    </div>
  )
}

function Indicators() {
  const { t } = useTranslation(['learn'])
  const indicatorKeys = ['rsi', 'macd', 'movingAverages', 'bollinger', 'volume', 'supportResistance', 'fibonacci', 'ichimoku', 'fearGreed', 'fundingRate']

  const items = indicatorKeys.map((key) => ({
    key,
    name: t(`learn:indicators.${key}.name`),
    level: t(`learn:indicators.${key}.level`),
    desc: t(`learn:indicators.${key}.desc`),
    tip: t(`learn:indicators.${key}.tip`),
  }))

  const learnFirst = t('learn:indicators.learnFirst')
  const advanced = t('learn:indicators.advanced')

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <Accordion key={item.key} title={item.name} color={item.level === learnFirst ? 'text-accent-green' : item.level === advanced ? 'text-purple-400' : 'text-accent-blue'}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
              item.level === learnFirst ? 'bg-accent-green/15 text-accent-green border-accent-green/30' :
              item.level === t('learn:indicators.essential') ? 'bg-accent-blue/15 text-accent-blue border-accent-blue/30' :
              item.level === t('learn:indicators.intermediate') ? 'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/30' :
              'bg-purple-500/15 text-purple-400 border-purple-500/30'
            }`}>{item.level}</span>
          </div>
          <p>{item.desc}</p>
          <p className="text-accent-yellow mt-1">{t('learn:indicators.proTip')} {item.tip}</p>
        </Accordion>
      ))}
    </div>
  )
}

function Strategies() {
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:strategies.hodl.title')} color="text-accent-green">
        <p>{t('learn:strategies.hodl.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.hodl.bestFor_label')}</span>{t('learn:strategies.hodl.bestFor_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.hodl.risk_label')}</span>{t('learn:strategies.hodl.risk_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:strategies.dca.title')} color="text-accent-green">
        <p>{t('learn:strategies.dca.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.dca.bestFor_label')}</span>{t('learn:strategies.dca.bestFor_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.dca.example_label')}</span>{t('learn:strategies.dca.example_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:strategies.swing.title')} color="text-accent-blue">
        <p>{t('learn:strategies.swing.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.swing.bestFor_label')}</span>{t('learn:strategies.swing.bestFor_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.swing.tools_label')}</span>{t('learn:strategies.swing.tools_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:strategies.day.title')} color="text-accent-red">
        <p>{t('learn:strategies.day.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.day.bestFor_label')}</span>{t('learn:strategies.day.bestFor_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.day.warning_label')}</span>{t('learn:strategies.day.warning_desc')}</p>
      </Accordion>
      <Accordion title={t('learn:strategies.onePercent.title')}>
        <p>{t('learn:strategies.onePercent.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.onePercent.example_label')}</span>{t('learn:strategies.onePercent.example_desc')}</p>
        <p>{t('learn:strategies.onePercent.p2')}</p>
      </Accordion>
      <Accordion title={t('learn:strategies.srTrading.title')}>
        <p>{t('learn:strategies.srTrading.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.srTrading.strategy_label')}</span>{t('learn:strategies.srTrading.strategy_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:strategies.srTrading.confirmation_label')}</span>{t('learn:strategies.srTrading.confirmation_desc')}</p>
      </Accordion>
    </div>
  )
}

function RiskManagement() {
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:risk.onePercent.title')} color="text-accent-red">
        <p>{t('learn:risk.onePercent.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:risk.onePercent.p1_bold')}</span>{t('learn:risk.onePercent.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.onePercent.formula_label')}</span>{t('learn:risk.onePercent.formula_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.onePercent.example_title')}</span></p>
        <p>{t('learn:risk.onePercent.example_account')}<span className="text-accent-red font-semibold">{t('learn:risk.onePercent.example_risk')}</span>.</p>
        <p>{t('learn:risk.onePercent.example_entry')}</p>
        <p>{t('learn:risk.onePercent.example_position_prefix')}<span className="text-accent-blue font-semibold">{t('learn:risk.onePercent.example_position_value')}</span>{t('learn:risk.onePercent.example_position_suffix')}</p>
        <p className="text-accent-yellow">{t('learn:risk.onePercent.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.riskReward.title')} color="text-accent-blue">
        <p>{t('learn:risk.riskReward.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.riskReward.minimum_label')}</span>{t('learn:risk.riskReward.minimum_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.riskReward.howTo_label')}</span></p>
        <p>{t('learn:risk.riskReward.howTo_entry')}</p>
        <p>{t('learn:risk.riskReward.howTo_result_prefix')}<span className="text-accent-green font-semibold">{t('learn:risk.riskReward.howTo_result_value')}</span>{t('learn:risk.riskReward.howTo_result_suffix')}</p>
        <p className="text-accent-yellow">{t('learn:risk.riskReward.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.stopLoss.title')} color="text-accent-red">
        <p>{t('learn:risk.stopLoss.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.stopLoss.belowSupport_label')}</span>{t('learn:risk.stopLoss.belowSupport_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.stopLoss.atr_label')}</span>{t('learn:risk.stopLoss.atr_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.stopLoss.neverDo_label')}</span>{t('learn:risk.stopLoss.neverDo_desc')}</p>
        <p className="text-accent-yellow">{t('learn:risk.stopLoss.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.positionSizing.title')} color="text-accent-blue">
        <p>{t('learn:risk.positionSizing.p1')}</p>
        <p className="text-text-secondary font-semibold text-xs">{t('learn:risk.positionSizing.formula')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.positionSizing.example_label')}</span></p>
        <p>{t('learn:risk.positionSizing.example_account')}</p>
        <p>{t('learn:risk.positionSizing.example_entry')}</p>
        <p>{t('learn:risk.positionSizing.example_position_prefix')}<span className="text-accent-blue font-semibold">{t('learn:risk.positionSizing.example_position_value')}</span>{t('learn:risk.positionSizing.example_position_suffix')}</p>
        <p>{t('learn:risk.positionSizing.example_note')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.portfolioHeat.title')} color="text-accent-yellow">
        <p>{t('learn:risk.portfolioHeat.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:risk.portfolioHeat.p1_bold')}</span>{t('learn:risk.portfolioHeat.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.portfolioHeat.max_label')}</span>{t('learn:risk.portfolioHeat.max_desc')}</p>
        <p>{t('learn:risk.portfolioHeat.p3')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.portfolioHeat.correlated_label')}</span>{t('learn:risk.portfolioHeat.correlated_desc')}</p>
        <p className="text-accent-yellow">{t('learn:risk.portfolioHeat.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.leverage.title')} color="text-accent-red">
        <p>{t('learn:risk.leverage.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.leverage.2x')}</span></p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.leverage.5x')}</span></p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.leverage.10x')}</span></p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.leverage.25x')}</span></p>
        <p><span className="text-text-secondary font-semibold">{t('learn:risk.leverage.100x')}</span></p>
        <p className="text-accent-yellow">{t('learn:risk.leverage.safe')}</p>
      </Accordion>

      <Accordion title={t('learn:risk.drawdown.title')} color="text-accent-red">
        <p>{t('learn:risk.drawdown.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:risk.drawdown.p1_bold')}</span>{t('learn:risk.drawdown.p1_suffix')}</p>
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
              <span className="text-accent-red w-16">{t('learn:risk.drawdown.loss', { pct: loss })}</span>
              <span className="text-text-muted">=</span>
              <span className="text-accent-green">{t('learn:risk.drawdown.recovery', { pct: gain })}</span>
            </div>
          ))}
        </div>
        <p className="text-accent-yellow mt-2">{t('learn:risk.drawdown.tip')}</p>
      </Accordion>
    </div>
  )
}

function Psychology() {
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:psychology.fomo.title')} color="text-accent-yellow">
        <p>{t('learn:psychology.fomo.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.fomo.whyDangerous_label')}</span>{t('learn:psychology.fomo.whyDangerous_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.fomo.howToFight_label')}</span></p>
        <p>{t('learn:psychology.fomo.howToFight_1')}</p>
        <p>{t('learn:psychology.fomo.howToFight_2')}</p>
        <p>{t('learn:psychology.fomo.howToFight_3')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.fomo.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.revenge.title')} color="text-accent-red">
        <p>{t('learn:psychology.revenge.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.revenge.whyKiller_label')}</span>{t('learn:psychology.revenge.whyKiller_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.revenge.howToFight_label')}</span></p>
        <p>{t('learn:psychology.revenge.howToFight_1_prefix')}<span className="text-accent-red font-semibold">{t('learn:psychology.revenge.howToFight_1_bold')}</span>{t('learn:psychology.revenge.howToFight_1_suffix')}</p>
        <p>{t('learn:psychology.revenge.howToFight_2')}</p>
        <p>{t('learn:psychology.revenge.howToFight_3')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.revenge.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.confirmation.title')} color="text-accent-yellow">
        <p>{t('learn:psychology.confirmation.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.confirmation.example_label')}</span>{t('learn:psychology.confirmation.example_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.confirmation.howToFight_label')}</span></p>
        <p>{t('learn:psychology.confirmation.howToFight_1')}</p>
        <p>{t('learn:psychology.confirmation.howToFight_2')}</p>
        <p>{t('learn:psychology.confirmation.howToFight_3')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.confirmation.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.overtrading.title')} color="text-accent-blue">
        <p>{t('learn:psychology.overtrading.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.overtrading.signs_label')}</span></p>
        <p>{t('learn:psychology.overtrading.signs_1')}</p>
        <p>{t('learn:psychology.overtrading.signs_2')}</p>
        <p>{t('learn:psychology.overtrading.signs_3')}</p>
        <p>{t('learn:psychology.overtrading.signs_4')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.overtrading.fix_label')}</span>{t('learn:psychology.overtrading.fix_desc')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.tradingPlan.title')} color="text-accent-green">
        <p>{t('learn:psychology.tradingPlan.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:psychology.tradingPlan.p1_bold')}</span>{t('learn:psychology.tradingPlan.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.tradingPlan.must_label')}</span></p>
        <p>1. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_1_label')}</span>{t('learn:psychology.tradingPlan.must_1_desc')}</p>
        <p>2. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_2_label')}</span>{t('learn:psychology.tradingPlan.must_2_desc')}</p>
        <p>3. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_3_label')}</span>{t('learn:psychology.tradingPlan.must_3_desc')}</p>
        <p>4. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_4_label')}</span>{t('learn:psychology.tradingPlan.must_4_desc')}</p>
        <p>5. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_5_label')}</span>{t('learn:psychology.tradingPlan.must_5_desc')}</p>
        <p>6. <span className="text-text-secondary">{t('learn:psychology.tradingPlan.must_6_label')}</span>{t('learn:psychology.tradingPlan.must_6_desc')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.tradingPlan.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.detachment.title')} color="text-accent-blue">
        <p>{t('learn:psychology.detachment.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:psychology.detachment.mindset_label')}</span></p>
        <p>{t('learn:psychology.detachment.mindset_1')}</p>
        <p>{t('learn:psychology.detachment.mindset_2')}</p>
        <p>{t('learn:psychology.detachment.mindset_3')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.detachment.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:psychology.whenNot.title')} color="text-accent-red">
        <p>{t('learn:psychology.whenNot.p1')}</p>
        <p><span className="text-accent-red font-semibold">{t('learn:psychology.whenNot.dontTrade_label')}</span></p>
        <p>{t('learn:psychology.whenNot.dontTrade_1')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_2')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_3')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_4')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_5')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_6')}</p>
        <p>{t('learn:psychology.whenNot.dontTrade_7')}</p>
        <p className="text-accent-yellow">{t('learn:psychology.whenNot.tip')}</p>
      </Accordion>
    </div>
  )
}

function Patterns() {
  const { t } = useTranslation(['learn'])
  return (
    <div className="space-y-2">
      <Accordion title={t('learn:patterns.sr.title')} color="text-accent-green">
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.sr.support_label')}</span>{t('learn:patterns.sr.support_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.sr.resistance_label')}</span>{t('learn:patterns.sr.resistance_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.sr.rules_label')}</span></p>
        <p>{t('learn:patterns.sr.rules_1')}</p>
        <p>{t('learn:patterns.sr.rules_2')}</p>
        <p>{t('learn:patterns.sr.rules_3')}</p>
        <p>{t('learn:patterns.sr.rules_4')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.sr.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.doubleTopBottom.title')} color="text-accent-blue">
        <p>{t('learn:patterns.doubleTopBottom.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:patterns.doubleTopBottom.p1_bold')}</span>{t('learn:patterns.doubleTopBottom.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.doubleTopBottom.doubleTop_label')}</span>{t('learn:patterns.doubleTopBottom.doubleTop_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.doubleTopBottom.doubleBottom_label')}</span>{t('learn:patterns.doubleTopBottom.doubleBottom_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.doubleTopBottom.target_label')}</span>{t('learn:patterns.doubleTopBottom.target_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.doubleTopBottom.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.headShoulders.title')} color="text-accent-blue">
        <p>{t('learn:patterns.headShoulders.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:patterns.headShoulders.p1_bold')}</span>{t('learn:patterns.headShoulders.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.headShoulders.regular_label')}</span>{t('learn:patterns.headShoulders.regular_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.headShoulders.inverse_label')}</span>{t('learn:patterns.headShoulders.inverse_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.headShoulders.target_label')}</span>{t('learn:patterns.headShoulders.target_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.headShoulders.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.triangles.title')} color="text-accent-blue">
        <p>{t('learn:patterns.triangles.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.triangles.ascending_label')}</span>{t('learn:patterns.triangles.ascending_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.triangles.descending_label')}</span>{t('learn:patterns.triangles.descending_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.triangles.symmetrical_label')}</span>{t('learn:patterns.triangles.symmetrical_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.triangles.entry_label')}</span>{t('learn:patterns.triangles.entry_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.triangles.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.flags.title')} color="text-accent-green">
        <p>{t('learn:patterns.flags.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:patterns.flags.p1_bold')}</span>{t('learn:patterns.flags.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.flags.bullFlag_label')}</span>{t('learn:patterns.flags.bullFlag_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.flags.bearFlag_label')}</span>{t('learn:patterns.flags.bearFlag_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.flags.pennant_label')}</span>{t('learn:patterns.flags.pennant_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.flags.target_label')}</span>{t('learn:patterns.flags.target_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.flags.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.cup.title')} color="text-accent-green">
        <p>{t('learn:patterns.cup.p1_prefix')}<span className="text-text-secondary font-semibold">{t('learn:patterns.cup.p1_bold')}</span>{t('learn:patterns.cup.p1_suffix')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.cup.cup_label')}</span>{t('learn:patterns.cup.cup_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.cup.handle_label')}</span>{t('learn:patterns.cup.handle_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.cup.entry_label')}</span>{t('learn:patterns.cup.entry_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.cup.target_label')}</span>{t('learn:patterns.cup.target_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.cup.tip')}</p>
      </Accordion>

      <Accordion title={t('learn:patterns.candlestick.title')} color="text-accent-blue">
        <p>{t('learn:patterns.candlestick.p1')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.candlestick.doji_label')}</span>{t('learn:patterns.candlestick.doji_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.candlestick.hammer_label')}</span>{t('learn:patterns.candlestick.hammer_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.candlestick.shootingStar_label')}</span>{t('learn:patterns.candlestick.shootingStar_desc')}</p>
        <p><span className="text-text-secondary font-semibold">{t('learn:patterns.candlestick.engulfing_label')}</span>{t('learn:patterns.candlestick.engulfing_desc')}</p>
        <p className="text-accent-yellow">{t('learn:patterns.candlestick.tip')}</p>
      </Accordion>
    </div>
  )
}

function Glossary() {
  const { t } = useTranslation(['learn'])
  const termKeys = [
    'ATH', 'ATL', 'Bearish', 'Bullish', 'Candle', 'DCA', 'DeFi', 'DYOR',
    'FOMO', 'FUD', 'Gas', 'Halving', 'HODL', 'Leverage', 'Liquidation',
    'Long', 'MACD', 'MarketCap', 'MVRV', 'OI', 'RSI', 'Satoshi', 'Short',
    'Slippage', 'StopLoss', 'Support', 'Resistance', 'TakeProfit', 'TVL', 'Whale',
  ]

  // Display names for glossary terms (some differ from JSON keys)
  const displayNames = {
    MarketCap: 'Market Cap',
    StopLoss: 'Stop-Loss',
    TakeProfit: 'Take-Profit',
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
      <div className="space-y-1.5">
        {termKeys.map((key) => (
          <div key={key} className="flex gap-2 py-1 border-b border-white/[0.03] last:border-0">
            <span className="text-accent-blue text-[11px] font-bold w-20 flex-shrink-0">{displayNames[key] || key}</span>
            <span className="text-text-muted text-[11px]">{t(`learn:glossary.${key}`)}</span>
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
