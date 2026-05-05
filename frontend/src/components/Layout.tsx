import { Link, Outlet, useLocation } from 'react-router-dom'

const STEPS = [
  { path: '/', label: '项目' },
]

function getProjectSteps(projectId: string) {
  return [
    { path: `/projects/${projectId}`, label: '水质输入' },
    { path: `/projects/${projectId}/process`, label: '工艺选择' },
    { path: `/projects/${projectId}/calculation`, label: '设计计算' },
    { path: `/projects/${projectId}/drawings`, label: '图纸导入' },
    { path: `/projects/${projectId}/mapping`, label: '构筑物映射' },
    { path: `/projects/${projectId}/verification`, label: '设计校核' },
    { path: `/projects/${projectId}/equipment`, label: '设备选型' },
    { path: `/projects/${projectId}/report`, label: '方案报告' },
  ]
}

function StepIndicator({ steps, currentPath }: { steps: { path: string; label: string }[]; currentPath: string }) {
  const currentIdx = steps.findIndex(s => currentPath.startsWith(s.path) && s.path !== '/')

  return (
    <nav className="flex items-center gap-1 text-sm" aria-label="设计流程">
      {steps.map((step, i) => {
        const isActive = i === currentIdx || (i === steps.length - 1 && currentIdx >= steps.length - 1)
        const isPast = i < currentIdx
        return (
          <div key={step.path} className="flex items-center gap-1">
            {i > 0 && (
              <span className={`w-6 h-px ${isPast ? 'bg-primary' : 'bg-gray-300'}`} />
            )}
            <Link
              to={step.path}
              className={`px-3 py-1.5 rounded-full transition-colors ${
                isActive
                  ? 'bg-primary text-white'
                  : isPast
                    ? 'text-primary hover:bg-primary/10'
                    : 'text-gray-400 pointer-events-none'
              }`}
            >
              {step.label}
            </Link>
          </div>
        )
      })}
    </nav>
  )
}

export default function Layout() {
  const location = useLocation()
  const match = location.pathname.match(/^\/projects\/([^/]+)/)
  const projectId = match ? match[1] : null
  const steps = projectId ? getProjectSteps(projectId) : STEPS

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="text-lg font-bold text-primary tracking-tight">
            污水处理工艺设计系统
          </Link>
          {projectId && (
            <StepIndicator steps={steps} currentPath={location.pathname} />
          )}
          <Link
            to="/projects/new"
            className="px-4 py-1.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-light transition-colors"
          >
            新建项目
          </Link>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
