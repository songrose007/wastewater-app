import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { CalculationResult, UnitParams, ParameterOverrides } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import ParameterEditor from '../components/ParameterEditor'
import PresetSelector from '../components/PresetSelector'

export default function CalculationPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [results, setResults] = useState<CalculationResult[]>([])
  const [designParams, setDesignParams] = useState<UnitParams[]>([])
  const [overrides, setOverrides] = useState<ParameterOverrides>({})
  const [showParams, setShowParams] = useState(false)
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api.getCalculations(id).catch(() => ({ results: [] })),
      api.getDesignParams(id).catch(() => ({ units: [] })),
    ])
      .then(([calcData, paramData]) => {
        const calcResults = (calcData as { results: CalculationResult[] }).results
        if (Array.isArray(calcResults) && calcResults.length > 0) {
          setResults(calcResults)
        }
        const dp = paramData as { units: UnitParams[] }
        if (dp.units && Array.isArray(dp.units) && dp.units.length > 0) {
          setDesignParams(dp.units)
          setSelectedUnit(dp.units[0].unit_code)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const handleCalculate = async () => {
    if (!id) return
    setCalculating(true)
    setError('')
    try {
      const hasOverrides = Object.values(overrides).some(
        unitParams => Object.keys(unitParams).length > 0
      )
      const data = await api.runCalculation(
        id,
        hasOverrides ? overrides : undefined,
      ) as { results: CalculationResult[] }
      setResults(data.results || [])
      setShowParams(false)
    } catch (e) {
      setError((e as Error).message || '计算失败')
    } finally {
      setCalculating(false)
    }
  }

  const handleApplyPreset = (newOverrides: ParameterOverrides, _presetName: string) => {
    setOverrides(newOverrides)
  }

  const countOverrides = Object.values(overrides).reduce(
    (sum, p) => sum + Object.keys(p).length, 0
  )

  if (loading) return <LoadingSpinner />

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">设计计算结果</h1>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      {/* Parameter Review Panel (collapsible) */}
      {designParams.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <button
            onClick={() => setShowParams(!showParams)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-gray-700">设计参数审查</h2>
              {countOverrides > 0 && !showParams && (
                <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                  {countOverrides} 项已修改
                </span>
              )}
            </div>
            <svg
              className={`w-5 h-5 text-gray-400 transition-transform ${showParams ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showParams && (
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
              <PresetSelector
                onApply={handleApplyPreset}
                overrides={overrides}
              />
              <ParameterEditor
                units={designParams}
                overrides={overrides}
                onChange={setOverrides}
                selectedUnit={selectedUnit}
                onSelectUnit={setSelectedUnit}
              />
            </div>
          )}
        </div>
      )}

      {results.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-2">
            {designParams.length > 0
              ? '审查上方设计参数（可选），然后点击下方按钮执行计算'
              : '点击下方按钮，系统将按工艺路线依次计算各处理单元的设计参数'}
          </p>
          {countOverrides > 0 && (
            <p className="text-xs text-amber-600 mb-4">
              已修改 {countOverrides} 项参数，将使用您的自定义值计算
            </p>
          )}
          <button
            onClick={handleCalculate}
            disabled={calculating}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-light transition-colors disabled:opacity-50 text-base mt-4"
          >
            {calculating ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                计算中...
              </span>
            ) : (
              '执行全部计算'
            )}
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {results.map((result, i) => (
              <div
                key={result.unit_code || i}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden"
              >
                <button
                  onClick={() => setSelectedUnit(
                    selectedUnit === result.unit_code ? null : (result.unit_code || null)
                  )}
                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                      {result.order || i + 1}
                    </span>
                    <div>
                      <h3 className="font-semibold text-gray-900">{result.unit_name_zh}</h3>
                      <p className="text-xs text-gray-400 font-mono">{result.unit_code}</p>
                    </div>
                    {result.warnings && result.warnings.length > 0 && (
                      <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                        {result.warnings.length} 条警告
                      </span>
                    )}
                  </div>
                  <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${selectedUnit === result.unit_code ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {selectedUnit === result.unit_code && (
                  <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-4">
                    {result.error ? (
                      <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{result.error}</div>
                    ) : (
                      <>
                        <div>
                          <h4 className="text-xs font-medium text-gray-500 mb-2">设计结果</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {Object.entries(result.output_parameters || {}).map(([key, val]) => (
                              <div key={key} className="bg-gray-50 rounded-lg px-3 py-2">
                                <div className="text-xs text-gray-400">{key}</div>
                                <div className="text-sm font-medium text-gray-900">
                                  {typeof val === 'number' ? val.toFixed(2) : String(val)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {result.formulas_applied && result.formulas_applied.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-gray-500 mb-1.5">计算公式</h4>
                            <ul className="space-y-0.5">
                              {result.formulas_applied.map((f, i) => (
                                <li key={i} className="text-sm text-gray-500 font-mono bg-gray-50 px-3 py-1 rounded">
                                  {f}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {result.warnings && result.warnings.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-amber-600 mb-1.5">警告</h4>
                            <ul className="space-y-0.5">
                              {result.warnings.map((w, i) => (
                                <li key={i} className="text-sm text-amber-700 flex items-start gap-1.5">
                                  <span className="text-amber-500 mt-0.5">!</span>
                                  {w}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {result.notes && result.notes.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-gray-500 mb-1.5">备注</h4>
                            <ul className="space-y-0.5">
                              {result.notes.map((n, i) => (
                                <li key={i} className="text-sm text-gray-500">{n}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={handleCalculate}
              disabled={calculating}
              className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              {calculating ? '计算中...' : '重新计算'}
            </button>
            <button
              onClick={() => navigate(`/projects/${id}/equipment`)}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
            >
              下一步：设备选型
            </button>
          </div>
        </>
      )}
    </div>
  )
}
