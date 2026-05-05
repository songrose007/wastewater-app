import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { PresetResponse, PresetParamValue, ParameterOverrides } from '../types'

interface PresetSelectorProps {
  onApply: (overrides: ParameterOverrides, presetName: string) => void
  overrides: ParameterOverrides
  wastewaterType?: string
}

export default function PresetSelector({ onApply, overrides, wastewaterType }: PresetSelectorProps) {
  const [presets, setPresets] = useState<PresetResponse[]>([])
  const [showSave, setShowSave] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listPresets()
      .then((data: unknown) => {
        const d = data as { presets: PresetResponse[] }
        setPresets(d.presets || [])
      })
      .catch(() => setPresets([]))
      .finally(() => setLoading(false))
  }, [])

  const handleApplyPreset = (preset: PresetResponse) => {
    const ov: ParameterOverrides = {}
    for (const p of preset.parameters) {
      if (!ov[p.unit_code]) ov[p.unit_code] = {}
      ov[p.unit_code][p.param_name] = p.param_value
    }
    onApply(ov, preset.name)
  }

  const handleSave = async () => {
    if (!saveName.trim()) return
    setSaving(true)
    try {
      const params: PresetParamValue[] = []
      for (const [unitCode, unitParams] of Object.entries(overrides)) {
        for (const [paramName, paramValue] of Object.entries(unitParams)) {
          params.push({ unit_code: unitCode, param_name: paramName, param_value: paramValue })
        }
      }

      const data = await api.createPreset({
        name: saveName.trim(),
        wastewater_type: wastewaterType,
        parameters: params,
      }) as PresetResponse

      setPresets(prev => [...prev, data])
      setSaveName('')
      setShowSave(false)
    } catch {
      // silently handle
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此预设？')) return
    try {
      await api.deletePreset(id)
      setPresets(prev => prev.filter(p => p.id !== id))
    } catch {
      // silently handle
    }
  }

  const countOverrides = Object.values(overrides).reduce(
    (sum, p) => sum + Object.keys(p).length, 0
  )

  const unmodified = Object.values(overrides).every(
    unitParams => Object.keys(unitParams).length === 0
  )

  return (
    <div className="space-y-3">
      {/* Load Preset */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">加载参数预设</label>
        {loading ? (
          <span className="text-xs text-gray-400">加载中...</span>
        ) : presets.length === 0 ? (
          <span className="text-xs text-gray-400">暂无保存的预设</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            <button
              key="default"
              onClick={() => onApply({}, '默认值')}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                Object.keys(overrides).length === 0 || unmodified
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              默认值
            </button>
            {presets.map(p => (
              <div key={p.id} className="flex items-center gap-0.5">
                <button
                  onClick={() => handleApplyPreset(p)}
                  className="px-3 py-1 text-xs rounded-full bg-gray-100 text-gray-600 hover:bg-primary/10 hover:text-primary transition-colors"
                  title={p.description || ''}
                >
                  {p.name}
                  {p.is_default && <span className="ml-1 text-[10px] text-amber-500">默认</span>}
                </button>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="w-4 h-4 flex items-center justify-center text-gray-300 hover:text-red-500 text-[10px]"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Save Preset */}
      {countOverrides > 0 && (
        <div>
          {!showSave ? (
            <button
              onClick={() => setShowSave(true)}
              className="text-xs text-primary hover:text-primary-light transition-colors"
            >
              保存当前参数为预设...
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={saveName}
                onChange={e => setSaveName(e.target.value)}
                placeholder="预设名称，如：我的经验参数-生活污水"
                className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-primary/30"
                autoFocus
              />
              <button
                onClick={handleSave}
                disabled={saving || !saveName.trim()}
                className="px-3 py-1 bg-primary text-white text-xs rounded hover:bg-primary-light transition-colors disabled:opacity-50"
              >
                {saving ? '保存中...' : '保存'}
              </button>
              <button
                onClick={() => { setShowSave(false); setSaveName('') }}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                取消
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
