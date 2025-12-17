"""应用配置管理。

使用 Pydantic Settings 统一读取环境变量，便于在本地/生产之间切换。
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """核心配置项。

    - ``database_url``：默认使用本地 SQLite，便于快速启动。
    - ``chroma_persist_dir``：向量库持久化目录，后续步骤会用到。
    - ``gemini_api_key``：占位的 API 密钥，后续 Agent 步骤会引用。
    """

    database_url: str = Field(
        default="sqlite:///./storage/cdas.db", description="SQLAlchemy 数据库 URL"
    )
    chroma_persist_dir: Path = Field(
        default=Path("./storage/chroma"), description="Chroma 持久化目录"
    )
    gemini_api_key: Optional[str] = Field(
        default=None, description="Gemini API Key，占位，后续步骤使用"
    )

    model_config = {
        "env_prefix": "CDAS_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """缓存后的全局配置实例。"""

    return Settings()

