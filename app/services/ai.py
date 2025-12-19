"""Gemini/LangChain集成的通用工具。"""

from __future__ import annotations

import hashlib
from typing import Iterable, List, Sequence, TypeVar

from pydantic import BaseModel

from app.config import Settings

try:  # 可选依赖，未安装时自动降级
    from langchain_google_genai import (
        ChatGoogleGenerativeAI,
        GoogleGenerativeAIEmbeddings,
    )
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:  # pragma: no cover - 运行环境可能暂无 LangChain
    ChatGoogleGenerativeAI = None  # type: ignore[assignment]
    GoogleGenerativeAIEmbeddings = None  # type: ignore[assignment]
    HumanMessage = None  # type: ignore[assignment]
    SystemMessage = None  # type: ignore[assignment]


T = TypeVar("T", bound=BaseModel)


class GeminiNotConfiguredError(RuntimeError):
    """当未提供 Gemini 相关依赖或 API Key 时抛出。"""


class EmbeddingProvider:
    """包装 Gemini Embedding，未配置时回退到哈希向量。"""

    def __init__(self, settings: Settings, dim: int = 768) -> None:
        self.settings = settings
        self.dim = dim
        self._client: GoogleGenerativeAIEmbeddings | None = None

    def _get_client(self) -> GoogleGenerativeAIEmbeddings | None:
        if not self.settings.gemini_api_key or GoogleGenerativeAIEmbeddings is None:
            return None
        if self._client is None:
            self._client = GoogleGenerativeAIEmbeddings(
                model=self.settings.gemini_embedding_model,
                google_api_key=self.settings.gemini_api_key,
            )
        return self._client

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        if not client:
            return self._fallback_embeddings(texts)
        try:
            return client.embed_documents(list(texts))
        except Exception:  # pragma: no cover - API 调用失败回退
            return self._fallback_embeddings(texts)

    def _fallback_embeddings(self, texts: Sequence[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
            vector: List[float] = []
            while len(vector) < self.dim:
                for byte in digest:
                    vector.append((byte - 128) / 128.0)
                    if len(vector) >= self.dim:
                        break
            embeddings.append(vector)
        return embeddings


class GeminiJSONClient:
    """使用 LangChain 封装的 Gemini 结构化输出。"""

    def __init__(
        self,
        settings: Settings,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> None:
        self.settings = settings
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._chat: ChatGoogleGenerativeAI | None = None

    @property
    def is_available(self) -> bool:
        return bool(
            self.settings.gemini_api_key
            and ChatGoogleGenerativeAI
            and HumanMessage
            and SystemMessage
        )

    def _get_chat(self) -> ChatGoogleGenerativeAI:
        if not self.is_available:
            raise GeminiNotConfiguredError("Gemini API 未配置或依赖缺失")
        if self._chat is None:
            self._chat = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,
                google_api_key=self.settings.gemini_api_key,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                convert_system_message_to_human=True,
            )
        return self._chat

    def structured_predict(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
    ) -> T:
        """根据 prompt 生成并校验结构化结果。"""

        chat = self._get_chat()
        chain = chat.with_structured_output(schema=schema)
        try:
            result: T = chain.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
        except Exception as exc:  # pragma: no cover - 依赖外部 API
            raise RuntimeError("Gemini 结构化生成失败") from exc
        return result
