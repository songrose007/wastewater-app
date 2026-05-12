"""项目成果打包 API。"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.package_project import get_package_path, package_project, safe_artifact_id

router = APIRouter(prefix="/api/v1/projects", tags=["package"])

LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost"}


def _require_local_client(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in LOCAL_CLIENTS:
        raise HTTPException(status_code=403, detail="成果包接口仅允许本机访问")


@router.post("/{project_id}/package")
def create_package(project_id: str, request: Request, db: Session = Depends(get_db)):
    """生成项目成果 ZIP 包。"""
    _require_local_client(request)
    try:
        safe_artifact_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = package_project(project_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result


@router.get("/{project_id}/package/download")
def download_package(project_id: str, request: Request):
    """下载项目成果 ZIP 包。"""
    _require_local_client(request)
    try:
        package_path = get_package_path(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not package_path.exists():
        raise HTTPException(status_code=404, detail="成果包不存在，请先生成成果包")
    return FileResponse(
        str(Path(package_path)),
        filename=f"污水处理设计成果包_{safe_artifact_id(project_id)[:8]}.zip",
        media_type="application/zip",
    )
