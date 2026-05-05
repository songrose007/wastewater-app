# 污水处理工艺自动化工作流 — 实施计划

## 最新任务：图纸驱动的设计校核系统

### 用户完整工作流

```
外部条件输入（水质/水量/标准）
  → 工艺选型（规则引擎推荐）
  → 设计计算（经验参数覆盖）
  → 【新】上传平面图/高程图（PDF/DWG）
  → 【新】图纸识别与信息抽取
  → 【新】构筑物及设备参数校核（图纸 vs 计算）
  → 设备选型 + 造价估算
  → 【新】规范化设计方案文本输出
```

### 分阶段实现策略

#### Phase A: PDF图纸导入与文字提取（本次实现）

**技术选型**: PyMuPDF (fitz) — 从CAD导出的矢量PDF中提取文字层
**输入**: 平面布置图PDF、高程布置图PDF
**输出**: 文字标注列表（含坐标位置）

**新建文件**:
| 文件 | 说明 |
|------|------|
| `backend/app/api/drawings.py` | 图纸上传/解析/查询 API |
| `backend/app/engine/drawing_parser.py` | PDF文字提取 + 尺寸识别引擎 |
| `backend/app/db/models.py` | 新增 Drawing、ExtractedElement ORM 模型 |
| `frontend/src/pages/DrawingUploadPage.tsx` | 图纸上传 + 解析结果展示 |
| `frontend/src/components/DrawingViewer.tsx` | PDF图纸预览 + 标注高亮 |

**API 设计**:
```
POST /api/v1/projects/{id}/drawings/upload    → 上传PDF图纸
GET  /api/v1/projects/{id}/drawings           → 获取已上传图纸列表
GET  /api/v1/projects/{id}/drawings/{did}/elements → 获取解析出的文字元素
```

**PDF解析流程**:
```
上传PDF → PyMuPDF逐页解析
  → 提取文字块（text + bbox坐标）
  → 按坐标聚簇分组（同一构筑物区域的文字）
  → 识别尺寸标注（匹配 数字×数字×数字 或 数字mm/m 模式）
  → 返回结构化元素列表
```

#### Phase B: 半自动构筑物映射（本次实现）

**目标**: 将图纸中提取的文字/尺寸与工艺路线中的构筑物建立对应关系

**交互流程**:
```
图纸元素列表（左侧） ←→ 工艺路线构筑物（右侧）
  ├─ 系统自动关键词匹配（"曝气池"→aeration_tank）
  ├─ 工程师拖拽确认映射
  ├─ 提取尺寸填入对应构筑物参数
  └─ 保存映射关系
```

**新建文件**:
| 文件 | 说明 |
|------|------|
| `frontend/src/pages/DrawingMappingPage.tsx` | 构筑物映射界面 |
| `frontend/src/components/ElementMapper.tsx` | 拖拽/选择映射组件 |

**API**:
```
POST /api/v1/projects/{id}/drawings/{did}/map   → 保存映射关系
GET  /api/v1/projects/{id}/drawings/mapping      → 获取已保存的映射
```

#### Phase C: 参数校核对比（本次实现）

**目标**: 将图纸提取参数与计算引擎输出进行交叉比对

**校核逻辑**:
```
图纸参数 vs 计算参数 → 逐项对比
  ├─ 池容：图纸 (L×W×H) 实际容积 vs 计算需求容积
  ├─ 尺寸：各维度是否满足规范最小尺寸
  ├─ 标高：高程图中的标高是否合理
  ├─ 设备：图纸标注设备型号 vs 选型推荐型号
  └─ 输出：校核报告（通过项/警告项/超标项）
```

**新建文件**:
| 文件 | 说明 |
|------|------|
| `backend/app/engine/design_verifier.py` | 设计校核引擎（参数对比 + 规范检查） |
| `frontend/src/pages/VerificationPage.tsx` | 校核结果展示页 |

**API**:
```
POST /api/v1/projects/{id}/verify-design    → 执行设计校核
GET  /api/v1/projects/{id}/verify-design    → 获取校核结果
```

#### Phase D: 规范化方案文本（本次实现）

**目标**: 生成符合《市政公用工程设计文件编制深度规定》要求的设计方案

