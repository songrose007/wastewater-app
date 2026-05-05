#!/bin/bash
# Ubuntu 24.04 一键安装脚本
# 用法: chmod +x setup_ubuntu.sh && ./setup_ubuntu.sh

set -e
echo "============================================"
echo "  污水处理工艺设计平台 — Ubuntu 24.04 安装"
echo "============================================"

# 1. 系统依赖
echo "[1/5] 安装系统依赖..."
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv \
    nodejs npm \
    fonts-wqy-zenhei fonts-wqy-microhei \   # 中文字体（流程图用）
    git curl

# 2. Python 依赖
echo "[2/5] 安装 Python 依赖..."
cd backend
pip install -r requirements.txt --break-system-packages
pip install python-docx pillow pyyaml openpyxl pymupdf --break-system-packages

# 3. 前端依赖（可选，只用出方案的话不需要）
echo "[3/5] 安装前端依赖（可跳过）..."
cd ../frontend
npm install

# 4. 验证
echo "[4/5] 验证安装..."
cd ../backend
python3 -c "
from app.knowledge.loader import KnowledgeLoader
from app.engine.equipment_selector import EquipmentSelector
from app.engine.equipment_verifier import EquipmentVerifier
kb = KnowledgeLoader()
print(f'  知识库加载成功: {len(kb.standards)} 标准, {len(kb.templates)} 模板')
from app.engine.calculators.registry import CalculatorRegistry
reg = CalculatorRegistry()
print(f'  计算器: {len(reg.list_all())} 个')
print('  安装验证通过!')
"

# 5. 完成
echo "[5/5] 完成!"
echo ""
echo "  使用方式:"
echo "    cd backend"
echo "    python3 generate_report.py project_input.yaml    # 一键出方案"
echo "    python3 demo_equipment.py                        # 设备选型演示"
echo ""
echo "  启动 Web 应用（可选）:"
echo "    cd backend && uvicorn app.main:app --port 8000"
echo "    cd frontend && npm run dev"
