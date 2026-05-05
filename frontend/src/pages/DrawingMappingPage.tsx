import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'

interface ExtractedElement {
  id: number
  text: string
  element_type: string
  parsed_value?: number
  parsed_unit?: string
  parsed_dimensions?: Record<string, number>
}

interface RouteUnit {
  unit_code: string
  unit_name_zh: string
  order: number
}

export default function DrawingMappingPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [elements, setElements] = useState<ExtractedElement[]>([])
  const [routeUnits, setRouteUnits] = useState<RouteUnit[]>([])
  const [mappings, setMappings] = useState<Record<number, { unit_code: string; param_name: string }>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetchElements(),
      fetchRouteUnits(),
    ]).finally(() => setLoading(false))
  }, [id])

  const fetchElements = async () => {
    if (!id) return
    try {
      const drawings = await api.request(`/projects/${id}/drawings`) as { drawings: { id: number }[] }
      const allElements: ExtractedElement[] = []
      for (const d of drawings.drawings || []) {
        const data = await api.request(
          `/projects/${id}/drawings/${d.id}/elements`
        ) as { elements: ExtractedElement[] }
        allElements.push(...(data.elements || []))
      }
      setElements(allElements)
    } catch {
      setElements([])
    }
  }

  const fetchRouteUnits = async () => {
    if (!id) return
    try {
      const data = await api.getSelectedRoute(id)
      const route = data as { units: RouteUnit[] }
      setRouteUnits(route.units || [])
    } catch {
      setRouteUnits([])
    }
  }

  const applyAutoSuggest = async () => {
    if (!id) return
    try {
      const data = await api.request(`/projects/${id}/drawings/suggest-mappings`) as { suggestions: { element_id: number; unit_code: string; param_name?: string }[] }
      const newMappings: Record<number, { unit_code: string; param_name: string }> = {}
      for (const s of data.suggestions || []) {
        // Find element by text
        const elem = elements.find(e => e.text === String(s.element_id) || e.id === s.element_id)
        if (elem) {
          newMappings[elem.id] = { unit_code: s.unit_code, param_name: s.param_name || '' }
        }
      }
      setMappings(prev => ({ ...prev, ...newMappings }))
    } catch {
      // silent
    }
  }

  const handleMap = (elementId: number, unitCode: string) => {
    if (!unitCode) {
      const newMappings = { ...mappings }
      delete newMappings[elementId]
      setMappings(newMappings)
      return
    }
    setMappings(prev => ({
      ...prev,
      [elementId]: { unit_code: unitCode, param_name: prev[elementId]?.param_name || '' },
    }))
  }

  const handleSave = async () => {
    if (!id) return
    setSaving(true)
    setError('')
    try {
      const mappingList = Object.entries(mappings).map(([elementId, m]) => ({
        element_id: parseInt(elementId),
        unit_code: m.unit_code,
        param_name: m.param_name || null,
      }))
      await api.request(`/projects/${id}/drawings/map`, {
        method: 'POST',
        body: JSON.stringify({ mappings: mappingList }),
      })
    } catch (e) {
      setError((e as Error).message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const mappedCount = Object.keys(mappings).length

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" /></div>

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">构筑物映射</h1>
      <p className="text-sm text-gray-500 mb-6">将图纸中提取的文字标注映射到工艺路线中的构筑物</p>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={applyAutoSuggest}
          className="px-4 py-2 border border-primary text-primary text-sm rounded-lg hover:bg-primary/5 transition-colors"
        >
          自动建议映射
        </button>
        <span className="text-sm text-gray-400">
          已映射 {mappedCount} / {elements.length} 个元素
        </span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-1/3">图纸元素</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">提取值</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-1/3">映射到构筑物</th>
            </tr>
          </thead>
          <tbody>
            {elements.filter(e => e.element_type === 'dimension').map(e => (
              <tr key={e.id} className={`border-t border-gray-50 ${mappings[e.id] ? 'bg-green-50/50' : 'hover:bg-gray-50'}`}>
                <td className="px-4 py-2">
                  <div className="text-xs font-mono">{e.text}</div>
                  {e.parsed_dimensions && (
                    <div className="text-xs text-gray-400 mt-0.5">
                      {Object.entries(e.parsed_dimensions).map(([k, v]) => `${k}=${v}`).join(', ')}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2 text-xs">
                  {e.parsed_value != null ? `${e.parsed_value} ${e.parsed_unit || ''}` : '-'}
                </td>
                <td className="px-4 py-2">
                  <select
                    value={mappings[e.id]?.unit_code || ''}
                    onChange={ev => handleMap(e.id, ev.target.value)}
                    className="w-full px-2 py-1 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-primary/30"
                  >
                    <option value="">-- 未映射 --</option>
                    {routeUnits.map(u => (
                      <option key={u.unit_code} value={u.unit_code}>
                        {u.unit_name_zh} ({u.unit_code})
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving || mappedCount === 0}
          className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存映射'}
        </button>
        <button
          onClick={() => navigate(`/projects/${id}/verification`)}
          className="px-6 py-2 border border-primary text-primary rounded-lg hover:bg-primary/5 transition-colors"
        >
          下一步：设计校核
        </button>
      </div>
    </div>
  )
}