**报告结构**:
```
第1章 工程概况
第2章 设计依据与标准
第3章 进水水质与处理要求
第4章 工艺方案选择与论证
第5章 构筑物设计计算（逐单元）
第6章 平面布置与高程设计（含图纸信息）
第7章 设备选型与配置
第8章 投资估算与经济分析
第9章 运行管理建议
附件 设计计算书 + 设备清单 + 图纸目录
```

**修改文件**: `backend/app/report/generator.py` — 重构为规范的章节模板

#### Phase E: DWG/DXF原生支持（后续）

- 使用 `ezdxf` 解析DXF文件
- 提取图层、图块、标注
- 可选：接入视觉AI模型识别构筑物符号

### 前端步骤扩展

```
水质输入 → 工艺选择 → 设计计算 → 图纸校核 → 设备选型 → 造价估算 → 方案报告
                                    ↑ 新增三步
                              (上传/解析→映射→校核)
```

### 实现顺序

```
1. ORM模型扩展（Drawing, ExtractedElement, ElementMapping）
2. drawing_parser.py 引擎（PyMuPDF文字提取+尺寸识别）
3. drawings API（上传/解析/查询）
4. design_verifier.py 引擎（参数对比校核）
5. verify-design API（校核执行/结果查询）
6. generator.py 重构（规范化章节模板）
7. 前端 DrawingUploadPage + DrawingViewer
8. 前端 DrawingMappingPage + ElementMapper
9. 前端 VerificationPage
10. App.tsx路由 + Layout.tsx步骤更新
11. 构建验证 + 测试
```

## 当前状态

用户需求：设计规范参数取值宽泛，希望用自己经验中的工艺参数覆盖默认值，在项目中直接使用经验参数。

核心模式：**计算前审查参数 → 按需修改 → 一次性计算 → 可选存为模板**

### 实现方案

#### 1. 参数流向改造

当前流向：`calculation_defaults.yaml` → `get_calculator_defaults()` → `run_route()` → 计算结果
改造后流向：`defaults.yaml` → **前端参数审查面板** → 工程师编辑 → `parameter_overrides` → `run_route()` → 计算结果
                                                                                    ↘ 可选保存为模板

#### 2. 改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/calculation.py` | 修改 | POST calculate 增加 `parameter_overrides` 请求体参数 |
| `api/design_params.py` | 新建 | GET 获取路由中所有构筑物的设计参数默认值+推荐范围 |
| `api/presets.py` | 新建 | 参数预设的 CRUD API (DB存储) |
| `db/models.py` | 修改 | 新增 `ParameterPreset` 和 `PresetParameter` ORM模型 |
| `models/__init__.py` | 修改 | 新增预设相关 Pydantic Schema |
| `main.py` | 修改 | 注册 design_params + presets 路由 |
| `pages/CalculationPage.tsx` | 修改 | 增加参数审查面板、预设选择器、覆盖参数传递 |
| `components/ParameterEditor.tsx` | 新建 | 参数编辑组件：展示名称/默认值/单位/范围，行内编辑 |
| `components/PresetSelector.tsx` | 新建 | 预设模板选择器：加载/保存/删除预设 |
| `types.ts` | 修改 | 新增 ParameterDef, DesignParams, Preset 接口 |
| `services/api.ts` | 修改 | 新增 getDesignParams, savePreset, listPresets 等方法 |

#### 3. API 设计

```
GET  /api/v1/projects/{id}/design-params       → 返回各构筑物的设计参数默认值+范围
POST /api/v1/projects/{id}/calculate            → 增加 parameter_overrides 参数

GET  /api/v1/presets                            → 列出所有参数预设
POST /api/v1/presets                            → 创建新预设
GET  /api/v1/presets/{preset_id}                → 获取预设详情
PUT  /api/v1/presets/{preset_id}                → 更新预设
DELETE /api/v1/presets/{preset_id}              → 删除预设
```

#### 4. 前端交互流程

