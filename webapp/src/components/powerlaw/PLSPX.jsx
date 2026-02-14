import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { safeFixed } from '../../utils/format'
import CalculationModal, { ClickableStat } from './CalculationModal'

export default function PLSPX({ data }) {
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

  const multColor = data.multiplier >= 1 ? 'text-accent-yellow' : 'text-accent-green'
  const calcs = data.calculations || {}

  return (
    <div className="space-y-3">
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div
            className={calcs.ratio ? 'cursor-pointer hover:opacity-80 active:scale-[0.98] transition-all' : ''}
            onClick={() => showCalc('ratio', t('market:powerLaw.spx.btcSpxRatio'))}
          >
            <div className="text-text-muted text-[10px] flex items-center gap-1">
              {t('market:powerLaw.spx.btcSpxRatio')}
              {calcs.ratio && (
                <svg className="w-2.5 h-2.5 text-accent-blue/40" viewBox="0 0 10 10" fill="none">
                  <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
                  <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
                </svg>
              )}
            </div>
            <div className="text-accent-blue text-2xl font-bold tabular-nums">
              {safeFixed(data.btc_spx_ratio, 2)}x
            </div>
          </div>
          <div
            className={`text-right ${calcs.model_ratio ? 'cursor-pointer hover:opacity-80 active:scale-[0.98] transition-all' : ''}`}
            onClick={() => showCalc('model_ratio', t('market:powerLaw.spx.modelRatio'))}
          >
            <div className="text-text-muted text-[10px] flex items-center justify-end gap-1">
              {t('market:powerLaw.spx.modelRatio')}
              {calcs.model_ratio && (
                <svg className="w-2.5 h-2.5 text-accent-blue/40" viewBox="0 0 10 10" fill="none">
                  <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1"/>
                  <text x="5" y="7.5" textAnchor="middle" fill="currentColor" fontSize="7" fontFamily="monospace">?</text>
                </svg>
              )}
            </div>
            <div className="text-text-secondary text-2xl font-bold tabular-nums">
              {safeFixed(data.model_ratio, 2)}x
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted">{t('market:powerLaw.spx.spxPrice')}: ${data.spx_price?.toLocaleString()}</span>
          <span
            className={`font-bold ${multColor} ${calcs.multiplier ? 'cursor-pointer hover:opacity-80' : ''}`}
            onClick={() => showCalc('multiplier', t('market:powerLaw.dashboard.multiplier'))}
          >
            {safeFixed(data.multiplier, 2)}x
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <ClickableStat
          label={t('market:powerLaw.dashboard.rSquared')}
          value={safeFixed(data.r_squared, 3)}
          color="text-accent-green"
          calcKey="r_squared"
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
          label={t('market:powerLaw.dashboard.logVol')}
          value={safeFixed(data.log_volatility, 2)}
          calcKey="log_volatility"
          calculations={calcs}
          onShowCalc={showCalc}
        />
      </div>

      {data.projections && (
        <div>
          <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('market:powerLaw.dashboard.projections')}</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.projections).map(([key, val]) => (
              <div key={key} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
                <div className="text-text-muted text-[9px] mb-1">{key.replace('dec_', 'Dec ')}</div>
                <div className="text-accent-blue text-sm font-bold">{safeFixed(val, 1)}x</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.milestones && Object.keys(data.milestones).length > 0 && (
        <div>
          <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('market:powerLaw.dashboard.milestones')}</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.milestones).map(([target, date]) => (
              <div key={target} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
                <div className="text-accent-yellow text-sm font-bold">{target}</div>
                <div className="text-text-muted text-[10px] mt-1">{t('market:powerLaw.dashboard.expected')}</div>
                <div className="text-text-secondary text-xs font-medium">{date}</div>
              </div>
            ))}
          </div>
        </div>
      )}

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
