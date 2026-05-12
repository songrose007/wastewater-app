import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { PackageManifest, WorkflowState } from '../types'
import ActionPanel from '../components/workflow/ActionPanel'
import ExportPanel from '../components/workflow/ExportPanel'
import QuestionCard from '../components/workflow/QuestionCard'
import WorkflowTimeline from '../components/workflow/WorkflowTimeline'
import ErrorDisplay from '../components/ErrorDisplay'
import LoadingSpinner from '../components/LoadingSpinner'

export default function SchemeWizardPage() {
  const { id } = useParams<{ id: string }>()
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null)
  const [packageInfo, setPackageInfo] = useState<PackageManifest | null>(null)
  const [loading, setLoading] = useState(true)
  const [runningStep, setRunningStep] = useState<string | null>(null)
  const [packaging, setPackaging] = useState(false)
  const [error, setError] = useState('')

  const loadWorkflow = useCallback(async () => {
    if (!id) return
    setError('')
    try {
      const data = await api.getWorkflow(id)
      setWorkflow(data as WorkflowState)
    } catch (event) {
      setError((event as Error).message || '加载工作流失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadWorkflow()
  }, [loadWorkflow])

  const runStep = async (step: string) => {
    if (!id) return
    setRunningStep(step)
    setError('')
    try {
      await api.runWorkflowStep(id, step)
      await loadWorkflow()
    } catch (event) {
      setError((event as Error).message || '执行失败')
    } finally {
      setRunningStep(null)
    }
  }

  const generateReport = async () => {
    if (!id) return
    setRunningStep('report')
    setError('')
    try {
      await api.generateReport(id, 'all')
      await loadWorkflow()
    } catch (event) {
      setError((event as Error).message || '生成报告失败')
    } finally {
      setRunningStep(null)
    }
  }

  const packageProject = async () => {
    if (!id) return
    setPackaging(true)
    setError('')
    try {
      const result = await api.packageProject(id)
      setPackageInfo(result as PackageManifest)
      await loadWorkflow()
    } catch (event) {
      setError((event as Error).message || '成果打包失败')
    } finally {
      setPackaging(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!id) return null

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-3xl border border-primary/10 bg-gradient-to-br from-primary/10 via-white to-emerald-50 p-8 shadow-sm">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <span className="inline-flex rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-primary shadow-sm">本地 WebUI 工作流</span>
          <h1 className="mt-4 text-3xl font-black tracking-tight text-gray-950">方案生成向导</h1>
          <p className="mt-3 text-base leading-7 text-gray-600">
            从基础信息和平面图开始，把需要输入、确认、修改和复核的事项集中在这里，最后生成 DOCX/PDF/HTML 报告和 GitHub 可上传成果包。
          </p>
          {workflow?.next_step && (
            <Link
              to={workflow.steps.find(step => step.key === workflow.next_step)?.route || `/projects/${id}`}
              className="mt-5 inline-flex rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-light"
            >
              继续处理：{workflow.steps.find(step => step.key === workflow.next_step)?.label}
            </Link>
          )}
        </div>
      </div>

      {error && <ErrorDisplay message={error} onRetry={loadWorkflow} />}

      {workflow && <WorkflowTimeline steps={workflow.steps} />}

      {workflow && workflow.questions.length > 0 && (
        <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900">待处理事项</h2>
          <p className="mt-1 text-sm text-gray-500">这些是生成最终方案前需要输入、确认、修改或复核的内容。</p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {workflow.questions.map(question => <QuestionCard key={question.id} question={question} />)}
          </div>
        </section>
      )}

      <ActionPanel runningStep={runningStep} onRunStep={runStep} onGenerateReport={generateReport} />
      <ExportPanel projectId={id} packageInfo={packageInfo} packaging={packaging} onPackage={packageProject} />
    </div>
  )
}
