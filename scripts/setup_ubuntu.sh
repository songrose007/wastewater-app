#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "============================================"
echo "  污水处理工艺设计平台 — Ubuntu 24.04 安装"
echo "============================================"

echo "[1/5] 安装系统依赖..."
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  nodejs \
  npm \
  fonts-wqy-zenhei \
  fonts-wqy-microhei \
  git \
  curl

echo "[2/5] 创建 Python 虚拟环境..."
python3 -m venv "$BACKEND_DIR/.venv"
# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"
python -m pip install --upgrade pip setuptools wheel

echo "[3/5] 安装后端依赖..."
python -m pip install -r "$BACKEND_DIR/requirements.txt"
python -m pip install python-docx pillow pyyaml openpyxl pymupdf

echo "[4/5] 安装前端依赖..."
npm --prefix "$FRONTEND_DIR" install

echo "[5/5] 验证安装..."
(cd "$BACKEND_DIR" && python - <<'PY'
from app.knowledge.loader import KnowledgeLoader
from app.engine.calculators.registry import CalculatorRegistry
kb = KnowledgeLoader()
reg = CalculatorRegistry()
print(f"知识库加载成功，计算器数量: {len(reg.list_all())}")
PY
)
npm --prefix "$FRONTEND_DIR" run build

echo ""
echo "安装完成。"
echo "启动后端: cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 --reload"
echo "启动前端: cd frontend && npm run dev"
