import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import ErrorDisplay from '../components/ErrorDisplay'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const [generating, setGenerating] = useState(false)
  const [reportUrl, setReportUrl] = useState<string | null>(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!id) return
    setGenerating(true)
    setError('')
    try {
      await api.generateReport(id)
      setReportUrl(`/api/v1/projects/${id}/report/preview`)
    } catch (e) {
      setError((e as Error).message || '生成报告失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = () => {
    if (!id) return
    const link = document.createElement('a')
    link.href = `/api/v1/projects/${id}/report/download`
    link.download = ''
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">设计方案报告</h1>

      {error && (
        <div className="mb-4">
          <ErrorDisplay message={error} onRetry={handleGenerate} />
        </div>
      )}

      {!reportUrl ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-6">点击下方按钮生成完整的污水处理工艺设计方案报告</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-light transition-colors disabled:opacity-50 text-base"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                生成中...
              </span>
            ) : (
              '生成报告'
            )}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownload}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors inline-flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              下载 PDF
            </button>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              {generating ? '重新生成中...' : '重新生成'}
            </button>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden" style={{ height: '70vh' }}>
            <iframe
              src={reportUrl}
              className="w-full h-full"
              title="报告预览"
            />
          </div>
        </div>
      )}
    </div>
  )
}
