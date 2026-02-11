import { useTranslation } from 'react-i18next'

const CATEGORY_COLORS = {
  genesis: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', dot: 'bg-purple-500' },
  adoption: { bg: 'bg-accent-green/10', border: 'border-accent-green/30', dot: 'bg-accent-green' },
  price: { bg: 'bg-accent-blue/10', border: 'border-accent-blue/30', dot: 'bg-accent-blue' },
  halving: { bg: 'bg-[#f7931a]/10', border: 'border-[#f7931a]/30', dot: 'bg-[#f7931a]' },
  crisis: { bg: 'bg-accent-red/10', border: 'border-accent-red/30', dot: 'bg-accent-red' },
  institutional: { bg: 'bg-[#ffd700]/10', border: 'border-[#ffd700]/30', dot: 'bg-[#ffd700]' },
  technical: { bg: 'bg-text-muted/10', border: 'border-text-muted/30', dot: 'bg-text-muted' },
}

function MilestoneCard({ milestone }) {
  const colors = CATEGORY_COLORS[milestone.category] || CATEGORY_COLORS.technical
  const priceStr = milestone.price > 0
    ? milestone.price >= 1000
      ? `$${milestone.price.toLocaleString()}`
      : `$${milestone.price}`
    : 'Pre-market'

  return (
    <div className={`rounded-xl p-3 border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between mb-1">
        <div className="text-text-primary text-xs font-bold">{milestone.title}</div>
        <div className="text-text-muted text-[9px] whitespace-nowrap ml-2">{milestone.date}</div>
      </div>
      <div className="text-text-muted text-[10px] mb-2">{milestone.significance}</div>
      <div className="flex items-center justify-between">
        <span className={`text-[9px] px-1.5 py-0.5 rounded ${colors.bg} ${colors.border} border`}>
          {milestone.category}
        </span>
        <span className="text-text-secondary text-[10px] font-medium tabular-nums">{priceStr}</span>
      </div>
      {milestone.driver && (
        <div className="text-text-muted text-[9px] mt-1.5 italic">{milestone.driver}</div>
      )}
    </div>
  )
}

export default function PLMilestones({ data }) {
  const { t } = useTranslation(['market', 'common'])

  if (!data || data.error || !data.milestones?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-2">
          {t('market:powerLaw.milestones.title')}
        </h3>
        <div className="flex flex-wrap gap-2">
          {data.categories?.map(cat => {
            const colors = CATEGORY_COLORS[cat] || CATEGORY_COLORS.technical
            const count = data.by_category?.[cat]?.length || 0
            return (
              <span key={cat} className={`text-[9px] px-2 py-1 rounded-full border ${colors.bg} ${colors.border}`}>
                {cat} ({count})
              </span>
            )
          })}
        </div>
      </div>

      {/* Timeline */}
      <div className="relative pl-4">
        <div className="absolute left-1.5 top-0 bottom-0 w-px bg-white/10" />
        <div className="space-y-3">
          {data.milestones.map((m, i) => {
            const colors = CATEGORY_COLORS[m.category] || CATEGORY_COLORS.technical
            return (
              <div key={i} className="relative">
                <div className={`absolute -left-2.5 top-3 w-2 h-2 rounded-full ${colors.dot}`} />
                <MilestoneCard milestone={m} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
