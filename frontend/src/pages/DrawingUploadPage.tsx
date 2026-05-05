import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'

interface DrawingInfo {
  id: number
  name: string
  drawing_type: string
  original_filename: string
  page_count: number
  processed: boolean
  element_count: number
  created_at: string
}

interface ExtractedElement {
  id: number
  text: string
  element_type: string
  page_num: number
  x0?: number
  y0?: number
  x1?: number
  y1?: number
  parsed_value?: number
  parsed_unit?: string
  parsed_dimensions?: Record<string, number>
}

const TYPE_LABELS: Record<string, string> = {
  plan: '平面布置图',
  elevation: '高程布置图',
  other: '其他图纸',
}

const ELEMENT_TYPE_LABELS: Record<string, string> = {
  dimension: '尺寸标注',
  equipment_tag: '设备编号',
  text: '文字',
}

export default function DrawingUploadPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [drawings, setDrawings] = useState<DrawingInfo[]>([])
  const [elements, setElements] = useState<ExtractedElement[]>([])
  const [selectedDrawing, setSelectedDrawing] = useState<number | null>(null)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    api.listProjects()
    fetchDrawings()
  }, [id])

  const fetchDrawings = async () => {
    if (!id) return
    try {
      const data = await api.request(`/projects/${id}/drawings`) as { drawings: DrawingInfo[] }
      setDrawings(data.drawings || [])
    } catch {
      setDrawings([])
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !id) return

    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', file.name)
      formData.append('drawing_type', 'plan')

      const res = await fetch(`/api/v1/projects/${id}/drawings/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }))
        throw new Error(err.detail || '上传失败')
      }
      await fetchDrawings()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const handleViewElements = async (drawingId: number) => {
    if (!id) return
    setLoading(true)
    try {
      const data = await api.request(
        `/projects/${id}/drawings/${drawingId}/elements`
      ) as { elements: ExtractedElement[] }
      setElements(data.elements || [])
      setSelectedDrawing(drawingId)
    } catch {
      setError('加载元素失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">图纸导入与解析</h1>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-lg">{error}</div>
      )}

      {/* Upload Area */}
      <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 text-center mb-6">
        <svg className="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-gray-500 mb-2">上传CAD导出的PDF图纸</p>
        <p className="text-xs text-gray-400 mb-4">支持平面布置图、高程布置图的矢量PDF</p>
        <label className="inline-block px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors cursor-pointer">
          {uploading ? '解析中...' : '选择PDF文件'}
          <input
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>

      {/* Drawing List */}
      {drawings.length > 0 && (
        <div className="space-y-3 mb-6">
          {drawings.map(d => (
            <div key={d.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{d.name}</h3>
                    <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                      {TYPE_LABELS[d.drawing_type] || d.drawing_type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400">{d.original_filename} · {d.page_count}页 · {d.element_count}个文字元素</p>
                </div>
                <button
                  onClick={() => handleViewElements(d.id)}
                  disabled={loading && selectedDrawing === d.id}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    selectedDrawing === d.id
                      ? 'bg-primary text-white'
                      : 'border border-primary text-primary hover:bg-primary/5'
                  }`}
                >
                  {selectedDrawing === d.id ? '正在查看' : '查看元素'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Elements List */}
      {elements.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">解析结果 ({elements.length}个元素)</h2>
            <span className="text-xs text-gray-400">按页面和Y坐标排序</span>
          </div>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">类型</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">文字</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">提取值</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">单位</th>
                  <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">坐标</th>
                </tr>
              </thead>
              <tbody>
                {elements.map(e => (
                  <tr key={e.id} className="border-t border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        e.element_type === 'dimension' ? 'bg-green-100 text-green-700' :
                        e.element_type === 'equipment_tag' ? 'bg-purple-100 text-purple-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {ELEMENT_TYPE_LABELS[e.element_type] || e.element_type}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{e.text}</td>
                    <td className="px-4 py-2">{e.parsed_value ?? '-'}</td>
                    <td className="px-4 py-2 text-gray-400">{e.parsed_unit ?? '-'}</td>
                    <td className="px-4 py-2 text-xs text-gray-400">
                      {e.x0 != null ? `(${e.x0}, ${e.y0})` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        {elements.length > 0 && (
          <button
            onClick={() => navigate(`/projects/${id}/mapping`)}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
          >
            下一步：构筑物映射
          </button>
        )}
      </div>
    </div>
  )
}
