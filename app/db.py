"""数据库连接与会话管理。"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    """SQLAlchemy 基类。"""

    pass


# SQLite 需要 ``check_same_thread=False`` 以支持多线程；其他数据库可忽略
engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """提供事务范围的 Session 上下文管理器。"""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

