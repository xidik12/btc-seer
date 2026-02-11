import { useTranslation } from 'react-i18next'
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'

export default function PLCurve({ data }) {
  const { t } = useTranslation(['market', 'common'])

  if (!data || !data.points?.length) {
    return (
      <div className="bg-bg-card rounded-2xl p-6 border border-white/5 text-center">
        <p className="text-text-muted text-sm">{t('common:widget.noData')}</p>
      </div>
    )
  }

  // Filter to every 2nd point for performance
  const chartData = data.points.filter((_, i) => i % 2 === 0).map(p => ({
    date: p.date,
    model: p.model,
    lower: p.lower,
    upper: p.upper,
    actual: p.actual,
  }))

  const todayDate = data.today?.date

  return (
    <div className="space-y-3">
      {/* Today Summary */}
      {data.today && (
        <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-text-muted text-[10px]">{t('market:powerLaw.curve.todayModel')}</div>
              <div className="text-accent-blue text-lg font-bold tabular-nums">
                ${data.today.model_price?.toLocaleString()}
              </div>
            </div>
            <div className="text-right">
              <div className="text-text-muted text-[10px]">{t('market:powerLaw.curve.todayActual')}</div>
              <div className="text-accent-yellow text-lg font-bold tabular-nums">
                ${data.today.actual_price?.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">
          {t('market:powerLaw.curve.title')}
        </h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#888' }}
              tickFormatter={v => v?.slice(0, 4)}
              interval={Math.floor(chartData.length / 8)}
            />
            <YAxis
              tick={{ fontSize: 9, fill: '#888' }}
              tickFormatter={v => {
                if (v >= 1000000) return `$${(v / 1000000).toFixed(0)}M`
                if (v >= 1000) return `$${(v / 1000).toFixed(0)}k`
                return `$${v}`
              }}
              scale="log"
              domain={['auto', 'auto']}
              allowDataOverflow
            />
            <Tooltip
              contentStyle={{
                background: '#1a1a2e',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                fontSize: 11,
              }}
              formatter={(v, name) => {
                if (v == null) return ['--', name]
                return [`$${Number(v).toLocaleString()}`, name]
              }}
              labelFormatter={l => l}
            />
            {/* Upper band (red) */}
            <Line
              dataKey="upper"
              stroke="#ff4d6a"
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name={t('market:powerLaw.curve.upperBand')}
            />
            {/* Model line (blue/white) */}
            <Line
              dataKey="model"
              stroke="#4a9eff"
              strokeWidth={2}
              dot={false}
              name={t('market:powerLaw.curve.modelLine')}
            />
            {/* Lower band (green) */}
            <Line
              dataKey="lower"
              stroke="#00c853"
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name={t('market:powerLaw.curve.lowerBand')}
            />
            {/* Actual price (yellow) */}
            <Line
              dataKey="actual"
              stroke="#ffc107"
              strokeWidth={1.5}
              dot={false}
              name={t('market:powerLaw.curve.actualPrice')}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mt-2 justify-center">
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-[#4a9eff] inline-block" /> {t('market:powerLaw.curve.modelLine')}
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-[#ffc107] inline-block" /> {t('market:powerLaw.curve.actualPrice')}
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-[#00c853] inline-block" /> {t('market:powerLaw.curve.lowerBand')}
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-[#ff4d6a] inline-block" /> {t('market:powerLaw.curve.upperBand')}
          </span>
        </div>
      </div>
    </div>
  )
}
