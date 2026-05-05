# 污水处理工艺设计工作流 — 便携包

> 换电脑 / 换 CLI 平台后，按以下步骤恢复全部能力。
> 更新时间：2026-05-05

---

## 包内文件说明

```
wastewater-app/
│
├── 📄 PORTABLE_README.md          ← 你正在看的这份说明
├── 📄 TEMPLATE_SPEC.md            ← ★ 方案模板规范（最重要，任何 AI 都能用）
│
├── 📂 backend/                     ← 后端（纯 Python，无需 Node.js）
│   ├── requirements.txt            ← Python 依赖列表
│   ├── app/
│   │   ├── knowledge/data/         ← ★ 知识库 YAML（可文本编辑）
│   │   │   ├── discharge_standards.yaml   排放标准
│   │   │   ├── process_rules.yaml         工艺选择规则
│   │   │   ├── process_templates.yaml     工艺模板
│   │   │   ├── calculation_defaults.yaml  设计参数默认值
│   │   │   ├── equipment_catalog.yaml     设备选型目录
│   │   │   └── cost_factors.yaml         造价估算系数
│   │   ├── engine/                 ← 计算引擎（工艺选择/设计计算/设备/造价）
│   │   ├── api/                    ← FastAPI 路由（Web 应用用）
│   │   ├── report/                 ← 报告生成器
│   │   └── db/                     ← 数据库模型
│   ├── reports/                    ← ★ 输出目录
│   │   ├── TEMPLATE_SPEC.md        ← 模板规范（喂给 AI）
│   │   ├── generate_uranium_final.py  ← 最终版 DOCX 生成器
│   │   ├── draw_flow_pillow.py     ← 流程图绘制
│   │   └── flow_diagram.png        ← 流程图 PNG
│   └── tests/                      ← 单元测试
│
├── 📂 frontend/                    ← 前端（React + TypeScript + Vite）
│   └── ...
│
└── 📂 .claude/                     ← Claude Code 专属配置（仅 Claude Code CLI 需要）
    ├── rules/                      ← 编码规范
    ├── hookify.*.local.md          ← 自动化钩子
    └── plans/                      ← 项目架构知识
```

---

## 场景 A：只用 AI 出方案（不需要 Web 应用）

### 前提
- Python 3.10+ 已安装
- pip 可用

### 步骤

**1. 安装依赖**
```bash
pip install python-docx pillow pyyaml
```

**2. 把 `TEMPLATE_SPEC.md` 喂给 AI**

在任何 AI 工具中（Claude Code / Hermes Agent / ChatGPT / Cursor / Copilot 等），粘贴以下指令：

```
请阅读附件中的 TEMPLATE_SPEC.md，这是污水处理工程设计方案的标准模板规范。
然后根据我提供的项目信息，生成一份符合该规范的 DOCX 格式设计方案。

【项目信息】
- 项目名称：XXX
- 建设地点：XXX
- 废水类型：XXX
- 设计规模：XXX
- 排放标准：XXX
  （以下省略，根据实际填写）
```

AI 会按照模板规范生成完整的 Python 脚本，运行后输出 DOCX。

**3. 直接运行已有生成器（参考）**

```bash
cd backend
# 修改 generate_uranium_final.py 中的项目参数
# 然后运行：
python generate_uranium_final.py
# 输出：reports/baotou_uranium_flowchart.docx
```

---

## 场景 B：用完整 Web 应用（前后端都跑起来）

### 前提
- Python 3.10+
- Node.js 20+
- Git

### 步骤

**1. 安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

**2. 启动后端**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 访问 http://localhost:8000/docs 查看 API 文档
```

**3. 安装前端依赖并启动**
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

**4. 完整工作流**
```
浏览器打开 http://localhost:5173
→ 新建项目 → 水质输入 → 工艺选择 → 设计计算(参数审查)
→ 图纸导入 → 构筑物映射 → 设计校核 → 设备选型 → 方案报告
```

---

## 场景 C：换 Claude Code CLI 或 Hermes Agent

### Claude Code CLI

1. 拷贝 `.claude/` 目录到新电脑的 `C:\Users\<用户名>\.claude\`
2. 重启 Claude Code
3. Hook 和 Rules 自动生效

### Hermes Agent 或其他 CLI

1. 拷贝 `.claude/rules/` 中的内容到新平台的规则/规范目录
2. 将 `TEMPLATE_SPEC.md` 作为上下文文档加载
3. Hook 脚本需要根据新平台的钩子系统重新配置

---

## 知识库自定义

所有工艺参数、设备型号、造价系数都在 YAML 文件中，用任何文本编辑器即可修改：

| 想改什么 | 编辑哪个文件 |
|---------|------------|
| 排放标准限值 | `knowledge/data/discharge_standards.yaml` |
| 工艺选择规则 | `knowledge/data/process_rules.yaml` |
| 工艺模板 | `knowledge/data/process_templates.yaml` |
| 设计参数默认值 | `knowledge/data/calculation_defaults.yaml` |
| 设备型号和价格 | `knowledge/data/equipment_catalog.yaml` |
| 造价系数 | `knowledge/data/cost_factors.yaml` |

修改后重启后端即生效（`--reload` 模式会自动重载）。

---

## 快速测试

```bash
# 测试后端 API
curl http://localhost:8000/api/health
# 预期返回：{"status":"ok","version":"0.1.0"}

# 运行单元测试
cd backend
pytest tests/ -v
# 预期：28 passed

# 构建前端
cd frontend
npm run build
# 预期：✓ built in <3s

# 生成一份方案（独立运行）
cd backend
python generate_uranium_final.py
# 预期：DOCX saved: reports/baotou_uranium_flowchart.docx
```
