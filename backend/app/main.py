"""污水处理工艺自动化设计平台 — FastAPI 主入口。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import engine, Base
from app.knowledge.loader import KnowledgeLoader

kb_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kb_instance
    Base.metadata.create_all(bind=engine)
    kb_instance = KnowledgeLoader()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import projects, water_quality, process_selection, calculation, standards, report, equipment, cost, design_params, presets, drawings, verify

app.include_router(projects.router)
app.include_router(water_quality.router)
app.include_router(process_selection.router)
app.include_router(calculation.router)
app.include_router(equipment.router)
app.include_router(cost.router)
app.include_router(design_params.router)
app.include_router(presets.router)
app.include_router(drawings.router)
app.include_router(verify.router)
app.include_router(standards.router)
app.include_router(report.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/v1/knowledge/calculators")
def list_calculators():
    from app.engine.calculators.registry import CalculatorRegistry
    return {"calculators": CalculatorRegistry.list_all()}
