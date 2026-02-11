import { useTranslation } from 'react-i18next'

function getReturnColor(val) {
  if (val === undefined || val === null) return 'text-text-muted'
  if (val > 100) return 'text-accent-green'
  if (val > 0) return 'text-accent-green/70'
  if (val === 0) return 'text-text-muted'
  if (val > -20) return 'text-accent-red/70'
  return 'text-accent-red'
}

function getReturnBg(val) {
  if (val === undefined || val === null) return ''
  if (val > 100) return 'bg-accent-green/10'
  if (val > 0) return 'bg-accent-green/5'
  if (val < -20) return 'bg-accent-red/10'
  if (val < 0) return 'bg-accent-red/5'
  return ''
}

export default function PLAssets({ data }) {
  const { t } = useTranslation(['market', 'common'])

  if (!data || data.error || !data.years?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  const assetNames = Object.keys(data.assets)

  return (
    <div className="space-y-3">
      {/* Win Count Summary */}
      <div className="grid grid-cols-4 gap-2">
        {assetNames.map(name => {
          const asset = data.assets[name]
          const wins = data.win_counts?.[name] || 0
          return (
            <div key={name} className="bg-bg-card rounded-xl p-3 border border-white/5 text-center">
              <div className="text-[9px] font-medium mb-1" style={{ color: asset.color }}>{name}</div>
              <div className="text-text-primary text-lg font-bold">{wins}</div>
              <div className="text-text-muted text-[9px]">
                {t('market:powerLaw.assets.winsOf', { count: wins, total: data.total_years })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Returns Table */}
      <div className="bg-bg-card rounded-2xl border border-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-2 py-2 text-text-muted font-medium sticky left-0 bg-bg-card z-10">
                  {t('market:powerLaw.assets.year')}
                </th>
                {assetNames.map(name => (
                  <th key={name} className="px-2 py-2 text-center font-medium" style={{ color: data.assets[name].color }}>
                    {name}
                  </th>
                ))}
                <th className="px-2 py-2 text-center text-text-muted font-medium">
                  {t('market:powerLaw.assets.winner')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.years.map((year, i) => {
                const winner = data.yearly_winners?.[i]
                return (
                  <tr key={year} className="border-b border-white/3 last:border-0">
                    <td className="px-2 py-1.5 text-text-secondary font-medium sticky left-0 bg-bg-card z-10">{year}</td>
                    {assetNames.map(name => {
                      const ret = data.assets[name]?.returns?.[i]
                      const isWinner = winner?.winner === name
                      return (
                        <td
                          key={name}
                          className={`px-2 py-1.5 text-center tabular-nums ${getReturnColor(ret)} ${getReturnBg(ret)} ${isWinner ? 'font-bold' : ''}`}
                        >
                          {ret != null ? `${ret > 0 ? '+' : ''}${ret}%` : '--'}
                        </td>
                      )
                    })}
                    <td className="px-2 py-1.5 text-center text-[9px]" style={{ color: data.assets[winner?.winner]?.color }}>
                      {winner?.winner || '--'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
