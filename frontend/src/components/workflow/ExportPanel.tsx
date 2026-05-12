import { useMemo, useState } from 'react'
import type { PackageManifest } from '../../types'

interface ExportPanelProps {
  projectId: string
  packageInfo: PackageManifest | null
  packaging: boolean
  onPackage: () => void
}

function quoteShellArg(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`
}

function buildCommands(repoUrl: string, packageName: string): string {
  const safeRepoUrl = repoUrl.trim() || '<你的GitHub仓库URL>'
  const safePackageName = packageName || '<成果包.zip>'
  return [
    `git clone ${quoteShellArg(safeRepoUrl)}`,
    'cd <仓库目录>',
    `unzip ${quoteShellArg(safePackageName)}`,
    'git add .',
    'git commit -m "feat: add wastewater design project package"',
    'git push',
  ].join('\n')
}

export default function ExportPanel({ projectId, packageInfo, packaging, onPackage }: ExportPanelProps) {
  const [repoUrl, setRepoUrl] = useState('')
  const commands = useMemo(
    () => buildCommands(repoUrl, packageInfo?.filename || `污水处理设计成果包_${projectId.slice(0, 8)}.zip`),
    [projectId, repoUrl, packageInfo],
  )

  return (
    <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900">成果导出与 GitHub 上传</h2>
          <p className="mt-1 text-sm text-gray-500">先生成成果包，再按命令上传到你的 GitHub 仓库。第一版不保存 token，更安全。</p>
        </div>
        <button
          onClick={onPackage}
          disabled={packaging}
          className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-light disabled:opacity-50"
        >
          {packaging ? '打包中...' : '生成成果包 ZIP'}
        </button>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <h3 className="font-semibold text-gray-900">下载文件</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            <a className="rounded-lg bg-white px-3 py-2 text-sm shadow-sm hover:shadow" href={`/api/v1/projects/${projectId}/report/download?format=pdf`}>下载 PDF</a>
            <a className="rounded-lg bg-white px-3 py-2 text-sm shadow-sm hover:shadow" href={`/api/v1/projects/${projectId}/report/download?format=docx`}>下载 DOCX</a>
            <a className="rounded-lg bg-white px-3 py-2 text-sm shadow-sm hover:shadow" href={`/api/v1/projects/${projectId}/report/download?format=html`}>下载 HTML</a>
            {packageInfo && (
              <a className="rounded-lg bg-primary px-3 py-2 text-sm text-white shadow-sm hover:shadow" href={`/api/v1/projects/${projectId}/package/download`}>下载成果包</a>
            )}
          </div>
          {packageInfo && (
            <p className="mt-3 text-xs text-gray-500">已生成：{packageInfo.filename}（{Math.round(packageInfo.size_bytes / 1024)} KB）</p>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-slate-950 p-4 text-slate-100">
          <label className="text-sm font-medium text-slate-200" htmlFor="repo-url">GitHub 仓库 URL</label>
          <input
            id="repo-url"
            value={repoUrl}
            onChange={event => setRepoUrl(event.target.value)}
            placeholder="https://github.com/your-name/your-repo.git"
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-primary"
          />
          <pre className="mt-3 overflow-auto rounded-lg bg-black/40 p-3 text-xs leading-5 text-slate-200">{commands}</pre>
        </div>
      </div>
    </section>
  )
}
