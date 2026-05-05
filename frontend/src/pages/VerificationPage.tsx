import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'

interface VerificationItem {
  unit_code: string
  unit_name_zh: string
  param_name: string
  drawing_value?: number | null
  calculated_value?: number | null
  required_min?: number | null
  required_max?: number | null
  status: string
  message: string
}

const STATUS_COLORS: Record<string, string> = {
  pass: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  fail: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  pass: '通过',
  warning: '警告',
  fail: '超标',
}

export default function VerificationPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [items, setItems] = useState<VerificationItem[]>([])
  const [summary, setSummary] = useState<Record<string, number>>({})
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  const handleVerify = async () => {
    if (!id) return
    setVerifying(true)
    setError('')
    try {
      const data = await api.request(`/projects/${id}/verify-design`, { method: 'POST' }) as { items: VerificationItem[]; summary: Record<string, number> }
      setItems(data.items || [])
      setSummary(data.summary || {})
    } catch (e) {
      setError((e as Error).message || '校核执行失败')
    } finally {
      setVerifying(false)
    }
  }

  const filtered = filter === 'all' ? items : items.filter(i => i.status === filter)

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">设计校核</h1>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      {items.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-6">执行设计校核，对比图纸参数与计算结果</p>
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-light transition-colors disabled:opacity-50 text-base"
          >
            {verifying ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                校核中...
              </span>
            ) : (
              '执行设计校核'
            )}
          </button>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {['pass', 'warning', 'fail'].map(s => (
              <div key={s} className={`rounded-xl p-4 text-center ${s === 'pass' ? 'bg-green-50' : s === 'warning' ? 'bg-amber-50' : 'bg-red-50'}`}>
                <div className={`text-2xl font-bold ${s === 'pass' ? 'text-green-600' : s === 'warning' ? 'text-amber-600' : 'text-red-600'}`}>
                  {summary[s] || 0}
                </div>
                <div className="text-sm text-gray-500">{STATUS_LABELS[s]}</div>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-2 mb-4">
            {[
              { key: 'all', label: '全部' },
              { key: 'fail', label: '超标' },
              { key: 'warning', label: '警告' },
              { key: 'pass', label: '通过' },
            ].map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                  filter === f.key
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Items */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">构筑物</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">参数</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">图纸值</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">计算值</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">状态</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">说明</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, i) => (
                  <tr key={i} className={`border-t border-gray-50 ${item.status !== 'pass' ? 'bg-amber-50/30' : ''}`}>
                    <td className="px-4 py-2">{item.unit_name_zh}</td>
                    <td className="px-4 py-2 font-mono text-xs">{item.param_name}</td>
                    <td className="px-4 py-2">{item.drawing_value ?? '-'}</td>
                    <td className="px-4 py-2">{item.calculated_value?.toFixed(2) ?? '-'}</td>
                    <td className="px-4 py-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[item.status]}`}>
                        {STATUS_LABELS[item.status]}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 max-w-xs">{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors mr-3"
          >
            {verifying ? '重新校核中...' : '重新校核'}
          </button>
          <button
            onClick={() => navigate(`/projects/${id}/equipment`)}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
          >
            下一步：设备选型
          </button>
        </>
      )}
    </div>
  )
}
