"""Agent Service：封装 CPOTE 解析与提交评价的核心逻辑。"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Sequence

from pydantic import BaseModel
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
from app.services.ai import DeepSeekJSONClient
from app.services.inventory import InventoryService


class CPOTEAgentPayload(BaseModel):
    """LangChain 结构化输出的中间模型。"""

    cpote: CPOTEExtraction
    milestones: List[Milestone]


CPOTE_SYSTEM_PROMPT = (
    "你是一名教学设计解析 Agent。"
    "需要根据提供的教材片段提取 Context/Problem/Objective/Task/Evaluation 五要素，"
    "并结合 PBL 模式生成至少四个阶段的 Milestone（组队与分工、调查与研究、成果制作、汇报与评价）。"
    "输出 JSON，字段：cpote（含 source_refs，引用 chunk_id）与 milestones。"
    "Milestone index 必须从 1 开始递增，due_at 使用 ISO8601 UTC。"
)

EVALUATION_SYSTEM_PROMPT = (
    "你是一名严格的项目式学习评估专家。"
    "请根据 Rubric 与提交内容，从参与、协作、探究、创新、成果五个维度（0-100）给出评分，"
    "并提供 overall、雷达图数据、总结、至少两条改进建议以及证据列表。"
    "输出格式需符合 EvaluationResult Pydantic 模型。"
)


class AgentService:
    """提供与 Agent 层相关的核心业务逻辑。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.inventory_service = InventoryService(settings)
        self.deepseek_client = DeepSeekJSONClient(settings)

    def _fetch_chunks(self, document_id: int) -> list[dict]:
        """从 Chroma 获取指定文档的 chunk 数据。"""

        collection = self.inventory_service.get_collection()
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

    def _prepare_chunk_prompt(self, chunks: Sequence[dict], limit: int = 8) -> str:
        """将 chunk 转换为 Prompt 片段。"""

        lines: List[str] = []
        for chunk in chunks[:limit]:
            snippet = self._summarize_text(chunk.get("text", ""), "", max_length=500)
            lines.append(
                f"[chunk_id={chunk.get('id','')} page={chunk.get('page','?')}] {snippet}"
            )
        return "\n".join(lines)

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

        try:
            chunks = self._fetch_chunks(document_id)
        except Exception as e:
            print(f"Error fetching chunks: {e}")
            chunks = []
        base_date = datetime.now(timezone.utc)
        cpote_payload: CPOTEAgentPayload | None = None

        if self.deepseek_client.is_available and chunks:
            try:
                cpote_payload = self._call_cpote_agent(document, assignment_title, chunks)
            except Exception:
                cpote_payload = None

        if cpote_payload:
            cpote = cpote_payload.cpote
            milestones = self._normalize_milestones(cpote_payload.milestones, base_date)
        else:
            cpote, milestones = self._fallback_cpote(document, assignment_title, chunks, base_date)

        summary = self._summarize_text(
            chunks[0]["text"] if chunks else "",
            fallback=f"基于《{document.filename}》的教学设计",
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

    def _call_cpote_agent(
        self,
        document: Document,
        assignment_title: str,
        chunks: Sequence[dict],
    ) -> CPOTEAgentPayload:
        prompt_chunks = self._prepare_chunk_prompt(chunks)
        user_prompt = (
            f"Assignment Title: {assignment_title}\n"
            f"Document: {document.filename}\n"
            f"Retrieved snippets:\n{prompt_chunks}\n"
            "请输出 JSON：{\"cpote\": {...}, \"milestones\": [...]}，"
            "source_refs 引用 chunk_id，milestones 描述四个阶段及截止时间。"
        )
        return self.deepseek_client.structured_predict(
            CPOTEAgentPayload,
            CPOTE_SYSTEM_PROMPT,
            user_prompt,
        )

    def _fallback_cpote(
        self,
        document: Document,
        assignment_title: str,
        chunks: Sequence[dict],
        base_date: datetime,
    ) -> tuple[CPOTEExtraction, List[Milestone]]:
        first_text = chunks[0]["text"] if chunks else ""
        cpote = CPOTEExtraction(
            context=f"围绕文档《{document.filename}》生成的教学场景。",
            problem=self._summarize_text(first_text, "需根据资料补充问题描述"),
            objective=f"完成 {assignment_title} 的学习目标。",
            task=self._summarize_text(first_text, "请依据文档内容规划学习任务"),
            evaluation="按参与度、协作、探究、创新、成果五维进行评价。",
            source_refs=[
                {
                    "document_id": document.id,
                    "page": chunk.get("page", 1),
                    "chunk_id": chunk.get("id", ""),
                    "text": self._summarize_text(chunk.get("text", ""), "", max_length=160),
                }
                for chunk in chunks[:8]
            ],
        )
        milestones = self._default_milestones(base_date)
        return cpote, milestones

    def _default_milestones(self, base_date: datetime) -> List[Milestone]:
        templates = [
            ("组队与分工", "明确分工并提交分工表"),
            ("调查与研究", "提交数据或草稿"),
            ("成果制作", "制作汇报材料"),
            ("汇报与评价", "完成最终汇报"),
        ]
        milestones: List[Milestone] = []
        for idx, (name, description) in enumerate(templates, start=1):
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
        return milestones

    def _normalize_milestones(
        self,
        milestones: Sequence[Milestone],
        base_date: datetime,
    ) -> List[Milestone]:
        if not milestones:
            return self._default_milestones(base_date)
        normalized: List[Milestone] = []
        for idx, milestone in enumerate(milestones, start=1):
            due_at = milestone.due_at or (base_date + timedelta(days=7 * idx)).isoformat().replace(
                "+00:00", "Z"
            )
            normalized.append(
                Milestone(
                    index=idx,
                    name=milestone.name or f"阶段{idx}",
                    description=milestone.description or "请补充阶段描述",
                    due_at=due_at,
                    submission_requirements=milestone.submission_requirements,
                )
            )
        return normalized

    def evaluate_submission(
        self, db: Session, group_id: int, milestone_index: int, content: SubmissionContent
    ) -> tuple[Submission, EvaluationResult]:
        """根据提交内容生成 AI/规则混合的评分并写入 Submission。"""

        group = db.get(ProjectGroup, group_id)
        if not group:
            raise ValueError("Group not found")

        assignment = group.assignment
        if not assignment:
            raise ValueError("Assignment not found for group")

        evaluation: EvaluationResult | None = None
        if self.deepseek_client.is_available:
            try:
                evaluation = self._call_evaluation_agent(
                    assignment, milestone_index, content
                )
            except Exception:
                evaluation = None

        if evaluation is None:
            evaluation = self._rule_based_evaluation(content)

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

    def _call_evaluation_agent(
        self,
        assignment: Assignment,
        milestone_index: int,
        content: SubmissionContent,
    ) -> EvaluationResult:
        rubric = assignment.rubric_json or self._default_rubric()
        rubric_text = json.dumps(rubric, ensure_ascii=False)
        cpote_text = (
            json.dumps(assignment.cpote_json, ensure_ascii=False)
            if assignment.cpote_json
            else "null"
        )
        attachments = content.attachments or []
        attachment_summary = (
            ", ".join(f"{att.filename}({att.type})" for att in attachments) if attachments else "无"
        )
        submission_text = content.text.strip() or "无正文"

        user_prompt = (
            f"Assignment Title: {assignment.title}\n"
            f"Milestone Index: {milestone_index}\n"
            f"Rubric JSON: {rubric_text}\n"
            f"CPOTE JSON: {cpote_text}\n"
            f"Submission Text:\n{submission_text}\n"
            f"Attachments: {attachment_summary}\n"
            "请返回 EvaluationResult 结构，字段含 scores/radar_data/summary/improvements/evidence。"
        )
        evaluation = self.gemini_client.structured_predict(
            EvaluationResult,
            EVALUATION_SYSTEM_PROMPT,
            user_prompt,
        )
        return self._post_process_evaluation(evaluation)

    def _post_process_evaluation(self, evaluation: EvaluationResult) -> EvaluationResult:
        dims = ["participation", "collaboration", "inquiry", "innovation", "result"]
        values = [getattr(evaluation.scores, dim) for dim in dims]
        evaluation.scores.overall = int(sum(values) / len(values))
        evaluation.radar_data = [
            RadarPoint(dimension=dim, score=getattr(evaluation.scores, dim)) for dim in dims
        ]
        if not evaluation.improvements:
            evaluation.improvements = [
                "结合 Rubric 填充更具体的改进建议。",
                "补充数据或证据以支撑论点。",
            ]
        return evaluation

    def _rule_based_evaluation(self, content: SubmissionContent) -> EvaluationResult:
        scores = {
            "participation": self._score_text(content.text, 0),
            "collaboration": self._score_text(content.text, 2),
            "inquiry": self._score_text(content.text, 4),
            "innovation": self._score_text(content.text, 6),
            "result": self._score_text(content.text, 8),
        }
        overall = int(sum(scores.values()) / len(scores))
        summary = self._summarize_text(
            content.text, "提交内容较少，请补充细节以获得更准确的评价。"
        )
        improvements = [
            "补充可量化的数据或证据以支持论点。",
            "在报告中明确分工与协作过程，提升协作得分。",
        ]
        evidence = [
            EvidenceItem(
                source="submission_text",
                quote=self._summarize_text(content.text, "无提交内容", max_length=80),
                reason="基于提交文本提取的关键表述。",
            )
        ]
        return EvaluationResult(
            scores=ScoreBreakdown(overall=overall, **scores),
            radar_data=[RadarPoint(dimension=dim, score=value) for dim, value in scores.items()],
            summary=summary,
            improvements=improvements,
            evidence=evidence,
        )

    def _score_text(self, text: str, offset: int) -> int:
        if not text.strip():
            return 10
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        value = int.from_bytes(digest[offset : offset + 2], "big")
        return 50 + value % 51  # 50-100 之间
