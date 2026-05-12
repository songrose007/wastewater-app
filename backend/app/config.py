from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "污水处理工艺自动化设计平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./wastewater.db"

    KNOWLEDGE_BASE_DIR: str = str(Path(__file__).parent / "knowledge" / "data")

    REPORT_TEMPLATE_DIR: str = str(Path(__file__).parent / "report" / "templates")
    REPORT_OUTPUT_DIR: str = str(Path(__file__).parent.parent / "reports")
    UPLOAD_DIR: str = str(Path(__file__).parent.parent / "uploads")
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
