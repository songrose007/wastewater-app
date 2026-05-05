import type { UnitParams, ParameterOverrides } from '../types'

interface ParameterEditorProps {
  units: UnitParams[]
  overrides: ParameterOverrides
  onChange: (overrides: ParameterOverrides) => void
  selectedUnit: string | null
  onSelectUnit: (unitCode: string | null) => void
}

export default function ParameterEditor({
  units,
  overrides,
  onChange,
  selectedUnit,
  onSelectUnit,
}: ParameterEditorProps) {
  const currentUnit = selectedUnit
    ? units.find(u => u.unit_code === selectedUnit) || units[0]
    : units[0]

  const unitOverrides = overrides[currentUnit?.unit_code || ''] || {}

  const handleParamChange = (paramName: string, rawValue: string) => {
    const numVal = parseFloat(rawValue)
    const newOverrides = { ...overrides }

    if (isNaN(numVal) || rawValue.trim() === '') {
      // Remove the override
      if (newOverrides[currentUnit.unit_code]) {
        delete newOverrides[currentUnit.unit_code][paramName]
        if (Object.keys(newOverrides[currentUnit.unit_code]).length === 0) {
          delete newOverrides[currentUnit.unit_code]
        }
      }
    } else {
      if (!newOverrides[currentUnit.unit_code]) {
        newOverrides[currentUnit.unit_code] = {}
      }
      newOverrides[currentUnit.unit_code][paramName] = numVal
    }

    onChange(newOverrides)
  }

  const countOverrides = Object.values(overrides).reduce(
    (sum, unitParams) => sum + Object.keys(unitParams).length,
    0
  )

  const clearAllOverrides = () => {
    onChange({})
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">设计参数审查</h3>
          {countOverrides > 0 && (
            <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
              {countOverrides} 项已修改
            </span>
          )}
        </div>
        {countOverrides > 0 && (
          <button
            onClick={clearAllOverrides}
            className="text-xs text-red-500 hover:text-red-700 transition-colors"
          >
            重置全部
          </button>
        )}
      </div>

      {/* Unit Tabs */}
      <div className="flex flex-wrap gap-1.5">
        {units.map(unit => {
          const hasOverride = overrides[unit.unit_code] && Object.keys(overrides[unit.unit_code]).length > 0
          return (
            <button
              key={unit.unit_code}
              onClick={() => onSelectUnit(unit.unit_code)}
              className={`px-3 py-1.5 text-xs rounded-full transition-colors ${
                (currentUnit?.unit_code === unit.unit_code)
                  ? 'bg-primary text-white'
                  : hasOverride
                    ? 'bg-amber-100 text-amber-700 border border-amber-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {unit.unit_name_zh || unit.unit_code}
              {hasOverride && <span className="ml-1">*</span>}
            </button>
          )
        })}
      </div>

      {/* Parameter Table */}
      {currentUnit && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 w-1/3">参数</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500">默认值</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500">单位</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500">推荐范围</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500">修改值</th>
              </tr>
            </thead>
            <tbody>
              {currentUnit.parameters.map(param => {
                const currentVal = unitOverrides[param.param_name]
                const isModified = currentVal !== undefined && currentVal !== param.value
                return (
                  <tr key={param.param_name} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-2 text-gray-700 text-xs">{param.param_name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{param.value}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{param.unit}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">
                      {param.range_min != null && param.range_max != null
                        ? `${param.range_min} ~ ${param.range_max}`
                        : '-'}
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="any"
                        value={isModified ? currentVal : ''}
                        placeholder={String(param.value)}
                        onChange={e => handleParamChange(param.param_name, e.target.value)}
                        className={`w-24 px-2 py-1 border rounded text-xs focus:outline-none focus:ring-1 ${
                          isModified
                            ? 'border-amber-400 bg-amber-50 text-amber-700 focus:ring-amber-300'
                            : 'border-gray-200 text-gray-600 focus:ring-primary/30'
                        }`}
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
