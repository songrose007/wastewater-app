import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

const WASTEWATER_TYPES: Record<string, string> = {
  domestic: '生活污水',
  textile: '印染废水',
  electroplating: '电镀废水',
  food: '食品加工废水',
  chemical: '化工废水',
  pharmaceutical: '制药废水',
  slaughter: '屠宰废水',
  paper: '造纸废水',
  other: '其他工业废水',
}

export default function ProjectNewPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [wastewaterType, setWastewaterType] = useState('domestic')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('请输入项目名称')
      return
    }
    setCreating(true)
    setError('')
    try {
      const data = await api.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        wastewater_type: wastewaterType,
      }) as { id: string }
      navigate(`/projects/${data.id}`)
    } catch (e) {
      setError((e as Error).message || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">新建项目</h1>
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1.5">
            项目名称 <span className="text-red-500">*</span>
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="例如：某市污水处理厂一期工程"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            autoFocus
          />
        </div>

        <div>
          <label htmlFor="desc" className="block text-sm font-medium text-gray-700 mb-1.5">
            项目描述
          </label>
          <textarea
            id="desc"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="简要描述项目背景、规模等信息（选填）"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none"
          />
        </div>

        <div>
          <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-1.5">
            污水类型
          </label>
          <select
            id="type"
            value={wastewaterType}
            onChange={e => setWastewaterType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
          >
            {Object.entries(WASTEWATER_TYPES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={creating}
            className="px-6 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
          >
            {creating ? '创建中...' : '创建项目'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
