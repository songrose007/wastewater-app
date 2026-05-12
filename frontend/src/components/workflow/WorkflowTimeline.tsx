import { Link } from 'react-router-dom'
import type { WorkflowStep, WorkflowStepState } from '../../types'

interface WorkflowTimelineProps {
  steps: WorkflowStep[]
}

const STATE_LABELS: Record<WorkflowStepState, string> = {
  pending: '待开始',
  active: '当前',
  complete: '完成',
  needs_input: '需输入',
  needs_confirmation: '需确认',
  action_required: '需处理',
  warning: '需复核',
  ready: '可执行',
  optional: '可选',
}

const STATE_CLASSES: Record<WorkflowStepState, string> = {
  pending: 'border-gray-200 bg-gray-50 text-gray-500',
  active: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  complete: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  needs_input: 'border-red-200 bg-red-50 text-red-700',
  needs_confirmation: 'border-amber-200 bg-amber-50 text-amber-700',
  action_required: 'border-blue-200 bg-blue-50 text-blue-700',
  warning: 'border-orange-200 bg-orange-50 text-orange-700',
  ready: 'border-primary/20 bg-primary/5 text-primary',
  optional: 'border-slate-200 bg-slate-50 text-slate-600',
}

export default function WorkflowTimeline({ steps }: WorkflowTimelineProps) {
  return (
    <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">方案生成流程</h2>
          <p className="text-sm text-gray-500">按步骤完成输入、确认、校核、报告和成果包导出。</p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {steps.map((step, index) => (
          <Link
            key={step.key}
            to={step.route}
            className={`group rounded-xl border p-4 transition-all hover:-translate-y-0.5 hover:shadow-md ${STATE_CLASSES[step.state]}`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/80 text-sm font-bold shadow-sm">
                  {index + 1}
                </span>
                <div>
                  <div className="font-semibold">{step.label}</div>
                  <div className="text-xs opacity-75">{STATE_LABELS[step.state]}</div>
                </div>
              </div>
              <span className="text-lg opacity-40 transition-opacity group-hover:opacity-80">›</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
