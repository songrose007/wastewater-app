import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Project } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorDisplay from '../components/ErrorDisplay'
import EmptyState from '../components/EmptyState'

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  water_quality_entered: '已输入水质',
  process_selected: '已选工艺',
  calculated: '已计算',
  reported: '已生成报告',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  water_quality_entered: 'bg-blue-100 text-blue-700',
  process_selected: 'bg-amber-100 text-amber-700',
  calculated: 'bg-green-100 text-green-700',
  reported: 'bg-emerald-100 text-emerald-700',
}

const TYPE_LABELS: Record<string, string> = {
  domestic: '生活污水',
  textile: '印染废水',
  electroplating: '电镀废水',
  food: '食品加工废水',
  chemical: '化工废水',
  pharmaceutical: '制药废水',
  slaughter: '屠宰废水',
  paper: '造纸废水',
  other: '其他',
}

function getNextPath(project: Project): string {
  switch (project.status) {
    case 'draft':
      return `/projects/${project.id}`
    case 'water_quality_entered':
      return `/projects/${project.id}/process`
    case 'process_selected':
      return `/projects/${project.id}/calculation`
    case 'calculated':
      return `/projects/${project.id}/report`
    default:
      return `/projects/${project.id}`
  }
}

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const fetchProjects = () => {
    setLoading(true)
    setError('')
    api.listProjects()
      .then((data: unknown) => setProjects(data as Project[]))
      .catch((e: Error) => setError(e.message || '加载项目列表失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除此项目？')) return
    try {
      await api.deleteProject(id)
      setProjects(prev => prev.filter(p => p.id !== id))
    } catch (e) {
      setError((e as Error).message || '删除失败')
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorDisplay message={error} onRetry={fetchProjects} />

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">我的项目</h1>
        <button
          onClick={() => navigate('/projects/new')}
          className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors"
        >
          新建项目
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          message="暂无项目，点击上方按钮创建第一个污水处理设计方案"
          actionLabel="新建项目"
          actionTo="/projects/new"
        />
      ) : (
        <div className="grid gap-4">
          {projects.map(project => (
            <div
              key={project.id}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-primary/30 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-lg font-semibold text-gray-900 truncate">
                      {project.name}
                    </h2>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[project.status]}`}>
                      {STATUS_LABELS[project.status]}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{TYPE_LABELS[project.wastewater_type] || project.wastewater_type}</span>
                    {project.flow_rate && <span>{project.flow_rate} m³/d</span>}
                    <span>{new Date(project.updated_at).toLocaleDateString('zh-CN')}</span>
                  </div>
                  {project.description && (
                    <p className="mt-2 text-sm text-gray-400 truncate">{project.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Link
                    to={getNextPath(project)}
                    className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors"
                  >
                    继续设计
                  </Link>
                  <button
                    onClick={() => handleDelete(project.id)}
                    className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    title="删除"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