```
CalculationPage 加载
  → 检查是否有已保存参数预设
  → 显示"参数审查"区域（默认折叠）
    ├─ 预设选择器：下拉选择已有预设 或 "使用默认值"
    ├─ 构筑物标签切换（格栅/沉砂池/曝气池/...）
    └─ 参数编辑表：参数名 | 默认值 | 单位 | 推荐范围 | 修改值
  → 工程师修改参数（修改值覆盖默认值）
  → 点击"执行全部计算"（携带覆盖参数）
  → 计算完成后，可选"保存为参数预设"
```

#### 5. 数据库模型

```python
class ParameterPreset(Base):
    id = Column(Integer, PK)
    name = Column(String)              # "我的经验参数-生活污水"
    description = Column(Text)
    wastewater_type = Column(String)   # 适用污水类型
    is_default = Column(Boolean)       # 是否设为默认
    created_at / updated_at

class PresetParameter(Base):
    id = Column(Integer, PK)
    preset_id = Column(FK)
    unit_code = Column(String)         # "aeration_tank"
    param_name = Column(String)        # "f_m_ratio"
    param_value = Column(Float)        # 0.12
```

#### 6. 实现顺序

```
1. ORM模型 + Pydantic Schema（预设存储）
2. GET design-params API（参数查询）
3. CRUD presets API（预设管理）
4. 修改 POST calculate API（接受覆盖参数）
5. 注册路由到 main.py
6. 前端 ParameterEditor + PresetSelector 组件
7. 改造 CalculationPage（集成参数审查面板）
8. 前端 types + api.ts 更新
9. 构建验证
```

## 当前状态

Phase 1（MVP 核心工作流）已完成：
- ✅ 后端：FastAPI + SQLAlchemy + SQLite + YAML 知识库
- ✅ 工艺选择引擎（规则评分） + 计算引擎（25+ 构筑物计算器）
- ✅ API 端点全部接通（projects, water-quality, process-selection, calculation, report, standards）
- ✅ 前端：React SPA 6 个页面（HomePage, ProjectNewPage, InputPage, ProcessSelectionPage, CalculationPage, ReportPage）
- ✅ 报告生成（HTML 内联模板 + WeasyPrint PDF）
- ⏳ 设备选型模块、造价估算模块、增强报告 —— **本次实现**

## 本次实施范围

按用户完整工作流补齐：设备选型 → 投资估算 → 规范化设计方案文本

### 模块概览

| 模块 | 新建文件 | 修改文件 | 说明 |
|------|---------|---------|------|
| 设备选型YAML知识库 | 2 | 1 | equipment_catalog.yaml (10大类200+型号), cost_factors.yaml |
| 设备选型引擎 | 1 | 0 | EquipmentSelector: 根据计算结果自动匹配设备 |
| 造价估算引擎 | 1 | 0 | CostEstimator: CAPEX + OPEX 完整计算 |
| 设备+造价API | 2 | 1 | equipment.py, cost.py 路由 + main.py注册 |
| ORM模型 + Schema | 0 | 2 | EquipmentSelection, CostEstimate 表 + Pydantic |
| 增强报告 | 0 | 1 | generator.py 增加设备/造价/合规章节 |
| 前端设备选型页 | 1 | 5 | EquipmentPage + 路由/导航/步骤更新 |
| 测试 | 2 | 0 | 设备选型+造价估算单元测试和集成测试 |

## 详细设计

### 1. 设备选型知识库 (equipment_catalog.yaml)

10大类别，每个类别含多个设备类型，每个类型含多型号，每个型号有设计范围、规格参数、价格：
- 格栅（粗/细格栅，按流量匹配）
- 沉砂池设备（曝气沉砂/旋流沉砂）
- 泵类（潜污泵/污泥泵/计量泵，按流量+扬程匹配，功率公式：P=QHρg/(3600η)）
- 曝气设备（罗茨风机/离心风机/微孔曝气器/表曝机）
- 搅拌推流设备（潜水搅拌机，功率=容积×搅拌功率密度）
- 沉淀池刮泥机（周边传动/中心传动/吸泥机，按池径匹配）
- 污泥处理设备（带式压滤机/离心机/叠螺机/板框压滤机）
- 加药系统（PAC/PAM/NaOH/次氯酸钠/碳源）
- MBR膜组件（中空纤维/平板膜，按膜面积匹配）
- 紫外消毒设备 + 仪表自控

