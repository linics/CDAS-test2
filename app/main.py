"""FastAPI 入口，完成 Step 1 的后端骨架与数据库表初始化。"""

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Assignment, Document, ProjectGroup, Submission


def create_app() -> FastAPI:
    """应用工厂，便于后续测试与拓展路由。"""

    settings = get_settings()
    app = FastAPI(title="CDAS API", version="0.1.0")

    @app.on_event("startup")
    def init_models() -> None:
        """启动时确保表存在。后续可替换为 Alembic 迁移。"""

        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": settings.database_url}

    return app


def get_db() -> Session:
    """FastAPI 依赖，用于获取数据库会话。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = create_app()
