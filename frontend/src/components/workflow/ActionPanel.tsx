interface ActionPanelProps {
  runningStep: string | null
  onRunStep: (step: string) => void
  onGenerateReport: () => void
}

const ACTIONS = [
  { step: 'process', label: '运行工艺推荐', desc: '根据水质、水量和标准生成候选工艺路线' },
  { step: 'equipment', label: '执行设备选型', desc: '根据设计计算结果自动匹配设备规格' },
  { step: 'cost', label: '估算投资成本', desc: '生成 CAPEX、OPEX 和吨水成本' },
]

export default function ActionPanel({ runningStep, onRunStep, onGenerateReport }: ActionPanelProps) {
  return (
    <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
      <h2 className="text-lg font-bold text-gray-900">一键动作</h2>
      <p className="mt-1 text-sm text-gray-500">安全可自动执行的步骤可以直接在这里触发，复杂修改会跳转到对应页面。</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {ACTIONS.map(action => (
          <button
            key={action.step}
            onClick={() => onRunStep(action.step)}
            disabled={Boolean(runningStep)}
            className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-left transition hover:border-primary/40 hover:bg-primary/5 disabled:opacity-50"
          >
            <div className="font-semibold text-gray-900">{runningStep === action.step ? '执行中...' : action.label}</div>
            <div className="mt-1 text-xs leading-5 text-gray-500">{action.desc}</div>
          </button>
        ))}
        <button
          onClick={onGenerateReport}
          disabled={Boolean(runningStep)}
          className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-left transition hover:bg-primary/10 disabled:opacity-50"
        >
          <div className="font-semibold text-primary">生成全部报告</div>
          <div className="mt-1 text-xs leading-5 text-primary/70">同时生成 HTML、PDF 和 DOCX</div>
        </button>
      </div>
    </section>
  )
}