### 2. 造价估算系数 (cost_factors.yaml)

- **CAPEX**: 土建费（按池容×单价系数，分池型，深基坑加价）、设备费、安装费（管道30%+电气15%+自控10%）、设计费8%、不可预见费10%
- **OPEX**: 电费(0.8元/kWh)、药剂费(PAC 2.5/PAM 18/NaOH 4 元/kg)、人工费(8万/人年)、维护费2.5%、污泥处置费250元/吨、折旧(土建30年/设备15年)
- **汇总**: 吨水处理成本 = (折旧+年运营费) / (Q×365)

### 3. 设备选型引擎 (EquipmentSelector)

- 输入：工艺路线单元 + 计算结果 + 设计流量
- 算法：UnitCode→设备类别映射 → 提取设计参数 → 按设计范围筛选型号 → 按优先级排序(范围内>功率效率>国产>低价) → 计算数量(含冗余系数)
- 输出：设备清单 + 分类汇总

### 4. 造价估算引擎 (CostEstimator)

- CAPEX = 土建 + 设备 + 安装 + 设计 + 不可预见
- OPEX = 电费 + 药剂费 + 人工 + 维护 + 污泥处置 + 折旧
- 吨水成本 = (折旧 + 年运营费) / (Q × 365)

### 5. 项目状态机扩展

draft → input_done → process_selected → calculated → **equipment_selected → cost_estimated** → reported

### 6. 前端设备选型页 (EquipmentPage)

- 分类标签过滤(全部/格栅/泵类/曝气/...) + 设备汇总卡片 + 分类设备卡片列表
- 每张卡片：型号、制造商、数量、单价、总价 + 展开显示规格详情
- 操作按钮：下一步→造价估算（调用API后显示结果内联或跳转报告页）

### 7. 增强报告模板

在 generator.py 内联 HTML 模板增加：
- 第6节：设备选型汇总表（序号/类别/设备名称/型号/数量/单价/总价/制造商）
- 第7节：投资估算 — CAPEX分项表 + OPEX分项表 + 吨水成本汇总
- 第8节：排放达标核验表（各单元出水 vs 排放标准限值，达标/超标标记）

### 8. 测试计划

- **单元测试**: 设备匹配逻辑（范围内/范围外/边界）、泵功率公式、曝气器数量计算、土建费=池容×单价×深度系数、OPEX电费=功率×电价×小时
- **集成测试**: POST select-equipment → 200 + 验证返回结构；POST estimate-cost → 验证CAPEX/OPEX分项之和等于总计

## 实现顺序

```
Phase A (并行): equipment_catalog.yaml + cost_factors.yaml
Phase B (并行): ORM模型 + Pydantic Schema + KnowledgeLoader扩展
Phase C (并行): EquipmentSelector引擎 + CostEstimator引擎
Phase D (并行): equipment API + cost API + main.py注册
Phase E: 增强报告生成器
Phase F (并行): 前端EquipmentPage + types + api.ts + 路由/导航更新
Phase G (并行): 单元测试 + 集成测试
Phase H: 构建验证
```

## 验证方式

1. 后端启动无错误，所有路由出现在 /docs
2. 完整状态流转：创建→水质→工艺→计算→设备→造价→报告，每步成功
3. 报告 HTML 包含设备表、造价表、合规核验表
4. 前端设备选型页正常展示，分类筛选工作
5. 前端构建成功，TypeScript 零错误
6. 测试覆盖率 ≥ 80%
                                        │
                                    YAML 知识库
                                    (排放标准/工艺规则/计算参数)
```

**核心技术选型**:
- 前端：React + TypeScript + Tailwind CSS + Vite
- 后端：Python FastAPI
- 数据库：SQLite（MVP 零依赖，后期可迁移 PostgreSQL）
- 报告：WeasyPrint + Jinja2 HTML 模板
- 知识库：YAML 文件（工程师可直接编辑，Git 版本管理）

## 核心工作流

```
输入水质水量 + 排放标准
  → 工艺选择引擎（规则评分，推荐最优工艺路线）
  → 计算引擎（逐构筑物计算：池容/尺寸/HRT/负荷/曝气量/产泥量）
  → 设备选型（Phase 2）
  → PDF 方案报告
