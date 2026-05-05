"""FastAPI 依赖注入。"""
from app.db.database import SessionLocal
from app.knowledge.loader import KnowledgeLoader

_kb_instance = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_kb() -> KnowledgeLoader:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeLoader()
    return _kb_instance
