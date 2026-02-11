import { useTranslation } from 'react-i18next'

export default function PLM2({ data }) {
  const { t } = useTranslation(['market', 'common'])

  if (!data || data.error) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  const multColor = data.multiplier >= 1 ? 'text-accent-yellow' : 'text-accent-green'

  return (
    <div className="space-y-3">
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-text-muted text-[10px]">{t('market:powerLaw.m2.btcM2Index')}</div>
            <div className="text-accent-blue text-2xl font-bold tabular-nums">
              {data.btc_m2_index?.toLocaleString(undefined, {maximumFractionDigits: 0})}
            </div>
          </div>
          <div className="text-right">
            <div className="text-text-muted text-[10px]">{t('market:powerLaw.m2.modelIndex')}</div>
            <div className="text-text-secondary text-2xl font-bold tabular-nums">
              {data.model_index?.toLocaleString(undefined, {maximumFractionDigits: 0})}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted">{t('market:powerLaw.m2.m2Supply')}: ${data.m2_supply_trillions?.toFixed(1)}T</span>
          <span className={`font-bold ${multColor}`}>{data.multiplier?.toFixed(2)}x</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] mb-1">{t('market:powerLaw.dashboard.rSquared')}</div>
          <div className="text-accent-green text-sm font-bold">{data.r_squared?.toFixed(3)}</div>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] mb-1">{t('market:powerLaw.gold.btcPrice')}</div>
          <div className="text-text-primary text-sm font-bold">${data.btc_price?.toLocaleString()}</div>
        </div>
        <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
          <div className="text-text-muted text-[9px] mb-1">{t('market:powerLaw.dashboard.multiplier')}</div>
          <div className={`text-sm font-bold ${multColor}`}>{data.multiplier?.toFixed(4)}</div>
        </div>
      </div>

      {data.projections && (
        <div>
          <h3 className="text-text-secondary text-xs font-semibold mb-2">{t('market:powerLaw.dashboard.projections')}</h3>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(data.projections).map(([key, val]) => (
              <div key={key} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
                <div className="text-text-muted text-[9px] mb-1">{key.replace('dec_', 'Dec ')}</div>
                <div className="text-accent-blue text-sm font-bold">{val?.toLocaleString()}</div>
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
    </div>
  )
}
