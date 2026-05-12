"""项目成果打包服务。"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db import models
from app.report.project_snapshot import build_project_report_snapshot

SAFE_NAME_PATTERN = re.compile(r"[^\w\-.一-鿿]+")
PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_artifact_id(project_id: str) -> str:
    """Return a filesystem-safe project artifact identifier."""
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("项目ID格式无效")
    return project_id


def package_project(project_id: str, db: Session) -> dict[str, Any] | None:
    """将项目成果按 allowlist 打包为 ZIP。"""
    snapshot = build_project_report_snapshot(project_id, db)
    if not snapshot:
        return None

    artifact_id = safe_artifact_id(project_id)
    project = snapshot["project"]
    output_dir = Path(settings.REPORT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = output_dir / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    package_path = _safe_child_path(package_dir, f"project_{artifact_id}.zip")

    manifest = {
        "project_id": project_id,
        "project_name": project.name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "files": [],
    }

    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        _write_json(archive, manifest, "manifest.json")
        _write_json(archive, _project_json(project), "project.json")
        _write_json(archive, snapshot["water_quality"], "water_quality.json")
        _write_json(archive, snapshot["process_route"], "selected_route.json")
        _write_json(archive, snapshot["calculation_results"], "calculation_results.json")
        _write_json(archive, snapshot["equipment_list"], "equipment.json")
        _write_json(archive, snapshot["cost_estimate"], "cost.json")
        _write_json(archive, _load_mappings(project_id, db), "drawing_mappings.json")
        _write_text(archive, _readme_text(project.name), "README.md")

        report = db.query(models.ProjectReport).filter(models.ProjectReport.project_id == project_id).first()
        if report and report.html_content:
            _write_text(archive, report.html_content, "report.html")
        if report and report.pdf_path:
            _add_safe_file(archive, Path(report.pdf_path), "report.pdf", output_dir)

        docx_path = _safe_child_path(output_dir, f"report_{artifact_id}.docx")
        _add_safe_file(archive, docx_path, "report.docx", output_dir)

        upload_root = Path(settings.UPLOAD_DIR) / "drawings"
        for drawing in db.query(models.Drawing).filter(models.Drawing.project_id == project_id).all():
            safe_filename = _safe_filename(drawing.original_filename)
            _add_safe_file(
                archive,
                Path(drawing.file_path),
                f"drawings/{drawing.id}_{safe_filename}",
                upload_root,
            )

    return {
        "project_id": project_id,
        "package_path": str(package_path),
        "filename": package_path.name,
        "size_bytes": package_path.stat().st_size,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def get_package_path(project_id: str) -> Path:
    artifact_id = safe_artifact_id(project_id)
    return _safe_child_path(Path(settings.REPORT_OUTPUT_DIR) / "packages", f"project_{artifact_id}.zip")


def _project_json(project: models.Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "wastewater_type": project.wastewater_type,
        "flow_rate": project.flow_rate,
        "target_standard_id": project.target_standard_id,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


def _load_mappings(project_id: str, db: Session) -> list[dict[str, Any]]:
    mappings = db.query(models.ElementMapping).filter(models.ElementMapping.project_id == project_id).all()
    result = []
    for mapping in mappings:
        element = db.query(models.ExtractedElement).filter(models.ExtractedElement.id == mapping.element_id).first()
        result.append({
            "element_id": mapping.element_id,
            "element_text": element.text if element else "",
            "unit_code": mapping.unit_code,
            "param_name": mapping.param_name,
            "confidence": mapping.confidence,
        })
    return result


def _write_json(archive: zipfile.ZipFile, data: Any, arcname: str) -> None:
    archive.writestr(arcname, json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _write_text(archive: zipfile.ZipFile, text: str, arcname: str) -> None:
    archive.writestr(arcname, text.encode("utf-8"))


def _add_safe_file(archive: zipfile.ZipFile, file_path: Path, arcname: str, allowed_root: Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        return

    resolved_file = file_path.resolve()
    resolved_root = allowed_root.resolve()
    if resolved_root not in resolved_file.parents and resolved_file != resolved_root:
        return

    safe_arcname = "/".join(_safe_filename(part) for part in Path(arcname).parts)
    archive.write(str(resolved_file), safe_arcname)


def _safe_child_path(parent: Path, filename: str) -> Path:
    safe_filename = _safe_filename(filename)
    resolved_parent = parent.resolve()
    resolved_path = (resolved_parent / safe_filename).resolve()
    if resolved_parent not in resolved_path.parents:
        raise ValueError("文件路径越界")
    return resolved_path


def _safe_filename(name: str) -> str:
    safe = SAFE_NAME_PATTERN.sub("_", name).strip("._")
    return safe or "file"


def _readme_text(project_name: str) -> str:
    return f"""# {project_name} 成果包

本成果包由污水处理工艺设计平台自动生成，包含项目基础信息、水质参数、工艺路线、设计计算、设备清单、造价估算和报告文件。

## 文件说明

- `project.json`：项目基础信息
- `water_quality.json`：设计进水水质
- `selected_route.json`：已选工艺路线
- `calculation_results.json`：构筑物计算结果
- `equipment.json`：设备选型清单
- `cost.json`：投资估算与运行成本
- `report.html` / `report.pdf` / `report.docx`：设计方案报告
- `drawings/`：上传图纸原件

## 复核提示

自动生成结果仅供方案编制参考，正式设计和投标前需由专业工程师复核确认。
"""
