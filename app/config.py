"""应用配置管理。

使用 Pydantic Settings 统一读取环境变量，便于在本地/生产之间切换。
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """核心配置项。

    - ``database_url``：默认使用本地 SQLite，便于快速启动。
    - ``chroma_persist_dir``：向量库持久化目录，后续步骤会用到。
    - ``deepseek_api_key``：DeepSeek API Key，用于结构化生成。
    - ``siliconflow_api_key``：SiliconFlow API Key，用于 Embedding。
    """

    database_url: str = Field(
        default="sqlite:///./storage/cdas.db", description="SQLAlchemy 数据库 URL"
    )
    documents_dir: Path = Field(
        default=Path("./storage/documents"), description="上传文件存储目录"
    )
    chroma_persist_dir: Path = Field(
        default=Path("./storage/chroma"), description="Chroma 持久化目录"
    )
    deepseek_api_key: Optional[str] = Field(
        default=None, description="DeepSeek API Key，用于对话/结构化生成"
    )
    deepseek_model: str = Field(
        default="deepseek-chat", description="DeepSeek 对话模型 ID"
    )
    siliconflow_api_key: Optional[str] = Field(
        default=None, description="SiliconFlow API Key，用于 Embedding"
    )
    siliconflow_embedding_model: str = Field(
        default="BAAI/bge-large-zh-v1.5", description="SiliconFlow Embedding 模型 ID"
    )
    siliconflow_rerank_model: str = Field(
        default="BAAI/bge-reranker-v2-m3", description="SiliconFlow Rerank 模型 ID"
    )

    model_config = {
        "env_prefix": "CDAS_",
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """缓存后的全局配置实例。"""

    return Settings()
