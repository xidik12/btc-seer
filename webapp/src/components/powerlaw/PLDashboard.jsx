import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { safeFixed } from '../../utils/format'
import CalculationModal, { ClickableStat } from './CalculationModal'

function ProjectionCard({ label, value, calcKey, calculations, onShowCalc }) {
  const hasCalc = calculations && calcKey && calculations[calcKey]

  return (
    <div
      className={`bg-bg-card rounded-xl p-3 border border-white/5 text-center ${hasCalc ? 'cursor-pointer hover:border-accent-blue/30 hover:bg-white/[0.02] active:scale-[0.98] transition-all' : ''}`}
      onClick={() => hasCalc && onShowCalc(calcKey, label)}
    >
      <div className="flex items-center justify-center gap-1">
        <div className="text-text-muted text-[9px] font-medium mb-1">{label}</div>
        {hasCalc && (
          <svg className="w-2.5 h-2.5 text-accent-blue/40 mb-1 shrink-0" viewBox="0 0 10 10" fill="none">
            <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
            <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
          </svg>
        )}
      </div>
      <div className="text-accent-blue text-sm font-bold tabular-nums">
        ${typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}

export default function PLDashboard({ data }) {
  const { t } = useTranslation(['market', 'common'])
  const [activeCalc, setActiveCalc] = useState(null)
  const [activeLabel, setActiveLabel] = useState('')

  const showCalc = (key, label) => {
    if (data?.calculations?.[key]) {
      setActiveCalc(data.calculations[key])
      setActiveLabel(label)
    }
  }

  if (!data || data.error) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  const priceColor = data.change_24h >= 0 ? 'text-accent-green' : 'text-accent-red'
  const deviationColor = data.deviation_pct >= 0 ? 'text-accent-red' : 'text-accent-green'
  const calcs = data.calculations || {}

  return (
    <div className="space-y-3">
      {/* Price Header */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-text-muted text-[10px]">{t('market:powerLaw.dashboard.btcPrice')}</div>
            <div className="text-text-primary text-2xl font-bold tabular-nums">
              ${data.current_price?.toLocaleString()}
            </div>
            {data.change_24h != null && (
              <div className={`text-xs font-medium ${priceColor}`}>
                {data.change_24h > 0 ? '+' : ''}{data.change_24h}% 24h
              </div>
            )}
          </div>
          <div
            className={`text-right ${calcs.model_price ? 'cursor-pointer hover:opacity-80 active:scale-[0.98] transition-all' : ''}`}
            onClick={() => showCalc('model_price', t('market:powerLaw.dashboard.modelPrice'))}
          >
            <div className="text-text-muted text-[10px] flex items-center justify-end gap-1">
              {t('market:powerLaw.dashboard.modelPrice')}
              {calcs.model_price && (
                <svg className="w-2.5 h-2.5 text-accent-blue/40" viewBox="0 0 10 10" fill="none">
                  <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
                  <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
                </svg>
              )}
            </div>
            <div className="text-accent-blue text-2xl font-bold tabular-nums">
              ${data.model_price?.toLocaleString()}
            </div>
            <div
              className={`text-xs font-medium ${deviationColor} ${calcs.deviation_pct ? 'cursor-pointer' : ''}`}
              onClick={(e) => { e.stopPropagation(); showCalc('deviation_pct', t('market:powerLaw.dashboard.deviation')) }}
            >
              {data.deviation_pct > 0 ? '+' : ''}{safeFixed(data.deviation_pct, 1)}%
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid 4x2 */}
      <div className="grid grid-cols-4 gap-2">
        <ClickableStat
          label={t('market:powerLaw.dashboard.multiplier')}
          value={`${safeFixed(data.multiplier, 2)}x`}
          color={data.multiplier > 1 ? 'text-accent-yellow' : 'text-accent-green'}
          calcKey="multiplier"
          calculations={calcs}
          onShowCalc={showCalc}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.slope')}
          value={safeFixed(data.slope, 3)}
          calcKey="slope"
          calculations={calcs}
          onShowCalc={showCalc}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.rSquared')}
          value={safeFixed(data.r_squared, 3)}
          color="text-accent-green"
          calcKey="r_squared"
          calculations={calcs}
          onShowCalc={showCalc}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.logVol')}
          value={safeFixed(data.log_volatility, 2)}
          calcKey="log_volatility"
          calculations={calcs}
          onShowCalc={showCalc}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.cagr')}
          value={`${safeFixed(data.cagr, 0)}%`}
          color="text-accent-green"
          calcKey="cagr"
          calculations={calcs}
          onShowCalc={showCalc}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.daysGenesis')}
          value={data.days_since_genesis?.toLocaleString()}
          calculations={{}}
          onShowCalc={() => {}}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.intercept')}
          value={safeFixed(data.intercept, 3)}
          calculations={{}}
          onShowCalc={() => {}}
        />
        <ClickableStat
          label={t('market:powerLaw.dashboard.deviation')}
          value={`${data.deviation_pct > 0 ? '+' : ''}${safeFixed(data.deviation_pct, 1)}%`}
          color={deviationColor}
          calcKey="deviation_pct"
          calculations={calcs}
          onShowCalc={showCalc}
        />
      </div>

      {/* Projections */}
      <div>
        <h3 className="text-text-secondary text-xs font-semibold mb-2">
          {t('market:powerLaw.dashboard.projections')}
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {data.projections && Object.entries(data.projections).map(([key, val]) => (
            <ProjectionCard
              key={key}
              label={key.replace('dec_', 'Dec ')}
              value={val}
              calcKey={`proj_${key}`}
              calculations={calcs}
              onShowCalc={showCalc}
            />
          ))}
        </div>
      </div>

      {/* Milestones — trendline + earliest (at 4x) like b1m.io */}
      {data.milestones && Object.keys(data.milestones).length > 0 && (
        <div>
          <h3 className="text-text-secondary text-xs font-semibold mb-2">
            {t('market:powerLaw.dashboard.milestones')}
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.milestones).map(([target, milestone]) => {
              const trendline = typeof milestone === 'object' ? milestone.trendline : milestone
              const earliest = typeof milestone === 'object' ? milestone.earliest : null
              const numTarget = target.replace(/[$,]/g, '')
              const trendCalcKey = `milestone_${numTarget}_trendline`
              const earliestCalcKey = `milestone_${numTarget}_earliest`
              const hasTrendCalc = calcs[trendCalcKey]
              const hasEarliestCalc = calcs[earliestCalcKey]
              return (
                <div key={target} className="contents">
                  {/* Trendline date */}
                  <div
                    className={`bg-bg-card rounded-xl p-3 border border-white/5 text-center ${hasTrendCalc ? 'cursor-pointer hover:border-accent-blue/30 hover:bg-white/[0.02] active:scale-[0.98] transition-all' : ''}`}
                    onClick={() => hasTrendCalc && showCalc(trendCalcKey, `${target} ${t('market:powerLaw.dashboard.trendline')}`)}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <div className="text-accent-yellow text-sm font-bold">{target} {t('market:powerLaw.dashboard.trendline')}</div>
                      {hasTrendCalc && (
                        <svg className="w-2.5 h-2.5 text-accent-blue/40 shrink-0" viewBox="0 0 10 10" fill="none">
                          <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
                          <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
                        </svg>
                      )}
                    </div>
                    <div className="text-text-muted text-[10px] mt-1">{t('market:powerLaw.dashboard.powerLawDate')}</div>
                    <div className="text-text-secondary text-xs font-medium">{trendline}</div>
                  </div>
                  {/* Earliest date (at 4x upper band) */}
                  {earliest && (
                    <div
                      className={`bg-bg-card rounded-xl p-3 border border-white/5 text-center ${hasEarliestCalc ? 'cursor-pointer hover:border-accent-blue/30 hover:bg-white/[0.02] active:scale-[0.98] transition-all' : ''}`}
                      onClick={() => hasEarliestCalc && showCalc(earliestCalcKey, `${t('market:powerLaw.dashboard.earliest')} ${target}`)}
                    >
                      <div className="flex items-center justify-center gap-1">
                        <div className="text-accent-green text-sm font-bold">{t('market:powerLaw.dashboard.earliest')} {target}</div>
                        {hasEarliestCalc && (
                          <svg className="w-2.5 h-2.5 text-accent-blue/40 shrink-0" viewBox="0 0 10 10" fill="none">
                            <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
                            <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
                          </svg>
                        )}
                      </div>
                      <div className="text-text-muted text-[10px] mt-1">{t('market:powerLaw.dashboard.at4xTrend')}</div>
                      <div className="text-text-secondary text-xs font-medium">{earliest}</div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Calculation Modal */}
      {activeCalc && (
        <CalculationModal
          calc={activeCalc}
          label={activeLabel}
          onClose={() => setActiveCalc(null)}
        />
      )}
    </div>
  )
}
