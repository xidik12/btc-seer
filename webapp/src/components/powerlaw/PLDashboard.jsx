import { useTranslation } from 'react-i18next'

function StatCard({ label, value, subtext, color }) {
  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5">
      <div className="text-text-muted text-[9px] font-medium mb-1">{label}</div>
      <div className={`text-sm font-bold tabular-nums ${color || 'text-text-primary'}`}>{value}</div>
      {subtext && <div className="text-text-muted text-[9px] mt-0.5">{subtext}</div>}
    </div>
  )
}

function ProjectionCard({ label, value }) {
  return (
    <div className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
      <div className="text-text-muted text-[9px] font-medium mb-1">{label}</div>
      <div className="text-accent-blue text-sm font-bold tabular-nums">
        ${typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}

export default function PLDashboard({ data }) {
  const { t } = useTranslation(['market', 'common'])

  if (!data || data.error) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  const priceColor = data.change_24h >= 0 ? 'text-accent-green' : 'text-accent-red'
  const deviationColor = data.deviation_pct >= 0 ? 'text-accent-red' : 'text-accent-green'

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
          <div className="text-right">
            <div className="text-text-muted text-[10px]">{t('market:powerLaw.dashboard.modelPrice')}</div>
            <div className="text-accent-blue text-2xl font-bold tabular-nums">
              ${data.model_price?.toLocaleString()}
            </div>
            <div className={`text-xs font-medium ${deviationColor}`}>
              {data.deviation_pct > 0 ? '+' : ''}{data.deviation_pct?.toFixed(1)}%
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid 4x2 */}
      <div className="grid grid-cols-4 gap-2">
        <StatCard
          label={t('market:powerLaw.dashboard.multiplier')}
          value={`${data.multiplier?.toFixed(2)}x`}
          color={data.multiplier > 1 ? 'text-accent-yellow' : 'text-accent-green'}
        />
        <StatCard
          label={t('market:powerLaw.dashboard.slope')}
          value={data.slope?.toFixed(3)}
        />
        <StatCard
          label={t('market:powerLaw.dashboard.rSquared')}
          value={data.r_squared?.toFixed(3)}
          color="text-accent-green"
        />
        <StatCard
          label={t('market:powerLaw.dashboard.logVol')}
          value={data.log_volatility?.toFixed(2)}
        />
        <StatCard
          label={t('market:powerLaw.dashboard.cagr')}
          value={`${data.cagr?.toFixed(0)}%`}
          color="text-accent-green"
        />
        <StatCard
          label={t('market:powerLaw.dashboard.daysGenesis')}
          value={data.days_since_genesis?.toLocaleString()}
        />
        <StatCard
          label={t('market:powerLaw.dashboard.intercept')}
          value={data.intercept?.toFixed(3)}
        />
        <StatCard
          label={t('market:powerLaw.dashboard.deviation')}
          value={`${data.deviation_pct > 0 ? '+' : ''}${data.deviation_pct?.toFixed(1)}%`}
          color={deviationColor}
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
            />
          ))}
        </div>
      </div>

      {/* Milestones */}
      {data.milestones && Object.keys(data.milestones).length > 0 && (
        <div>
          <h3 className="text-text-secondary text-xs font-semibold mb-2">
            {t('market:powerLaw.dashboard.milestones')}
          </h3>
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
