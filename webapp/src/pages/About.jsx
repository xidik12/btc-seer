import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

const I = (children, sm) => (
  <svg className={sm ? 'w-4 h-4 text-accent-blue' : 'w-5 h-5 text-accent-blue'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

const BTC_DONATION = '12yRGpUfFznzZoz4yVfZKRxLSkAwbanw2B'
const COMMUNITY_LINK = 'https://t.me/+-72wnR04tPUyZmIy'

export default function About() {
  const { t } = useTranslation(['about', 'common'])
  const [copied, setCopied] = useState(false)
  const tg = window.Telegram?.WebApp

  const openTelegramLink = useCallback((url) => {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(url)
    } else {
      window.open(url, '_blank')
    }
  }, [tg])

  const copyBtc = () => {
    navigator.clipboard.writeText(BTC_DONATION).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }

  const stats = [
    { value: '192', labelKey: 'about:byTheNumbers.features' },
    { value: '4', labelKey: 'about:byTheNumbers.aiModels' },
    { value: '13', labelKey: 'about:byTheNumbers.dataSources' },
    { value: '5', labelKey: 'about:byTheNumbers.timeframes' },
    { value: '24', labelKey: 'about:byTheNumbers.backgroundJobs' },
    { value: '6h', labelKey: 'about:byTheNumbers.retrainCycle' },
  ]

  const steps = [1, 2, 3, 4, 5].map((n) => ({
    num: n,
    label: t(`about:howToUse.step${n}_label`),
    desc: t(`about:howToUse.step${n}_desc`),
  }))

  const models = [
    { nameKey: 'about:architecture.models.tft', weight: '40%', descKey: 'about:architecture.tftDesc', color: 'text-accent-green' },
    { nameKey: 'about:architecture.models.xgboost', weight: '25%', descKey: 'about:architecture.xgboostDesc', color: 'text-accent-blue' },
    { nameKey: 'about:architecture.models.lstm', weight: '20%', descKey: 'about:architecture.lstmDesc', color: 'text-accent-purple' },
    { nameKey: 'about:architecture.models.timesfm', weight: '15%', descKey: 'about:architecture.timesfmDesc', color: 'text-accent-yellow' },
  ]

  const featureCategoryKeys = [
    'technical', 'sentiment', 'derivativesExt', 'exchangeFlows', 'macro',
    'onChain', 'eventMemory', 'etfFlows', 'stablecoin', 'dominance',
    'supplyMining', 'derivatives', 'phraseAnalysis',
  ]

  const aiSteps = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => ({
    num: n,
    label: t(`about:howAiWorks.step${n}_label`),
    desc: t(`about:howAiWorks.step${n}_desc`),
  }))

  const pipelineRaw = t('about:dataPipeline.items', { returnObjects: true })
  const pipelineItems = Array.isArray(pipelineRaw) ? pipelineRaw : []

  const whatsInsideKeys = [
    'dashboard', 'signals', 'advisor', 'technical', 'powerLaw', 'elliottWave',
    'liquidations', 'coins', 'news', 'events', 'history', 'paperTrading',
    'learn', 'tools', 'resources', 'settings', 'premium',
  ]

  return (
    <div className="px-4 pt-4 space-y-3 pb-4">
      {/* Hero */}
      <div className="bg-bg-card rounded-2xl p-5 gradient-border text-center slide-up">
        <img src="/btc-seer.jpeg" alt="BTC Seer" className="w-full rounded-xl mb-4" />
        <h1 className="text-xl font-bold mb-1 text-shimmer-gold">{t('common:app.title')}</h1>
        <p className="text-text-secondary text-sm">{t('about:description')}</p>
        <div className="flex items-center justify-center gap-2 mt-2">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-accent-blue/15 text-accent-blue border border-accent-blue/30">v2.0</span>
          <span className="flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-full bg-accent-green/15 text-accent-green border border-accent-green/30">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-green pulse-glow" />
            {t('common:app.live')}
          </span>
        </div>
        <p className="text-text-muted text-[11px] mt-2">
          {t('about:heroSubtitle')}
        </p>
      </div>

      {/* Incognito Generation Project */}
      <div className="bg-bg-card rounded-2xl p-4 gradient-border">
        <div className="flex items-center gap-3 mb-3">
          <img src="/incognito-generation.png" alt="Incognito Generation" className="w-12 h-12 rounded-lg" />
          <div>
            <h3 className="text-text-primary text-sm font-bold">{t('about:project.title')}</h3>
            <p className="text-text-muted text-[10px]">{t('about:project.subtitle')}</p>
          </div>
        </div>
        <p className="text-text-muted text-[11px]">{t('about:project.description')}</p>
      </div>

      {/* What is BTC Seer */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('about:whatIs.title')}</h3>
        <div className="text-text-muted text-[11px] space-y-2">
          <p dangerouslySetInnerHTML={{ __html: t('about:whatIs.p1') }} />
          <p dangerouslySetInnerHTML={{ __html: t('about:whatIs.p2') }} />
          <p dangerouslySetInnerHTML={{ __html: t('about:whatIs.p3') }} />
        </div>
      </div>

      {/* Self-Learning Prediction System */}
      <div className="bg-bg-card rounded-2xl p-4 gradient-border">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{String(t('about:selfLearning.title')).toUpperCase()}</h3>
        <p className="text-text-muted text-[11px] mb-3">{t('about:selfLearning.intro')}</p>
        <div className="space-y-2 text-[11px] text-text-muted">
          {[1, 2, 3, 4, 5].map((n) => (
            <div key={n} className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-green/20 text-accent-green text-[10px] font-bold flex items-center justify-center">{n}</span>
              <p><span className="text-text-secondary font-semibold">{t(`about:selfLearning.step${n}_label`)}</span>{t(`about:selfLearning.step${n}_desc`)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Time-Aligned Predictions */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{String(t('about:timeAligned.title')).toUpperCase()}</h3>
        <p className="text-text-muted text-[10px] mb-3">{t('about:timeAligned.intro')}</p>
        <div className="space-y-1.5">
          {['1h', '4h', '24h'].map((tf) => (
            <div key={tf} className="flex gap-2 py-1.5 border-b border-white/[0.03] last:border-0">
              <span className="text-accent-blue text-[11px] font-bold w-10 flex-shrink-0">{tf.toUpperCase()}</span>
              <span className="text-text-muted text-[10px]">{t(`about:timeAligned.${tf}`)}</span>
            </div>
          ))}
        </div>
        <p className="text-text-muted text-[10px] mt-2 italic">{t('about:timeAligned.note')}</p>
      </div>

      {/* By the Numbers */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:byTheNumbers.title')}</h3>
        <div className="grid grid-cols-3 gap-2">
          {stats.map((stat) => (
            <div key={stat.labelKey} className="text-center p-2 rounded-xl bg-white/[0.02]">
              <div className="text-accent-blue text-lg font-bold">{stat.value}</div>
              <div className="text-text-muted text-[9px] uppercase tracking-wider">{t(stat.labelKey)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How to Use BTC Seer -- Quick Start */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:howToUse.title')}</h3>
        <p className="text-text-muted text-[10px] mb-3">{t('about:howToUse.subtitle')}</p>
        <div className="space-y-2 text-[11px] text-text-muted">
          {steps.map((step) => (
            <div key={step.num} className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-[10px] font-bold flex items-center justify-center">{step.num}</span>
              <p><span className="text-text-secondary font-semibold">{step.label}</span>{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* AI Ensemble Architecture */}
      <div className="bg-bg-card rounded-2xl p-4 gradient-border">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{String(t('about:architecture.title')).toUpperCase()}</h3>
        <div className="space-y-2">
          {models.map((model) => (
            <div key={model.nameKey} className="p-2.5 rounded-xl bg-white/[0.02]">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-text-primary text-xs font-semibold">{t(model.nameKey)}</span>
                <span className={`text-[10px] font-bold ${model.color}`}>{model.weight}</span>
              </div>
              <p className="text-text-muted text-[10px]">{t(model.descKey)}</p>
            </div>
          ))}
        </div>
        <p className="text-text-muted text-[10px] mt-2">
          {t('about:architecture.adaptiveNote')}
        </p>
      </div>

      {/* 192 Features -- 13 Categories */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:featuresCategories.title')}</h3>
        <div className="space-y-1.5">
          {featureCategoryKeys.map((key) => (
            <div key={key} className="flex gap-2 py-1.5 border-b border-white/[0.03] last:border-0">
              <span className="text-accent-blue text-[10px] font-bold w-28 flex-shrink-0 leading-tight">{t(`about:featuresCategories.${key}.name`)}</span>
              <span className="text-text-muted text-[10px] leading-tight">{t(`about:featuresCategories.${key}.desc`)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Data Pipeline */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:dataPipeline.title')}</h3>
        <div className="space-y-1.5">
          {pipelineItems.map((item, idx) => (
            <div key={idx} className="flex gap-2 py-1 border-b border-white/[0.03] last:border-0">
              <span className="text-accent-green text-[10px] font-bold w-20 flex-shrink-0">{item.freq}</span>
              <span className="text-text-muted text-[10px]">{item.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* How the AI Works */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:howAiWorks.title')}</h3>
        <div className="space-y-2 text-[11px] text-text-muted">
          {aiSteps.map((step) => (
            <div key={step.num} className="flex items-start gap-2">
              <span className="text-accent-blue font-bold text-xs mt-0.5">{step.num}</span>
              <p><span className="text-text-secondary font-semibold">{step.label}</span>{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Helps */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:howItHelps.title')}</h3>
        <div className="space-y-2">
          {[
            { icon: I(<><path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" /></>), titleKey: 'about:features.predictions', descKey: 'about:features.predictionsDesc' },
            { icon: I(<><polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" /></>), titleKey: 'about:features.signals', descKey: 'about:features.signalsDesc' },
            { icon: I(<><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></>), titleKey: 'about:features.advisor', descKey: 'about:features.advisorDesc' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M7 16l4-6 4 4 5-8" /></>), titleKey: 'about:features.technical', descKey: 'about:features.technicalDesc' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M3 17C7 15 11 9 21 5" /></>), titleKey: 'about:features.powerLaw', descKey: 'about:features.powerLawDesc' },
            { icon: I(<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />), titleKey: 'about:features.elliott', descKey: 'about:features.elliottDesc' },
            { icon: I(<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />), titleKey: 'about:features.liquidations', descKey: 'about:features.liquidationsDesc' },
            { icon: I(<><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>), titleKey: 'about:features.news', descKey: 'about:features.newsDesc' },
            { icon: I(<><circle cx="12" cy="12" r="8" /><path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5 1-2.5 2s1 2 2.5 2 2.5 1 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5" /><path d="M12 6.5v1M12 16.5v1" /></>), titleKey: 'about:howItHelps.coinsMarket', descKey: 'about:howItHelps.coinsMarketDesc' },
            { icon: I(<><path d="M12 2c-4 4.5-8 8.5-8 13a8 8 0 0016 0c0-4.5-4-8.5-8-13z" /><path d="M12 18a4 4 0 01-4-4c0-2.5 2-4.5 4-7" /></>), titleKey: 'about:features.onChain', descKey: 'about:features.onChainDesc' },
            { icon: I(<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></>), titleKey: 'about:features.paperTrading', descKey: 'about:features.paperTradingDesc' },
            { icon: I(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>), titleKey: 'about:howItHelps.accuracyTransparency', descKey: 'about:howItHelps.accuracyTransparencyDesc' },
          ].map((item) => (
            <div key={item.titleKey} className="flex items-start gap-3 p-2 rounded-xl bg-white/[0.02]">
              <span className="mt-0.5 shrink-0">{item.icon}</span>
              <div>
                <div className="text-text-primary text-xs font-semibold">{t(item.titleKey)}</div>
                <div className="text-text-muted text-[10px]">{t(item.descKey)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* What's Inside -- All Pages */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{t('about:whatsInside.title')}</h3>
        <div className="space-y-1.5">
          {whatsInsideKeys.map((key) => (
            <div key={key} className="flex gap-2 py-1 border-b border-white/[0.03] last:border-0">
              <span className="text-accent-blue text-[11px] font-bold w-24 flex-shrink-0">{t(`about:whatsInside.${key}.name`)}</span>
              <span className="text-text-muted text-[10px]">{t(`about:whatsInside.${key}.desc`)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Features Grid */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{String(t('about:features.title')).toUpperCase()}</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { icon: I(<><path d="M9 18h6" /><path d="M10 22h4" /><path d="M12 2a7 7 0 00-4 12.9V17h8v-2.1A7 7 0 0012 2z" /></>, true), labelKey: 'about:features.predictions' },
            { icon: I(<><polyline points="22 17 13.5 8.5 8.5 13.5 2 7" /><polyline points="16 17 22 17 22 11" /></>, true), labelKey: 'about:features.quantTheory' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M3 17C7 15 11 9 21 5" /></>, true), labelKey: 'about:features.powerLaw' },
            { icon: I(<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />, true), labelKey: 'about:features.elliott' },
            { icon: I(<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />, true), labelKey: 'about:features.liquidations' },
            { icon: I(<><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>, true), labelKey: 'about:features.news' },
            { icon: I(<><polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" /></>, true), labelKey: 'about:features.signals' },
            { icon: I(<><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></>, true), labelKey: 'about:features.advisor' },
            { icon: I(<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></>, true), labelKey: 'about:features.paperTrading' },
            { icon: I(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>, true), labelKey: 'about:features.accuracyTracking' },
            { icon: I(<><path d="M12 2c-4 4.5-8 8.5-8 13a8 8 0 0016 0c0-4.5-4-8.5-8-13z" /></>, true), labelKey: 'about:features.onChain' },
            { icon: I(<><circle cx="12" cy="12" r="8" /><path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5 1-2.5 2s1 2 2.5 2 2.5 1 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5" /><path d="M12 6.5v1M12 16.5v1" /></>, true), labelKey: 'about:features.coinsTokens' },
            { icon: I(<><path d="M3 3v18h18" /><path d="M7 16l4-6 4 4 5-8" /></>, true), labelKey: 'about:features.technical' },
            { icon: I(<><path d="M12 20V10" /><path d="M18 20V4" /><path d="M6 20v-4" /></>, true), labelKey: 'about:features.etfFlows' },
            { icon: I(<><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z" /><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z" /></>, true), labelKey: 'about:features.learnEducate' },
            { icon: I(<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></>, true), labelKey: 'about:features.eventMemory' },
            { icon: I(<><path d="M4 4h16v16H4z" /><path d="M9 9h6v6H9z" /><path d="M4 9h5M15 9h5M4 15h5M15 15h5M9 4v5M9 15v5M15 4v5M15 15v5" /></>, true), labelKey: 'about:features.selfLearning' },
          ].map((f) => (
            <div key={f.labelKey} className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02]">
              <span className="shrink-0">{f.icon}</span>
              <span className="text-text-primary text-xs font-medium">{t(f.labelKey)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Creator + Project + Community */}
      <div className="bg-bg-card rounded-2xl p-4 gradient-border">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">{String(t('about:credits.title')).toUpperCase()}</h3>
        <div className="text-text-muted text-[11px] space-y-3">
          <div className="flex items-center gap-3">
            <img src="/incognito-generation.png" alt="Incognito Generation" className="w-10 h-10 rounded-lg" />
            <div>
              <p dangerouslySetInnerHTML={{ __html: t('about:credits.createdBy') }} />
              <p className="text-[10px] mt-0.5">{t('about:credits.projectNote')}</p>
            </div>
          </div>
          <p>{t('about:credits.builtWith')}</p>

          {/* Community + Bot buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => openTelegramLink(COMMUNITY_LINK)}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-accent-blue/10 text-accent-blue text-[11px] font-semibold border border-accent-blue/20"
            >
              {t('about:credits.joinCounsil')}
            </button>
            <button
              onClick={() => openTelegramLink('https://t.me/btc_seer_bot')}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-white/5 text-text-secondary text-[11px] font-semibold border border-white/10"
            >
              {t('about:credits.joinTelegram')}
            </button>
          </div>
        </div>
      </div>

      {/* BTC Donation */}
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-yellow/15">
        <h3 className="text-accent-yellow text-xs font-semibold mb-2">{String(t('about:donate.title')).toUpperCase()}</h3>
        <p className="text-text-muted text-[10px] mb-3">{t('about:donate.description')}</p>
        <div
          onClick={copyBtc}
          className="flex items-center gap-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/5 cursor-pointer hover:border-accent-yellow/30 transition-colors"
        >
          <span className="text-accent-yellow text-sm">&#8383;</span>
          <span className="text-text-primary text-[10px] font-mono break-all flex-1">{BTC_DONATION}</span>
          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full transition-all ${
            copied
              ? 'bg-accent-green/15 text-accent-green'
              : 'bg-white/5 text-text-muted'
          }`}>
            {copied ? t('about:donate.copied') : t('about:donate.copy')}
          </span>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-bg-card rounded-2xl p-4 border border-accent-red/10">
        <h3 className="text-accent-red text-xs font-semibold mb-2">{String(t('about:disclaimer.title')).toUpperCase()}</h3>
        <p className="text-text-muted text-[10px]">
          {t('about:disclaimer.text')}
        </p>
      </div>
    </div>
  )
}
