export interface Project {
  id: string
  name: string
  description?: string
  wastewater_type: string
  flow_rate?: number
  target_standard_id?: string
  status: 'draft' | 'water_quality_entered' | 'input_done' | 'process_selected' | 'calculated' | 'drawings_uploaded' | 'equipment_selected' | 'cost_estimated' | 'reported'
  created_at: string
  updated_at: string
}

export interface WaterQualityParams {
  ph?: number
  cod?: number
  bod5?: number
  ss?: number
  nh3_n?: number
  tn?: number
  tp?: number
  color?: number
  oil?: number
  cr6?: number
  cn?: number
  temperature?: number
  conductivity?: number
  [key: string]: number | undefined
}

export interface ProcessRoute {
  id: string
  template_id: string
  name: string
  name_zh: string
  score: number
  reasons: string[]
  risks: string[]
  units: RouteUnit[]
}

export interface RouteUnit {
  unit_code: string
  unit_name_zh: string
  order: number
  mandatory: boolean
}

export interface CalculationResult {
  id: string
  unit_code: string
  unit_name_zh: string
  order: number
  input_summary: Record<string, number>
  output_parameters: Record<string, number>
  formulas_applied: string[]
  warnings: string[]
  notes: string[]
  error?: string
}

export interface SelectedRoute {
  route_id: string
  route_name: string
  units: RouteUnit[]
}

export interface EquipmentItem {
  category: string
  process_unit_code: string
  equipment_type: string
  model_id: string
  model_name_zh: string
  quantity: number
  unit_price_cny: number
  total_price_cny: number
  specs: Record<string, number | string>
  manufacturer?: string
  is_chinese: boolean
  selection_rationale?: string
}

export interface EquipmentCategoryGroup {
  category: string
  name_zh: string
  items: EquipmentItem[]
}

export interface EquipmentListResponse {
  project_id: string
  categories: EquipmentCategoryGroup[]
  total_equipment_cost: number
}

export interface CapexBreakdown {
  civil_cost: number
  equipment_cost: number
  installation_cost: number
  engineering_cost: number
  contingency_cost: number
  total_capex: number
}

export interface OpexBreakdown {
  energy_cost: number
  chemical_cost: number
  labor_cost: number
  maintenance_cost: number
  sludge_disposal_cost: number
  depreciation_cost: number
  total_annual_opex: number
}

export interface CostEstimationResponse {
  project_id: string
  capex: CapexBreakdown
  opex: OpexBreakdown
  cost_per_m3: number
  assumptions: Record<string, number | string>
}

// Design Parameters
export interface ParamDef {
  unit_code: string
  unit_name_zh: string
  param_name: string
  param_name_zh: string
  value: number
  unit: string
  range_min?: number | null
  range_max?: number | null
}

export interface UnitParams {
  unit_code: string
  unit_name_zh: string
  parameters: ParamDef[]
}

export interface DesignParamsResponse {
  project_id: string
  route_name: string
  units: UnitParams[]
}

// Parameter Presets
export interface PresetParamValue {
  unit_code: string
  param_name: string
  param_value: number
}

export interface PresetResponse {
  id: number
  name: string
  description?: string
  wastewater_type?: string
  is_default: boolean
  parameters: PresetParamValue[]
  created_at: string
  updated_at: string
}

export interface PresetCreate {
  name: string
  description?: string
  wastewater_type?: string
  is_default?: boolean
  parameters: PresetParamValue[]
}

// Parameter overrides for calculation
export type ParameterOverrides = Record<string, Record<string, number>>
