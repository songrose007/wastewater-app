import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Project, WaterQualityParams } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorDisplay from '../components/ErrorDisplay'

const CORE_FIELDS = [
  { key: 'ph', label: 'pH', unit: '', placeholder: '6-9' },
  { key: 'cod', label: 'COD', unit: 'mg/L', placeholder: '如 350' },
  { key: 'bod5', label: 'BOD₅', unit: 'mg/L', placeholder: '如 180' },
  { key: 'ss', label: 'SS', unit: 'mg/L', placeholder: '如 200' },
  { key: 'nh3_n', label: 'NH₃-N', unit: 'mg/L', placeholder: '如 30' },
  { key: 'tn', label: 'TN', unit: 'mg/L', placeholder: '如 40' },
  { key: 'tp', label: 'TP', unit: 'mg/L', placeholder: '如 4' },
  { key: 'temperature', label: '水温', unit: '°C', placeholder: '如 20' },
]

const INDUSTRIAL_FIELDS = [
  { key: 'color', label: '色度', unit: '倍', placeholder: '如 200' },
  { key: 'oil', label: '油脂', unit: 'mg/L', placeholder: '如 30' },
  { key: 'cr6', label: 'Cr⁶⁺', unit: 'mg/L', placeholder: '如 0.5' },
  { key: 'cn', label: '氰化物', unit: 'mg/L', placeholder: '如 0.2' },
]

interface StandardOption {
  id: string
  name_zh: string
  grades: string[]
}

export default function InputPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [flowRate, setFlowRate] = useState('')
  const [standardId, setStandardId] = useState('GB18918-2002')
  const [standardGrade, setStandardGrade] = useState('1A')
  const [params, setParams] = useState<Record<string, string>>({})
  const [standards, setStandards] = useState<StandardOption[]>([])
  const [showIndustrial, setShowIndustrial] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api.getProject(id),
      api.getWaterQuality(id).catch(() => ({})),
      api.request('/standards').catch(() => []),
    ])
      .then(([p, wq, stdList]) => {
        const projectData = p as Project
        setProject(projectData)
        if (projectData.flow_rate) setFlowRate(String(projectData.flow_rate))

        // Parse target standard
        const target = projectData.target_standard_id || projectData as unknown as string
        if (typeof target === 'string' && target.includes('-')) {
          const parts = target.split('-')
          setStandardId(parts.slice(0, -1).join('-'))
          setStandardGrade(parts[parts.length - 1])
        }

        const wqData = wq as WaterQualityParams
        if (wqData) {
          const filled: Record<string, string> = {}
          for (const key of [...CORE_FIELDS, ...INDUSTRIAL_FIELDS].map(f => f.key)) {
            const val = wqData[key]
            if (val !== undefined && val !== null) filled[key] = String(val)
          }
          setParams(filled)
          // Auto-expand industrial section if data exists
          if (INDUSTRIAL_FIELDS.some(f => wqData[f.key] !== undefined)) {
            setShowIndustrial(true)
          }
        }

        const stdResult = stdList as StandardOption[]
        if (Array.isArray(stdResult)) setStandards(stdResult)
      })
      .catch((e: Error) => setError(e.message || '加载项目失败'))
      .finally(() => setLoading(false))
  }, [id])

  const handleParamChange = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    if (!id) return
    setSaving(true)
    setError('')
    try {
      const numericParams: Record<string, number> = {}
      for (const [key, val] of Object.entries(params)) {
        const n = parseFloat(val)
        if (!isNaN(n)) numericParams[key] = n
      }
      const payload: Record<string, unknown> = {
        ...numericParams,
        target_standard_id: `${standardId}-${standardGrade}`,
      }
      if (flowRate && !isNaN(parseFloat(flowRate))) {
        payload.flow_rate = parseFloat(flowRate)
      }
      await api.saveWaterQuality(id, payload)
    } catch (e) {
      setError((e as Error).message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const currentStandard = standards.find(s => s.id === standardId)
  const grades = currentStandard?.grades || []

  if (loading) return <LoadingSpinner />
  if (!project) return <ErrorDisplay message="项目不存在" />

  return (
    <div className="max-w-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">水质参数输入</h1>
          <p className="text-sm text-gray-500 mt-1">{project.name}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        {/* 排放标准 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            排放标准
          </label>
          <div className="flex gap-3">
            <select
              value={standardId}
              onChange={e => { setStandardId(e.target.value); setStandardGrade('1A') }}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              {standards.map(s => (
                <option key={s.id} value={s.id}>{s.name_zh}</option>
              ))}
            </select>
            <select
              value={standardGrade}
              onChange={e => setStandardGrade(e.target.value)}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              {grades.map(g => (
                <option key={g} value={g}>{g}级</option>
              ))}
            </select>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {currentStandard?.name_zh} — {standardGrade}级标准
          </p>
        </div>

        {/* 设计流量 */}
        <div>
          <label htmlFor="flowRate" className="block text-sm font-medium text-gray-700 mb-1.5">
            设计水量 (m³/d)
          </label>
          <input
            id="flowRate"
            type="number"
            value={flowRate}
            onChange={e => setFlowRate(e.target.value)}
            placeholder="如 10000"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
          />
        </div>

        {/* 进水水质 */}
        <div className="border-t border-gray-100 pt-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">进水水质</h2>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {CORE_FIELDS.map(field => (
              <div key={field.key} className="flex items-center gap-2">
                <label htmlFor={`p-${field.key}`} className="text-xs text-gray-500 w-16 shrink-0">
                  {field.label}
                </label>
                <input
                  id={`p-${field.key}`}
                  type="number"
                  step="any"
                  value={params[field.key] || ''}
                  onChange={e => handleParamChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  className="flex-1 px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                {field.unit && (
                  <span className="text-xs text-gray-400 w-10">{field.unit}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 工业废水附加参数 */}
        <div className="border-t border-gray-100 pt-3">
          <button
            onClick={() => setShowIndustrial(!showIndustrial)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            <svg
              className={`w-3 h-3 transition-transform ${showIndustrial ? 'rotate-90' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            工业废水附加参数
          </button>
          {showIndustrial && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 mt-3">
              {INDUSTRIAL_FIELDS.map(field => (
                <div key={field.key} className="flex items-center gap-2">
                  <label htmlFor={`pi-${field.key}`} className="text-xs text-gray-500 w-16 shrink-0">
                    {field.label}
                  </label>
                  <input
                    id={`pi-${field.key}`}
                    type="number"
                    step="any"
                    value={params[field.key] || ''}
                    onChange={e => handleParamChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="flex-1 px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                  {field.unit && (
                    <span className="text-xs text-gray-400 w-10">{field.unit}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存参数'}
          </button>
          <button
            onClick={() => navigate(`/projects/${id}/process`)}
            className="px-6 py-2 border border-primary text-primary text-sm rounded-lg hover:bg-primary/5 transition-colors"
          >
            下一步：工艺选择
          </button>
        </div>
      </div>
    </div>
  )
}
