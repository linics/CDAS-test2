"""Agent Service：封装 Step 3 的 CPOTE 解析与提交评价逻辑。

当前实现使用确定性规则与已有的向量切片数据生成可测试的
占位结果，便于后续替换为真实的大模型推理。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence

from chromadb import PersistentClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Assignment, Document, ProjectGroup, Submission
from app.schemas.step0 import (
    CPOTEExtraction,
    EvaluationResult,
    EvidenceItem,
    Milestone,
    RadarPoint,
    ScoreBreakdown,
    SubmissionContent,
)
from app.services.inventory import InventoryService


class AgentService:
    """提供与 Agent 相关的核心业务逻辑。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.inventory_service = InventoryService(settings)
        self._chroma_client: PersistentClient | None = None

    @property
    def chroma_client(self) -> PersistentClient:
        if self._chroma_client is None:
            self._chroma_client = PersistentClient(path=str(self.settings.chroma_persist_dir))
        return self._chroma_client

    def _get_collection(self):
        return self.inventory_service.get_collection()

    def _fetch_chunks(self, document_id: int) -> list[dict]:
        """从 Chroma 获取指定文档的 chunk 数据。"""

        collection = self._get_collection()
        result = collection.get(where={"document_id": document_id})
        chunks: list[dict] = []
        for idx, chunk_id in enumerate(result.get("ids", [])):
            metadata = (result.get("metadatas") or [{}])[idx] or {}
            text_list: Sequence[str] = result.get("documents") or []
            text = text_list[idx] if idx < len(text_list) else ""
            chunks.append(
                {
                    "id": chunk_id,
                    "page": metadata.get("page"),
                    "order": metadata.get("order"),
                    "text": text,
                }
            )
        return chunks

    def _summarize_text(self, text: str, fallback: str, max_length: int = 120) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return fallback
        return cleaned[:max_length] + ("..." if len(cleaned) > max_length else "")

    def _default_rubric(self) -> dict:
        return {
            "dimensions": [
                "participation",
                "collaboration",
                "inquiry",
                "innovation",
                "result",
            ],
            "scale": "0-100",
            "criteria": {
                "participation": "0-20: 缺失提交；21-60: 部分完成；61-85: 按时完成；86-100: 主动贡献",
                "collaboration": "团队协作与沟通程度",
                "inquiry": "调研深度与论证质量",
                "innovation": "方案的创新性与可行性",
                "result": "成果完成度与落地性",
            },
        }

    def parse_cpote(self, db: Session, document_id: int, assignment_title: str) -> Assignment:
        """根据上传文档生成 CPOTE 与默认里程碑并持久化 Assignment。"""

        document = db.get(Document, document_id)
        if not document:
            raise ValueError("Document not found")

        chunks = self._fetch_chunks(document_id)
        first_text = chunks[0]["text"] if chunks else ""
        summary = self._summarize_text(first_text, fallback=f"基于《{document.filename}》的教学设计")

        cpote = CPOTEExtraction(
            context=f"围绕文档《{document.filename}》生成的教学场景。",
            problem=self._summarize_text(first_text, "需根据资料补充问题描述"),
            objective=f"完成 {assignment_title} 的学习目标。",
            task=self._summarize_text(first_text, "请依据文档内容规划学习任务"),
            evaluation="按参与度、协作、探究、创新、成果五维进行评价。",
            source_refs=[
                {
                    "document_id": document_id,
                    "page": chunk.get("page", 1),
                    "chunk_id": chunk.get("id", ""),
                    "text": self._summarize_text(chunk.get("text", ""), ""),
                }
                for chunk in chunks[:8]
            ],
        )

        base_date = datetime.now(timezone.utc)
        milestone_templates = [
            ("组队与分工", "明确分工并提交分工表"),
            ("调查与研究", "提交数据或草稿"),
            ("成果制作", "制作汇报材料"),
            ("汇报与评价", "完成最终汇报"),
        ]
        milestones: List[Milestone] = []
        for idx, (name, description) in enumerate(milestone_templates, start=1):
            due_at = base_date + timedelta(days=7 * idx)
            milestones.append(
                Milestone(
                    index=idx,
                    name=name,
                    description=description,
                    due_at=due_at.isoformat().replace("+00:00", "Z"),
                    submission_requirements="依据文档内容提交阶段成果" if idx == 2 else None,
                )
            )

        assignment = Assignment(
            title=assignment_title,
            scenario=summary,
            milestones_json=[m.model_dump() for m in milestones],
            cpote_json=cpote.model_dump(),
            rubric_json=self._default_rubric(),
            document_id=document.id,
        )
        document.cpote_json = cpote.model_dump()
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        db.refresh(document)
        return assignment

    def _score_text(self, text: str, offset: int) -> int:
        if not text.strip():
            return 10
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        value = int.from_bytes(digest[offset : offset + 2], "big")
        return 50 + value % 51  # 50-100 之间

    def evaluate_submission(
        self, db: Session, group_id: int, milestone_index: int, content: SubmissionContent
    ) -> tuple[Submission, EvaluationResult]:
        """根据提交内容生成确定性的评分与雷达图数据并写入 Submission。"""

        group = db.get(ProjectGroup, group_id)
        if not group:
            raise ValueError("Group not found")

        assignment = group.assignment
        if not assignment:
            raise ValueError("Assignment not found for group")

        scores = {
            "participation": self._score_text(content.text, 0),
            "collaboration": self._score_text(content.text, 2),
            "inquiry": self._score_text(content.text, 4),
            "innovation": self._score_text(content.text, 6),
            "result": self._score_text(content.text, 8),
        }
        overall = int(sum(scores.values()) / len(scores))

        evaluation = EvaluationResult(
            scores=ScoreBreakdown(overall=overall, **scores),
            radar_data=[
                RadarPoint(dimension=dim, score=value) for dim, value in scores.items()
            ],
            summary=self._summarize_text(
                content.text, "提交内容较少，请补充细节以获得更准确的评价。"
            ),
            improvements=[
                "补充可量化的数据或证据以支持论点。",
                "在报告中明确分工与协作过程，提升协作得分。",
            ],
            evidence=[
                EvidenceItem(
                    source="submission_text",
                    quote=self._summarize_text(content.text, "无提交内容", max_length=80),
                    reason="基于提交文本提取的关键表述。",
                )
            ],
        )

        submission = Submission(
            group_id=group_id,
            assignment_id=assignment.id,
            milestone_index=milestone_index,
            content_json=content.model_dump(),
            ai_evaluation_json=evaluation.model_dump(),
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission, evaluation
