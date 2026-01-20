"""FastAPI 入口 - CDAS 跨学科作业系统。"""

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.v2 import router as v2_router
from app.config import get_settings
from app.db import Base, engine
from app.migrations import run_migrations


def create_app() -> FastAPI:
    """应用工厂，便于后续测试与拓展路由。"""

    settings = get_settings()
    app = FastAPI(
        title="CDAS API",
        version="2.0.0",
        description="跨学科作业系统 API"
    )

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    import traceback

    @app.middleware("http")
    async def catch_exceptions_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            trace = traceback.format_exc()
            print("Unhandled exception caught by middleware:")
            print(trace)
            return Response("Internal Server Error", status_code=500)

    @app.on_event("startup")
    def init_models() -> None:
        """启动时确保表存在并初始化学科数据。"""
        # 导入所有模型确保表被创建
        from app.models import (
            Document, User, Subject, Assignment, 
            ProjectGroup, Submission, Evaluation,
            PRESET_SUBJECTS
        )
        Base.metadata.create_all(bind=engine)
        run_migrations(engine)
        try:
            with open("storage/ai_status.log", "a", encoding="utf-8") as handle:
                handle.write(
                    f"deepseek_api_key_set={bool(get_settings().deepseek_api_key)}\n"
                )
        except Exception:
            pass
        
        # 自动初始化学科数据
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            existing = db.query(Subject).first()
            if not existing:
                for data in PRESET_SUBJECTS:
                    subject = Subject(**data)
                    db.add(subject)
                db.commit()
                print("[CDAS] 学科数据已自动初始化")
        finally:
            db.close()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": settings.database_url}

    # 旧版 API (保持兼容)
    app.include_router(documents_router, prefix="/api")
    
    # 新版 API v2
    app.include_router(v2_router)

    return app


app = create_app()

