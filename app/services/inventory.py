"""Inventory Service：负责文件上传、解析、切片与向量入库。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from chromadb import PersistentClient
from chromadb.errors import InvalidArgumentError
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, ParsingStatus, Subject
from app.services.ai import EmbeddingProvider, RerankProvider
from app.utils.storage import ensure_directory, remove_directory, save_upload_file
from app.utils.text_processing import chunk_pages, parse_document


class InventoryService:
    """封装文档上传与索引流程。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chroma_client: PersistentClient | None = None
        self.embedding_provider = EmbeddingProvider(settings)
        self.rerank_provider = RerankProvider(settings)
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

    def _detect_subject_from_filename(
        self,
        db: Session,
        filename: str,
    ) -> Tuple[Optional[int], Optional[str]]:
        stem = Path(filename).stem
        candidate = stem.split("_", 1)[-1] if "_" in stem else stem
        subjects = db.query(Subject).all()
        for subject in subjects:
            if subject.name and subject.name in stem:
                return subject.id, subject.name
            if subject.name and subject.name == candidate:
                return subject.id, subject.name
        return None, None

    async def handle_upload(self, db: Session, upload: UploadFile) -> Document:
        """完整处理上传、解析、索引流程。"""

        document = Document(
            filename=upload.filename or "uploaded",
            parsing_status=ParsingStatus.UPLOADED,
            mime_type=upload.content_type,
            source="user",
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
            subject_id, subject_name = self._detect_subject_from_filename(
                db, document.filename
            )
            raw_content = destination.read_bytes()
            pages = parse_document(raw_content, upload.filename or destination.name)
            chunks = chunk_pages(document.id, pages, chunk_size=800, overlap=200)
            embeddings = self.embedding_provider.embed_texts([c["text"] for c in chunks])

            collection = self.get_collection()
            if chunks:
                collection.upsert(
                    ids=[c["id"] for c in chunks],
                    embeddings=embeddings,
                    metadatas=[
                        {
                            "document_id": document.id,
                            "page": c["page"],
                            "chunk_id": c["id"],
                            "order": c["order"],
                            **({"subject_id": subject_id} if subject_id is not None else {}),
                            **({"subject_name": subject_name} if subject_name else {}),
                        }
                        for c in chunks
                    ],
                    documents=[c["text"] for c in chunks],
                )

            document.metadata_json = {
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "subject_id": subject_id,
                "subject_name": subject_name,
            }
            document.parsing_status = ParsingStatus.READY
        except Exception as exc: 
            document.parsing_status = ParsingStatus.FAILED
            document.error_msg = str(exc)
            # Log error for debugging
            print(f"Error processing document {document.id}: {exc}")
        finally:
            db.commit()
            db.refresh(document)
        
        return document

    def query_chunks(
        self,
        query: str,
        subject_ids: List[int] | None = None,
        limit: int = 12,
    ) -> list[dict]:
        if not query:
            return []
        embeddings = self.embedding_provider.embed_texts([query])
        if not embeddings:
            return []
        where = None
        if subject_ids:
            where = {"subject_id": {"$in": subject_ids}}
        collection = self.get_collection()
        try:
            result = collection.query(
                query_embeddings=[embeddings[0]],
                n_results=limit,
                where=where,
                include=["metadatas", "documents"],
            )
        except InvalidArgumentError as exc:
            print(f"Chroma query skipped due to embedding mismatch: {exc}")
            return []
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        chunks: list[dict] = []
        for idx, metadata in enumerate(metadatas):
            metadata = metadata or {}
            text = documents[idx] if idx < len(documents) else ""
            chunks.append(
                {
                    "id": metadata.get("chunk_id") or f"chunk_{idx}",
                    "page": metadata.get("page"),
                    "order": metadata.get("order"),
                    "text": text,
                    "subject_id": metadata.get("subject_id"),
                    "subject_name": metadata.get("subject_name"),
                }
            )
        if not chunks:
            return []
        reranked = self.rerank_provider.rerank(query, [c["text"] for c in chunks])
        if not reranked:
            return chunks
        return [chunks[i] for i in reranked if 0 <= i < len(chunks)]

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