```

## 目录结构

```
wastewater-app/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # pydantic-settings 配置
│   │   ├── api/                       # REST 路由
│   │   │   ├── projects.py            # 项目 CRUD
│   │   │   ├── water_quality.py       # 水质参数
│   │   │   ├── process_selection.py   # 工艺推荐
│   │   │   ├── calculation.py         # 设计计算
│   │   │   ├── equipment.py           # 设备选型 (Phase 2)
│   │   │   ├── report.py              # 报告生成
│   │   │   └── standards.py           # 排放标准查询
│   │   ├── models/                    # Pydantic schemas
│   │   ├── db/                        # SQLAlchemy ORM + CRUD
│   │   ├── engine/                    # 核心计算引擎
│   │   │   ├── process_selector.py    # 规则评分引擎
│   │   │   ├── orchestration.py       # 计算编排器
│   │   │   └── calculators/           # 构筑物计算器（15+ 个）
│   │   │       ├── base.py            # 抽象基类
│   │   │       ├── registry.py        # 自动注册
│   │   │       ├── screen.py          # 格栅
│   │   │       ├── grit_chamber.py    # 沉砂池
│   │   │       ├── primary_clarifier.py
│   │   │       ├── activated_sludge.py # 曝气池（活性污泥法）
│   │   │       ├── a2o.py             # A2O
│   │   │       ├── sbr.py             # SBR
│   │   │       ├── oxidation_ditch.py # 氧化沟
│   │   │       ├── mbr.py             # MBR
│   │   │       ├── secondary_clarifier.py
│   │   │       ├── coagulation.py     # 混凝沉淀
│   │   │       ├── advanced_oxidation.py
│   │   │       ├── disinfection.py
│   │   │       ├── sludge_thickening.py
│   │   │       └── sludge_dewatering.py
│   │   ├── knowledge/                 # 知识库
│   │   │   ├── loader.py              # YAML 加载器
│   │   │   └── data/
│   │   │       ├── discharge_standards.yaml   # GB 标准
│   │   │       ├── process_rules.yaml         # 选择规则
│   │   │       ├── process_templates.yaml     # 工艺模板
│   │   │       └── calculation_defaults.yaml  # 设计参数默认值
│   │   ├── report/                    # 报告生成
│   │   │   ├── generator.py
│   │   │   ├── pdf.py                 # WeasyPrint 封装
│   │   │   └── templates/report_zh.html
│   │   └── i18n/zh_CN.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── ProjectNewPage.tsx     # 新建项目
│   │   │   ├── InputPage.tsx          # Step 1: 水质输入
│   │   │   ├── ProcessSelectionPage.tsx # Step 2: 工艺推荐
│   │   │   ├── CalculationPage.tsx    # Step 3: 计算结果
│   │   │   ├── EquipmentPage.tsx      # Step 4 (Phase 2)
│   │   │   └── ReportPage.tsx         # Step 5: 报告
│   │   ├── components/                # 按功能分组的组件
│   │   ├── services/api.ts            # API 封装
│   │   ├── hooks/                     # 自定义 hooks
│   │   └── i18n/zh.ts                 # 中文翻译
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

## 核心模块设计

### 1. 知识库（YAML 驱动，工程师可直接编辑）

- **discharge_standards.yaml**: 排放标准（GB18918-2002 1A/1B/2级、GB8978-1996 等），含各项指标限值
- **process_rules.yaml**: 选择规则，每条规则有 condition（AND/OR 逻辑）和 actions（推荐/禁止/加减分）
  - 规则示例：BOD5/COD < 0.3 → 推荐高级氧化预处理 + 水解酸化；COD >= 2000 → 推荐 UASB 厌氧
- **process_templates.yaml**: 预定义工艺链模板（常规活性污泥法、A2O、SBR、MBR、氧化沟、印染标准工艺、电镀分类处理等）
- **calculation_defaults.yaml**: 每个构筑物的设计参数默认值和推荐范围

### 2. 工艺选择引擎

基于加权评分 + 过滤规则：
1. 加载适用该污水类型的所有工艺模板
2. 遍历所有规则，根据进水水质匹配
3. 每条规则对相关工艺模板加减分
4. 强制规则（mandatory）直接排除不满足条件的模板
5. 按总分排序输出推荐工艺路线

