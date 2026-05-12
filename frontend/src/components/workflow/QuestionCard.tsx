import { Link } from 'react-router-dom'
import type { WorkflowQuestion } from '../../types'

interface QuestionCardProps {
  question: WorkflowQuestion
}

const SEVERITY_STYLES = {
  blocking: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
}

const SEVERITY_LABELS = {
  blocking: '必须处理',
  warning: '建议复核',
  info: '提示',
}

export default function QuestionCard({ question }: QuestionCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${SEVERITY_STYLES[question.severity]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="inline-flex rounded-full bg-white/70 px-2 py-0.5 text-xs font-semibold">
            {SEVERITY_LABELS[question.severity]}
          </span>
          <p className="mt-2 text-sm leading-6">{question.message}</p>
        </div>
        <Link
          to={question.route}
          className="shrink-0 rounded-lg bg-white px-3 py-1.5 text-sm font-medium shadow-sm transition hover:shadow"
        >
          去处理
        </Link>
      </div>
    </div>
  )
}
