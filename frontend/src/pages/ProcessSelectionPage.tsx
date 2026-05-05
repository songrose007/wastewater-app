import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { ProcessRoute, SelectedRoute } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ProcessSelectionPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [routes, setRoutes] = useState<ProcessRoute[]>([])
  const [selected, setSelected] = useState<SelectedRoute | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api.getSelectedRoute(id).catch(() => null),
      api.listProjects().catch(() => []),
    ])
      .then(([sel]) => {
        if (sel) setSelected(sel as SelectedRoute)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const handleSelect = async () => {
    if (!id) return
    setAnalyzing(true)
    setError('')
    try {
      const result = await api.selectProcess(id) as { routes: ProcessRoute[] }
      setRoutes(result.routes || [])
    } catch (e) {
      setError((e as Error).message || '工艺分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleConfirm = async (routeId: string) => {
    if (!id) return
    setConfirming(true)
    setError('')
    try {
      const result = await api.confirmRoute(id, routeId) as SelectedRoute
      setSelected(result)
    } catch (e) {
      setError((e as Error).message || '确认失败')
    } finally {
      setConfirming(false)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">工艺路线选择</h1>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      {!selected && routes.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-6">点击下方按钮，系统将根据进水水质自动推荐最佳工艺路线</p>
          <button
            onClick={handleSelect}
            disabled={analyzing}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-light transition-colors disabled:opacity-50 text-base"
          >
            {analyzing ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                分析中...
              </span>
            ) : (
              '开始工艺推荐'
            )}
          </button>
        </div>
      )}

      {selected && (
        <div className="bg-white rounded-xl border border-green-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-semibold text-green-700">已确认工艺路线</span>
          </div>
          <h2 className="text-lg font-bold text-gray-900 mb-3">{selected.route_name}</h2>
          <div className="flex flex-wrap gap-2">
            {selected.units.map((unit, i) => (
              <span key={unit.unit_code} className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary/5 text-primary text-sm rounded-full">
                <span className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold">
                  {i + 1}
                </span>
                {unit.unit_name_zh}
              </span>
            ))}
          </div>
          <div className="mt-6">
            <button
              onClick={() => navigate(`/projects/${id}/calculation`)}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
            >
              下一步：设计计算
            </button>
          </div>
        </div>
      )}

      {!selected && routes.length > 0 && (
        <div className="space-y-4">
          {routes.map((route, idx) => (
            <div
              key={route.id || route.template_id}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:border-primary/30 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    {idx === 0 && (
                      <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">推荐</span>
                    )}
                    <h3 className="text-lg font-semibold text-gray-900">{route.name_zh}</h3>
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">{route.name}</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-primary">{route.score}</div>
                  <div className="text-xs text-gray-400">评分</div>
                </div>
              </div>

              {route.reasons.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-xs font-medium text-gray-500 mb-1">推荐理由</h4>
                  <ul className="space-y-0.5">
                    {route.reasons.map((r, i) => (
                      <li key={i} className="text-sm text-gray-600 flex items-start gap-1.5">
                        <span className="text-green-500 mt-0.5">+</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {route.risks.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-xs font-medium text-gray-500 mb-1">注意事项</h4>
                  <ul className="space-y-0.5">
                    {route.risks.map((r, i) => (
                      <li key={i} className="text-sm text-amber-600 flex items-start gap-1.5">
                        <span className="text-amber-500 mt-0.5">!</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <h4 className="text-xs font-medium text-gray-500 mb-1.5">处理单元</h4>
                <div className="flex flex-wrap gap-1.5">
                  {route.units.map((unit, i) => (
                    <span
                      key={unit.unit_code}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full ${
                        unit.mandatory
                          ? 'bg-primary/10 text-primary'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      <span className="font-mono text-[10px]">{i + 1}</span>
                      {unit.unit_name_zh}
                      {unit.mandatory && <span className="text-[10px] opacity-60">必需</span>}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100">
                <button
                  onClick={() => handleConfirm(route.id || route.template_id)}
                  disabled={confirming}
                  className="px-4 py-1.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
                >
                  {confirming ? '确认中...' : '确认工艺路线'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
