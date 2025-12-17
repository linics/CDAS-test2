"""核心 SQLAlchemy 模型定义。"""

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


class ParsingStatus(str, enum.Enum):
    """文档解析状态机。"""

    UPLOADED = "uploaded"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    """上传文档元数据与解析状态。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        Enum(ParsingStatus), default=ParsingStatus.UPLOADED, nullable=False
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(512))
    mime_type: Mapped[Optional[str]] = mapped_column(String(50))
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    cpote_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error_msg: Mapped[Optional[str]] = mapped_column(Text)

    assignments: Mapped[List["Assignment"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Assignment(Base):
    """由文档生成的作业配置。"""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario: Mapped[Optional[str]] = mapped_column(Text)
    milestones_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    cpote_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    rubric_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    document: Mapped[Optional[Document]] = relationship(back_populates="assignments")
    groups: Mapped[List["ProjectGroup"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class ProjectGroup(Base):
    """作业下的项目小组。"""

    __tablename__ = "project_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    members_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    assignment: Mapped[Assignment] = relationship(back_populates="groups")
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Submission(Base):
    """里程碑提交及 AI 评价。"""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    milestone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    content_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    ai_evaluation_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    group: Mapped[ProjectGroup] = relationship(back_populates="submissions")
    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
