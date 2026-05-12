$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "============================================"
Write-Host "  污水处理工艺设计平台 — Windows 安装"
Write-Host "============================================"

Write-Host "[1/4] 创建 Python 虚拟环境..."
python -m venv (Join-Path $BackendDir ".venv")
$Python = Join-Path $BackendDir ".venv\Scripts\python.exe"

Write-Host "[2/4] 安装后端依赖..."
& $Python -m pip install --upgrade pip setuptools wheel
& $Python -m pip install -r (Join-Path $BackendDir "requirements.txt")
& $Python -m pip install python-docx pillow pyyaml openpyxl pymupdf

Write-Host "[3/4] 安装前端依赖..."
npm --prefix $FrontendDir install

Write-Host "[4/4] 构建前端验证..."
npm --prefix $FrontendDir run build

Write-Host ""
Write-Host "安装完成。"
Write-Host "启动后端: cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8000 --reload"
Write-Host "启动前端: cd frontend; npm run dev"
