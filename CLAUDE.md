# 污水处理工艺设计平台

## 项目概述
面向环保工程师的污水处理工艺自动化设计平台。输入水质水量+排放标准 → 自动推荐工艺路线 → 设计计算 → 设备选型 → 造价估算 → 生成 DOCX 方案报告。

## 核心能力
- **工艺选择引擎**: 基于 YAML 规则评分，35个构筑物计算器
- **设备选型引擎**: 100%计算器覆盖，自动匹配型号/规格/价格，附带校核
- **造价估算**: CAPEX+OPEX 完整计算
- **方案生成**: 按尚科环境标准模板输出 DOCX
- **知识库**: 6个 YAML 文件（工程师可直接编辑）

## 常用命令
```bash
# 一键出方案
cd backend && python generate_report.py project_input.yaml

# 设备选型演示
cd backend && python demo_equipment.py

# Web 应用
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev

# 测试
cd backend && pytest tests/ -v
```

## 关键文件
- `backend/project_input.yaml` — 项目输入模板
- `backend/app/knowledge/data/*.yaml` — 知识库（标准/规则/参数/设备/造价）
- `backend/app/engine/equipment_selector.py` — 设备选型引擎
- `backend/app/engine/equipment_verifier.py` — 设备校核引擎
- `backend/reports/TEMPLATE_SPEC.md` — 方案模板规范
- `backend/draw_flow_pillow.py` — 流程图生成

## 输出格式
DOCX 方案严格按 TEMPLATE_SPEC.md 规范生成：封面→目录→项目概况→设计依据→工艺选择→构筑物设备→施工计划→投资成本。
