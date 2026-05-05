"""API schema models (Pydantic)"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class WastewaterTypeEnum(str, Enum):
    domestic = "domestic"
    textile_dyeing = "textile_dyeing"
    electroplating = "electroplating"
    food_processing = "food_processing"
    chemical = "chemical"


class ProjectStatusEnum(str, Enum):
    draft = "draft"
    input_done = "input_done"
    process_selected = "process_selected"
    calculated = "calculated"
    equipment_selected = "equipment_selected"
    cost_estimated = "cost_estimated"
    reported = "reported"


# --- Water Quality ---
class ParameterValue(BaseModel):
    parameter_code: str
    value: float
    unit: str = "mg/L"


class WaterQualityInput(BaseModel):
    wastewater_type: WastewaterTypeEnum
    flow_rate: float = Field(gt=0, description="设计流量 m3/d")
    flow_rate_peak_factor: float = Field(default=1.3, ge=1.0, le=3.0)
    design_temp_min: float = Field(default=10.0)
    design_temp_max: float = Field(default=25.0)
    target_standard_id: str
    parameters: List[ParameterValue]


# --- Process ---
class ProcessUnitDef(BaseModel):
    sequence: int
    unit_code: str
    unit_name_zh: str
    is_mandatory: bool = True
    purpose_zh: Optional[str] = None


class ProcessRecommendation(BaseModel):
    route_id: str
    route_name_zh: str
    total_score: float
    breakdown: Dict[str, float] = {}
    units: List[ProcessUnitDef] = []
    suitability_reasons: List[str] = []
    risks: List[str] = []


class ProcessSelectionResponse(BaseModel):
    project_id: str
    wastewater_type: str
    recommendations: List[ProcessRecommendation]
    applied_rules: List[Dict[str, Any]] = []


class ConfirmRouteRequest(BaseModel):
    route_id: str


# --- Calculation ---
class CalculationOutput(BaseModel):
    unit_code: str
    unit_name_zh: str
    sequence_order: int
    input_parameters: Dict[str, float] = {}
    computed_parameters: Dict[str, Any] = {}
    formulas: Dict[str, str] = {}
    warnings: List[str] = []
    notes: List[str] = []


class CalculationResponse(BaseModel):
    project_id: str
    route_id: str
    results: List[CalculationOutput]
    summary: Dict[str, Any] = {}


class ParameterOverride(BaseModel):
    unit_code: str
    parameters: Dict[str, Any]


# --- Project ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    wastewater_type: WastewaterTypeEnum


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    wastewater_type: str
    flow_rate: Optional[float] = None
    target_standard_id: Optional[str] = None
    status: str
    created_at: Any
    updated_at: Any


# --- Report ---
class ReportStatus(BaseModel):
    project_id: str
    status: str  # generating, ready, error
    pdf_path: Optional[str] = None
    message: Optional[str] = None


# --- Equipment Selection ---
class EquipmentItem(BaseModel):
    category: str
    process_unit_code: str
    equipment_type: str
    model_id: str
    model_name_zh: str
    quantity: int = 1
    unit_price_cny: float
    total_price_cny: float
    specs: Dict[str, Any] = {}
    manufacturer: Optional[str] = None
    is_chinese: bool = True
    selection_rationale: Optional[str] = None


class EquipmentSelectionResponse(BaseModel):
    project_id: str
    equipment_list: List[EquipmentItem]
    summary: Dict[str, Any] = {}


class EquipmentCategoryGroup(BaseModel):
    category: str
    name_zh: str
    items: List[EquipmentItem]


class EquipmentListResponse(BaseModel):
    project_id: str
    categories: List[EquipmentCategoryGroup]
    total_equipment_cost: float


# --- Cost Estimation ---
class CapexBreakdown(BaseModel):
    civil_cost: float
    equipment_cost: float
    installation_cost: float
    engineering_cost: float
    contingency_cost: float
    total_capex: float


class OpexBreakdown(BaseModel):
    energy_cost: float
    chemical_cost: float
    labor_cost: float
    maintenance_cost: float
    sludge_disposal_cost: float
    depreciation_cost: float
    total_annual_opex: float


class CostEstimationResponse(BaseModel):
    project_id: str
    capex: CapexBreakdown
    opex: OpexBreakdown
    cost_per_m3: float
    assumptions: Dict[str, Any] = {}


# --- Design Parameters ---
class ParamDef(BaseModel):
    unit_code: str
    unit_name_zh: str
    param_name: str
    param_name_zh: str = ""
    value: float
    unit: str = ""
    range_min: Optional[float] = None
    range_max: Optional[float] = None


class DesignParamsResponse(BaseModel):
    project_id: str
    route_name: str
    units: List[Dict[str, Any]]  # [{unit_code, unit_name_zh, parameters: [ParamDef]}]


class CalculateRequest(BaseModel):
    parameter_overrides: Optional[Dict[str, Dict[str, float]]] = None


# --- Parameter Presets ---
class PresetParamValue(BaseModel):
    unit_code: str
    param_name: str
    param_value: float


class PresetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    wastewater_type: Optional[str] = None
    is_default: bool = False
    parameters: List[PresetParamValue] = []


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    parameters: Optional[List[PresetParamValue]] = None


class PresetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    wastewater_type: Optional[str] = None
    is_default: bool
    parameters: List[PresetParamValue]
    created_at: Any
    updated_at: Any


# --- Drawings ---
class ExtractedElementSchema(BaseModel):
    id: int
    text: str
    element_type: str = "text"
    page_num: int = 1
    x0: Optional[float] = None
    y0: Optional[float] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    parsed_value: Optional[float] = None
    parsed_unit: Optional[str] = None
    parsed_dimensions: Optional[Dict[str, float]] = None


class DrawingResponse(BaseModel):
    id: int
    name: str
    drawing_type: str
    original_filename: str
    page_count: int
    processed: bool
    element_count: int = 0
    created_at: Any


class DrawingElementListResponse(BaseModel):
    drawing_id: int
    elements: List[ExtractedElementSchema]


class ElementMappingRequest(BaseModel):
    element_id: int
    unit_code: str
    param_name: Optional[str] = None


class BatchMappingRequest(BaseModel):
    mappings: List[ElementMappingRequest]


# --- Design Verification ---
class VerificationItem(BaseModel):
    unit_code: str
    unit_name_zh: str
    param_name: str
    drawing_value: Optional[float] = None
    calculated_value: Optional[float] = None
    required_min: Optional[float] = None
    required_max: Optional[float] = None
    status: str  # "pass" | "warning" | "fail"
    message: str


class VerificationResponse(BaseModel):
    project_id: str
    items: List[VerificationItem]
    summary: Dict[str, int] = {}  # {pass: N, warning: N, fail: N}