### 3. 计算引擎

- 每个构筑物是独立 Calculator 类，继承 BaseCalculator
- 输入：流量、进水水质、目标出水、设计温度、设计参数
- 输出：构筑物尺寸、HRT、负荷率、产泥量、药剂量、功率、出水预测、公式引用、警告
- 编排器按工艺路线顺序执行，上游出水自动作为下游进水
- Calculator 通过注册表自动发现，新增一个 .py 文件即可扩展

### 4. 报告生成

Jinja2 HTML 模板 → WeasyPrint 生成 PDF，支持中文字体嵌入

## API 设计（核心端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/projects | 创建项目 |
| POST | /api/v1/projects/{id}/water-quality | 保存水质参数 |
| POST | /api/v1/projects/{id}/select-process | 触发工艺选择 |
| GET | /api/v1/projects/{id}/process-routes | 获取推荐工艺列表 |
| POST | /api/v1/projects/{id}/confirm-route | 确认工艺路线 |
| POST | /api/v1/projects/{id}/calculate | 执行全部计算 |
| GET | /api/v1/projects/{id}/calculations | 获取计算结果 |
| POST | /api/v1/projects/{id}/report | 生成报告 |
| GET | /api/v1/projects/{id}/report/download | 下载 PDF |
| GET | /api/v1/standards | 排放标准列表 |

## 关键设计决策

1. **YAML 知识库 vs 纯数据库** → YAML 作为规范源，工程师可用文本编辑器直接修改，Git 可版本管理，启动时加载到内存
2. **Python 类计算器 vs 纯配置驱动** → Python 类处理复杂条件逻辑，YAML 管理可调系数。新增构筑物需写代码，但公式逻辑本身就需要编程级表达
3. **WeasyPrint(HTML→PDF) vs LaTeX** → WeasyPrint 中文字体支持好，工程师可编辑 HTML/CSS 模板，学习成本低
4. **SQLite vs PostgreSQL** → SQLite 零依赖适合单机 MVP，后期通过 SQLAlchemy 改一行连接串即可迁移
5. **加权评分 vs ML** → 透明、可审计、可解释，符合工程专业责任要求

## 实施阶段

### Phase 1: MVP（核心工作流）

| 步骤 | 内容 |
|------|------|
| 1 | 项目脚手架：FastAPI + React + Tailwind + SQLite + Docker |
| 2 | 知识库数据：排放标准、工艺规则（8+条）、工艺模板（5+套）、计算参数默认值 |
| 3 | 工艺选择引擎：规则求值器 + 模板评分器 + 约束检查 |
| 4 | 核心计算器：格栅、沉砂池、初沉池、曝气池（活性污泥法）、二沉池、消毒 |
| 5 | 高级计算器：A2O、SBR、MBR、氧化沟 |
| 6 | 工业计算器：调节池、混凝沉淀、高级氧化、水解酸化、UASB |
| 7 | API 端点全部接通 |
| 8 | 前端页面：项目创建→水质输入→工艺选择→计算结果 |
| 9 | 报告生成：Jinja2 模板 + WeasyPrint PDF + 前端预览下载 |
| 10 | 打磨：E2E 测试、中文本地化、响应式、错误处理 |

### Phase 2: 增强
- 设备选型数据库和匹配引擎
- 知识库管理后台界面（CRUD 规则/模板/参数）
- 更多污水类型覆盖（化工、制药、屠宰等）

### Phase 3: 高级功能
- 平面布置图生成（SVG/DXF）
- 调试管理模块
- 多用户 + 认证
- 工程投资估算（CAPEX/OPEX）
- 政策法规合规检查器

## 验证方式

1. **后端单元测试**：每个 Calculator 用标准设计场景验证（已知输入 → 手工核算输出）
2. **工艺选择测试**：10+ 不同水质场景验证推荐结果合理性
3. **集成测试**：完整 API 流程 input → select → calculate → report
4. **E2E 测试**：浏览器中完成一个完整的污水处理方案设计
5. **专业验证**：用实际工程项目数据反算，对比手工设计结果
