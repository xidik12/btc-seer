import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../utils/api'

export default function PLCalculator() {
  const { t } = useTranslation(['market', 'common'])
  const [expenses, setExpenses] = useState(3000)
  const [years, setYears] = useState(30)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [apr, setApr] = useState(4)
  const [ltv, setLtv] = useState(50)
  const [inflation, setInflation] = useState(3)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const calculate = async () => {
    setLoading(true)
    try {
      const data = await api.getPowerLawCalculator({
        monthly_expenses: expenses,
        years,
        apr,
        ltv,
        inflation,
      })
      setResult(data)
    } catch (err) {
      console.error('Calculator error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      {/* Input Form */}
      <div className="bg-bg-card rounded-2xl p-4 border border-white/5">
        <h3 className="text-text-secondary text-xs font-semibold mb-3">
          {t('market:powerLaw.calculator.title')}
        </h3>

        <div className="space-y-3">
          <div>
            <label className="text-text-muted text-[10px] block mb-1">{t('market:powerLaw.calculator.monthlyExpenses')}</label>
            <input
              type="number"
              value={expenses}
              onChange={e => setExpenses(Number(e.target.value))}
              className="w-full bg-bg-primary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-blue focus:outline-none"
            />
          </div>
          <div>
            <label className="text-text-muted text-[10px] block mb-1">{t('market:powerLaw.calculator.years')}</label>
            <input
              type="number"
              value={years}
              onChange={e => setYears(Number(e.target.value))}
              min={5}
              max={50}
              className="w-full bg-bg-primary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-blue focus:outline-none"
            />
          </div>

          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-accent-blue text-[10px] hover:underline"
          >
            {showAdvanced ? t('market:powerLaw.calculator.hideAdvanced') : t('market:powerLaw.calculator.showAdvanced')}
          </button>

          {showAdvanced && (
            <div className="space-y-3 border-t border-white/5 pt-3">
              <div>
                <label className="text-text-muted text-[10px] block mb-1">{t('market:powerLaw.calculator.apr')} (%)</label>
                <input type="number" value={apr} onChange={e => setApr(Number(e.target.value))} min={0} max={30} step={0.5}
                  className="w-full bg-bg-primary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-blue focus:outline-none" />
              </div>
              <div>
                <label className="text-text-muted text-[10px] block mb-1">{t('market:powerLaw.calculator.ltv')} (%)</label>
                <input type="number" value={ltv} onChange={e => setLtv(Number(e.target.value))} min={10} max={90}
                  className="w-full bg-bg-primary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-blue focus:outline-none" />
              </div>
              <div>
                <label className="text-text-muted text-[10px] block mb-1">{t('market:powerLaw.calculator.inflation')} (%)</label>
                <input type="number" value={inflation} onChange={e => setInflation(Number(e.target.value))} min={0} max={20} step={0.5}
                  className="w-full bg-bg-primary border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-blue focus:outline-none" />
              </div>
            </div>
          )}

          <button
            onClick={calculate}
            disabled={loading}
            className="w-full bg-accent-blue text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-blue/90 disabled:opacity-50 transition-colors"
          >
            {loading ? t('common:loading') : t('market:powerLaw.calculator.calculate')}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <>
          <div className="bg-bg-card rounded-2xl p-4 border border-accent-blue/20">
            <div className="text-center">
              <div className="text-text-muted text-[10px] mb-1">{t('market:powerLaw.calculator.btcNeeded')}</div>
              <div className="text-accent-blue text-3xl font-bold tabular-nums">
                {result.btc_needed?.toFixed(4)} BTC
              </div>
              <div className="text-text-muted text-xs mt-1">
                ≈ ${result.btc_value_usd?.toLocaleString()} @ ${result.current_btc_price?.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Timeline */}
          {result.timeline?.length > 0 && (
            <div className="bg-bg-card rounded-2xl border border-white/5 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="px-2 py-2 text-left text-text-muted">{t('market:powerLaw.calculator.yearCol')}</th>
                      <th className="px-2 py-2 text-right text-text-muted">{t('market:powerLaw.calculator.btcPriceCol')}</th>
                      <th className="px-2 py-2 text-right text-text-muted">{t('market:powerLaw.calculator.valueCol')}</th>
                      <th className="px-2 py-2 text-right text-text-muted">{t('market:powerLaw.calculator.surplusCol')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.timeline.filter((_, i) => i % 5 === 0 || i === result.timeline.length - 1).map(row => (
                      <tr key={row.year} className="border-b border-white/3 last:border-0">
                        <td className="px-2 py-1.5 text-text-secondary">{row.date}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums text-text-primary">
                          ${row.btc_price?.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </td>
                        <td className="px-2 py-1.5 text-right tabular-nums text-accent-blue">
                          ${row.btc_value?.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </td>
                        <td className={`px-2 py-1.5 text-right tabular-nums ${row.surplus >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                          ${row.surplus?.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
