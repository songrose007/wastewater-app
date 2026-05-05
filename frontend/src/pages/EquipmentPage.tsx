import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { EquipmentItem, EquipmentCategoryGroup, CostEstimationResponse } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'

const CATEGORY_LABELS: Record<string, string> = {
  screens: '格栅',
  grit_removal: '沉砂池设备',
  pumps: '泵类',
  blowers_aerators: '曝气设备',
  mixers: '搅拌/推流设备',
  clarifier_mechanisms: '沉淀池刮吸泥机',
  sludge_handling: '污泥处理设备',
  chemical_dosing: '加药系统',
  mbr_membranes: 'MBR膜组件',
  uv_disinfection: '紫外消毒设备',
  instruments: '仪表与自控',
}

export default function EquipmentPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [categories, setCategories] = useState<EquipmentCategoryGroup[]>([])
  const [totalCost, setTotalCost] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selecting, setSelecting] = useState(false)
  const [costResult, setCostResult] = useState<CostEstimationResponse | null>(null)
  const [estimating, setEstimating] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [expandedItem, setExpandedItem] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.getEquipment(id)
      .then((data: unknown) => {
        const d = data as EquipmentCategoryGroup[] | { categories: EquipmentCategoryGroup[]; total_equipment_cost: number }
        if (Array.isArray(d)) {
          setCategories(d)
        } else {
          setCategories(d.categories || [])
          setTotalCost(d.total_equipment_cost || 0)
        }
      })
      .catch(() => {
        // No equipment yet — that's OK, need to trigger selection
        setCategories([])
      })
      .finally(() => setLoading(false))

    // Try loading cost estimate
    api.getCost(id)
      .then((data: unknown) => setCostResult(data as CostEstimationResponse))
      .catch(() => setCostResult(null))
  }, [id])

  const handleSelect = async () => {
    if (!id) return
    setSelecting(true)
    setError('')
    try {
      const data = await api.selectEquipment(id) as { equipment_list: EquipmentItem[]; summary: { total_equipment_cost: number; by_category: Record<string, number> } }
      const items = data.equipment_list || []
      // Group items by category
      const groups: Record<string, EquipmentItem[]> = {}
      for (const item of items) {
        if (!groups[item.category]) groups[item.category] = []
        groups[item.category].push(item)
      }
      setCategories(
        Object.entries(groups).map(([cat, its]) => ({
          category: cat,
          name_zh: CATEGORY_LABELS[cat] || cat,
          items: its,
        }))
      )
      setTotalCost(data.summary?.total_equipment_cost || 0)
    } catch (e) {
      setError((e as Error).message || '设备选型失败')
    } finally {
      setSelecting(false)
    }
  }

  const handleEstimateCost = async () => {
    if (!id) return
    setEstimating(true)
    setError('')
    try {
      const data = await api.estimateCost(id) as CostEstimationResponse
      setCostResult(data)
    } catch (e) {
      setError((e as Error).message || '造价估算失败')
    } finally {
      setEstimating(false)
    }
  }

  const filteredCategories = filter === 'all'
    ? categories
    : categories.filter(c => c.category === filter)

  const allCategories = ['all', ...new Set(categories.map(c => c.category))]

  if (loading) return <LoadingSpinner />

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">设备选型</h1>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      {categories.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-6">点击下方按钮，系统将根据设计计算结果自动匹配设备型号</p>
          <button
            onClick={handleSelect}
            disabled={selecting}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-light transition-colors disabled:opacity-50 text-base"
          >
            {selecting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                分析匹配中...
              </span>
            ) : (
              '开始设备选型'
            )}
          </button>
        </div>
      ) : (
        <>
          {/* Summary Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4 flex items-center justify-between">
            <div>
              <span className="text-sm text-gray-500">设备总价</span>
              <div className="text-2xl font-bold text-primary">¥{totalCost.toLocaleString()}</div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSelect}
                disabled={selecting}
                className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
              >
                {selecting ? '重新选型中...' : '重新选型'}
              </button>
              {!costResult && (
                <button
                  onClick={handleEstimateCost}
                  disabled={estimating}
                  className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
                >
                  {estimating ? '估算中...' : '下一步：造价估算'}
                </button>
              )}
            </div>
          </div>

          {/* Cost Result */}
          {costResult && (
            <div className="bg-white rounded-xl border border-green-200 p-6 mb-4">
              <h2 className="text-lg font-bold text-gray-900 mb-4">投资与运行成本估算</h2>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-500">工程总投资</div>
                  <div className="text-2xl font-bold text-primary">{costResult.capex.total_capex.toLocaleString()}</div>
                  <div className="text-xs text-gray-400">万元</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-500">年运行成本</div>
                  <div className="text-2xl font-bold text-amber-600">{costResult.opex.total_annual_opex.toLocaleString()}</div>
                  <div className="text-xs text-gray-400">万元/年</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <div className="text-sm text-gray-500">吨水处理成本</div>
                  <div className="text-2xl font-bold text-green-600">{costResult.cost_per_m3}</div>
                  <div className="text-xs text-gray-400">元/m³</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-600 mb-2">CAPEX 分项</h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between"><span className="text-gray-500">土建费</span><span>{costResult.capex.civil_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">设备费</span><span>{costResult.capex.equipment_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">安装费</span><span>{costResult.capex.installation_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">设计费</span><span>{costResult.capex.engineering_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">不可预见费</span><span>{costResult.capex.contingency_cost.toLocaleString()} 万元</span></div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-600 mb-2">OPEX 分项（年）</h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between"><span className="text-gray-500">电费</span><span>{costResult.opex.energy_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">药剂费</span><span>{costResult.opex.chemical_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">人工费</span><span>{costResult.opex.labor_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">维护费</span><span>{costResult.opex.maintenance_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">污泥处置费</span><span>{costResult.opex.sludge_disposal_cost.toLocaleString()} 万元</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">折旧</span><span>{costResult.opex.depreciation_cost.toLocaleString()} 万元</span></div>
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-gray-100 flex gap-2">
                <button
                  onClick={handleEstimateCost}
                  disabled={estimating}
                  className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {estimating ? '重新估算...' : '重新估算'}
                </button>
                <button
                  onClick={() => navigate(`/projects/${id}/report`)}
                  className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
                >
                  下一步：生成方案报告
                </button>
              </div>
            </div>
          )}

          {/* Category Filter Tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {allCategories.map(cat => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                  filter === cat
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat === 'all' ? '全部' : CATEGORY_LABELS[cat] || cat}
              </button>
            ))}
          </div>

          {/* Equipment Cards */}
          <div className="space-y-3">
            {filteredCategories.map(group => (
              <div key={group.category}>
                <h2 className="text-sm font-medium text-gray-500 mb-2">{group.name_zh}</h2>
                {group.items.map(item => (
                  <div
                    key={`${item.category}-${item.model_id}`}
                    className="bg-white rounded-lg border border-gray-200 mb-2 overflow-hidden"
                  >
                    <button
                      onClick={() => setExpandedItem(
                        expandedItem === item.model_id ? null : item.model_id
                      )}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate">{item.model_name_zh}</div>
                        <div className="text-xs text-gray-400 mt-0.5">{item.manufacturer}</div>
                      </div>
                      <div className="flex items-center gap-4 ml-4">
                        <span className="text-sm px-2 py-0.5 bg-primary/10 text-primary rounded-full">
                          ×{item.quantity}
                        </span>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-gray-900">¥{item.unit_price_cny.toLocaleString()}</div>
                          <div className="text-xs text-gray-400">共 ¥{item.total_price_cny.toLocaleString()}</div>
                        </div>
                        <svg
                          className={`w-4 h-4 text-gray-300 transition-transform ${expandedItem === item.model_id ? 'rotate-180' : ''}`}
                          fill="none" viewBox="0 0 24 24" stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </button>
                    {expandedItem === item.model_id && (
                      <div className="px-4 pb-3 border-t border-gray-100 pt-3">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {Object.entries(item.specs || {}).map(([key, val]) => (
                            <div key={key} className="bg-gray-50 rounded px-3 py-1.5">
                              <div className="text-xs text-gray-400">{key}</div>
                              <div className="text-sm font-medium text-gray-700">{String(val)}</div>
                            </div>
                          ))}
                        </div>
                        {item.selection_rationale && (
                          <p className="mt-2 text-xs text-gray-400">{item.selection_rationale}</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
