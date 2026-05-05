import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    wastewater_type = Column(String(50), nullable=False)
    flow_rate = Column(Float, nullable=True)
    flow_rate_peak_factor = Column(Float, default=1.3)
    design_temp_min = Column(Float, default=10.0)
    design_temp_max = Column(Float, default=25.0)
    target_standard_id = Column(String(50), nullable=True)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    water_quality_params = relationship("WaterQualityParameter", back_populates="project", cascade="all, delete-orphan")
    process_routes = relationship("ProjectProcessRoute", back_populates="project", cascade="all, delete-orphan")
    calculation_results = relationship("CalculationResult", back_populates="project", cascade="all, delete-orphan")
    equipment_selections = relationship("EquipmentSelection", back_populates="project", cascade="all, delete-orphan")
    cost_estimates = relationship("CostEstimate", back_populates="project", cascade="all, delete-orphan")
    drawings = relationship("Drawing", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("ProjectReport", back_populates="project", cascade="all, delete-orphan")


class WaterQualityParameter(Base):
    __tablename__ = "water_quality_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    parameter_code = Column(String(50), nullable=False)
    parameter_name_zh = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), default="mg/L")
    category = Column(String(50), nullable=True)

    project = relationship("Project", back_populates="water_quality_params")


class ProjectProcessRoute(Base):
    __tablename__ = "project_process_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    route_id = Column(String(100), nullable=False)
    route_name_zh = Column(String(200), nullable=True)
    rank = Column(Integer, nullable=False)
    total_score = Column(Float, nullable=False)
    is_selected = Column(Boolean, default=False)

    project = relationship("Project", back_populates="process_routes")
    units = relationship("RouteUnit", back_populates="route", cascade="all, delete-orphan")


class RouteUnit(Base):
    __tablename__ = "route_units"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("project_process_routes.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    unit_code = Column(String(50), nullable=False)
    unit_name_zh = Column(String(100), nullable=False)
    is_mandatory = Column(Boolean, default=True)

    route = relationship("ProjectProcessRoute", back_populates="units")


class CalculationResult(Base):
    __tablename__ = "calculation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    route_unit_id = Column(Integer, ForeignKey("route_units.id"), nullable=True)
    calculator_code = Column(String(50), nullable=False)
    input_snapshot = Column(JSON, nullable=True)
    output_parameters = Column(JSON, nullable=True)
    intermediate_values = Column(JSON, nullable=True)
    formulas_applied = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="calculation_results")


class ProjectReport(Base):
    __tablename__ = "project_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    pdf_path = Column(String(500), nullable=True)
    html_content = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    revision = Column(Integer, default=1)

    project = relationship("Project", back_populates="reports")


class EquipmentSelection(Base):
    __tablename__ = "equipment_selections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    category = Column(String(50), nullable=False)
    process_unit_code = Column(String(50), nullable=False)
    equipment_type = Column(String(80), nullable=False)
    model_id = Column(String(100), nullable=False)
    model_name_zh = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price_cny = Column(Float, nullable=False)
    total_price_cny = Column(Float, nullable=False)
    specs = Column(JSON, nullable=True)
    manufacturer = Column(String(200), nullable=True)
    is_chinese = Column(Boolean, default=True)
    selection_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="equipment_selections")


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    capex_breakdown = Column(JSON, nullable=True)
    opex_breakdown = Column(JSON, nullable=True)
    total_capex = Column(Float, nullable=False)
    total_annual_opex = Column(Float, nullable=False)
    cost_per_m3 = Column(Float, nullable=True)
    assumptions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="cost_estimates")


class ParameterPreset(Base):
    __tablename__ = "parameter_presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    wastewater_type = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parameters = relationship("PresetParameter", back_populates="preset", cascade="all, delete-orphan")


class PresetParameter(Base):
    __tablename__ = "preset_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    preset_id = Column(Integer, ForeignKey("parameter_presets.id"), nullable=False)
    unit_code = Column(String(50), nullable=False)
    param_name = Column(String(100), nullable=False)
    param_value = Column(Float, nullable=False)

    preset = relationship("ParameterPreset", back_populates="parameters")


class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    drawing_type = Column(String(50), nullable=False)  # "plan" | "elevation" | "other"
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(200), nullable=False)
    page_count = Column(Integer, default=1)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="drawings")
    elements = relationship("ExtractedElement", back_populates="drawing", cascade="all, delete-orphan")


class ExtractedElement(Base):
    __tablename__ = "extracted_elements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=False)
    text = Column(String(500), nullable=False)
    element_type = Column(String(50), default="text")  # "text" | "dimension" | "label" | "equipment_tag"
    page_num = Column(Integer, default=1)
    x0 = Column(Float, nullable=True)
    y0 = Column(Float, nullable=True)
    x1 = Column(Float, nullable=True)
    y1 = Column(Float, nullable=True)
    parsed_value = Column(Float, nullable=True)       # extracted numeric value
    parsed_unit = Column(String(20), nullable=True)    # m, mm, etc.
    parsed_dimensions = Column(JSON, nullable=True)    # for L×W×H patterns
    raw_attributes = Column(JSON, nullable=True)        # additional parsed data

    drawing = relationship("Drawing", back_populates="elements")


class ElementMapping(Base):
    __tablename__ = "element_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    element_id = Column(Integer, ForeignKey("extracted_elements.id"), nullable=False)
    unit_code = Column(String(50), nullable=True)       # mapped process unit code
    param_name = Column(String(100), nullable=True)     # mapped parameter name
    is_auto_mapped = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)           # 0-1 auto-mapping confidence
    created_at = Column(DateTime, default=datetime.utcnow)
