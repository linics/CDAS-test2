"""Inventory Service：负责文件上传、解析、切片与向量入库。"""

from __future__ import annotations

from pathlib import Path
from typing import List

from chromadb import PersistentClient
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, ParsingStatus
from app.services.ai import EmbeddingProvider
from app.utils.storage import ensure_directory, remove_directory, save_upload_file
from app.utils.text_processing import chunk_pages, parse_document


class InventoryService:
    """封装文档上传与索引流程。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chroma_client: PersistentClient | None = None
        self.embedding_provider = EmbeddingProvider(settings)
        ensure_directory(self.settings.documents_dir)
        ensure_directory(self.settings.chroma_persist_dir)

    @property
    def chroma_client(self) -> PersistentClient:
        if self._chroma_client is None:
            self._chroma_client = PersistentClient(path=str(self.settings.chroma_persist_dir))
        return self._chroma_client

    def get_collection(self):
        return self.chroma_client.get_or_create_collection(
            name="cdas-documents",
            metadata={"hnsw:space": "cosine"},
        )

    async def handle_upload(self, db: Session, upload: UploadFile) -> Document:
        """完整处理上传、解析、索引流程。"""

        document = Document(
            filename=upload.filename or "uploaded",
            parsing_status=ParsingStatus.UPLOADED,
            mime_type=upload.content_type,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        suffix = Path(upload.filename or "").suffix or ".bin"
        document_dir = self.settings.documents_dir / str(document.id)
        destination = document_dir / f"orig{suffix}"
        size_bytes = await save_upload_file(upload, destination)

        document.file_path = str(destination)
        document.size_bytes = size_bytes
        document.parsing_status = ParsingStatus.INDEXING
        db.commit()

        try:
            raw_content = destination.read_bytes()
            pages = parse_document(raw_content, upload.filename or destination.name)
            chunks = chunk_pages(document.id, pages, chunk_size=800, overlap=200)
            embeddings = self.embedding_provider.embed_texts([c["text"] for c in chunks])

            collection = self.get_collection()
            collection.upsert(
                ids=[c["id"] for c in chunks],
                embeddings=embeddings,
                metadatas=[
                    {
                        "document_id": document.id,
                        "page": c["page"],
                        "chunk_id": c["id"],
                        "order": c["order"],
                    }
                    for c in chunks
                ],
                documents=[c["text"] for c in chunks],
            )

            document.metadata_json = {
                "page_count": len(pages),
                "chunk_count": len(chunks),
            }
            document.parsing_status = ParsingStatus.READY
        except Exception as exc:  # noqa: BLE001 - 捕获任意异常并记录
            document.parsing_status = ParsingStatus.FAILED
            document.error_msg = str(exc)
        finally:
            db.commit()
            db.refresh(document)
        return document

    def list_documents(self, db: Session) -> list[Document]:
        return db.query(Document).order_by(Document.upload_date.desc()).all()

    def get_document(self, db: Session, document_id: int) -> Document | None:
        return db.get(Document, document_id)

    def delete_document(self, db: Session, document: Document) -> None:
        """删除 SQL 记录、文件目录与向量条目。"""

        collection = self.get_collection()
        collection.delete(where={"document_id": document.id})

        if document.file_path:
            doc_dir = Path(document.file_path).parent
            remove_directory(doc_dir)

        db.delete(document)
        db.commit()
