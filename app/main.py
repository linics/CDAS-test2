"""FastAPI 入口，完成 Step 1 的后端骨架与数据库表初始化。"""

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.config import get_settings
from app.db import Base, engine
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

    app.include_router(documents_router, prefix="/api")

    return app


app = create_app()
