"""作业评价API - 教师评价/自评/互评。"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    Assignment,
    Evaluation,
    Submission,
    User,
    EvaluationType,
    EvaluationLevel,
    SubmissionStatus,
)
from app.api.v2.auth import get_current_user, require_teacher
from app.services.ai import DeepSeekJSONClient

router = APIRouter()


# === Schemas ===

class TeacherEvaluationCreate(BaseModel):
    submission_id: int
    score_level: EvaluationLevel
    score_numeric: Optional[int] = None
    dimension_scores_json: Dict[str, int] = Field(default_factory=dict)
    feedback: str


class SelfEvaluationCreate(BaseModel):
    submission_id: int
    completion: int = Field(ge=1, le=4)  # 任务完成度 1-4
    effort: int = Field(ge=1, le=4)      # 过程投入度 1-4
    difficulties: str = ""               # 困难与克服
    gains: str = ""                      # 主要收获
    improvement: str = ""                # 改进方向


class PeerEvaluationCreate(BaseModel):
    submission_id: int
    quality: int = Field(ge=1, le=4)     # 成果质量 1-4
    clarity: int = Field(ge=1, le=4)     # 表达清晰度 1-4
    highlights: str = ""                 # 亮点发现
    suggestions: str = ""                # 改进建议


class EvaluationResponse(BaseModel):
    id: int
    submission_id: int
    evaluator_id: int
    evaluation_type: EvaluationType
    score_level: Optional[EvaluationLevel]
    score_numeric: Optional[int]
    dimension_scores_json: Dict[str, int]
    feedback: Optional[str]
    ai_generated: bool
    is_anonymous: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int


# === Helpers ===

class AIEvaluationSuggestion(BaseModel):
    suggested_level: str
    suggested_score: int
    dimension_scores: Dict[str, int] = Field(default_factory=dict)
    feedback: str = ""
    evidence: List[Dict[str, str]] = Field(default_factory=list)


def _normalize_rubric_dimensions(rubric: Dict[str, Any]) -> List[Dict[str, Any]]:
    dimensions = rubric.get("dimensions") or []
    normalized: List[Dict[str, Any]] = []
    if isinstance(dimensions, list):
        for idx, dim in enumerate(dimensions, start=1):
            if isinstance(dim, dict):
                name = dim.get("name") or dim.get("dimension") or f"Dimension {idx}"
                weight = dim.get("weight")
                try:
                    weight = int(weight)
                except Exception:
                    weight = 0
                description = dim.get("description") or ""
                normalized.append({"name": name, "weight": weight, "description": description})
            elif isinstance(dim, str):
                normalized.append({"name": dim, "weight": 0, "description": ""})
    return normalized


def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except Exception:
        return 0
    return max(0, min(100, score))


def _compute_weighted_score(dimensions: List[Dict[str, Any]], scores: Dict[str, int]) -> int:
    if not dimensions:
        return _clamp_score(sum(scores.values()) / len(scores)) if scores else 0
    weights = [max(0, int(dim.get("weight") or 0)) for dim in dimensions]
    if sum(weights) == 0:
        weights = [1 for _ in dimensions]
    total_weight = sum(weights)
    total = 0.0
    for dim, weight in zip(dimensions, weights):
        total += _clamp_score(scores.get(dim["name"], 0)) * weight
    return _clamp_score(total / total_weight)


def _score_to_level(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _format_phase_context(phase: Dict[str, Any] | None) -> str:
    if not phase:
        return "N/A"
    title = phase.get("title") or phase.get("name") or "Phase"
    lines = [f"{title}"]
    steps = phase.get("steps") or []
    if isinstance(steps, dict):
        steps = [steps]
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        primary = step.get("content") or step.get("description") or step.get("name") or f"Step {idx}"
        lines.append(f"- Step {idx}: {primary}")
        desc = step.get("description")
        if desc and desc != primary:
            lines.append(f"  - Description: {desc}")
        checkpoints = step.get("checkpoints") or []
        if isinstance(checkpoints, dict):
            checkpoints = [checkpoints]
        for cp in checkpoints:
            if isinstance(cp, dict):
                cp_text = cp.get("content") or cp.get("text") or cp.get("description") or ""
            else:
                cp_text = str(cp)
            if cp_text:
                lines.append(f"  - Checkpoint: {cp_text}")
    return "\n".join(lines)


# === API 端点 ===

@router.post("/teacher", response_model=EvaluationResponse)
async def create_teacher_evaluation(
    data: TeacherEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """教师评价。"""
    submission = db.query(Submission).filter(Submission.id == data.submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    
    evaluation = Evaluation(
        submission_id=data.submission_id,
        evaluator_id=current_user.id,
        evaluation_type=EvaluationType.TEACHER,
        score_level=data.score_level,
        score_numeric=data.score_numeric,
        dimension_scores_json=data.dimension_scores_json,
        feedback=data.feedback,
        ai_generated=False,
        is_anonymous=False,
    )
    db.add(evaluation)
    
    # 更新提交状态为已评分
    submission.status = SubmissionStatus.GRADED
    
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.post("/self", response_model=EvaluationResponse)
async def create_self_evaluation(
    data: SelfEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """学生自评。"""
    submission = db.query(Submission).filter(Submission.id == data.submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能对自己的提交进行自评")
    
    # 检查是否已有自评
    existing = db.query(Evaluation).filter(
        Evaluation.submission_id == data.submission_id,
        Evaluation.evaluator_id == current_user.id,
        Evaluation.evaluation_type == EvaluationType.SELF
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已提交过自评")
    
    evaluation = Evaluation(
        submission_id=data.submission_id,
        evaluator_id=current_user.id,
        evaluation_type=EvaluationType.SELF,
        self_evaluation_json={
            "completion": data.completion,
            "effort": data.effort,
            "difficulties": data.difficulties,
            "gains": data.gains,
            "improvement": data.improvement,
        },
        is_anonymous=False,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.post("/peer", response_model=EvaluationResponse)
async def create_peer_evaluation(
    data: PeerEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """学生互评。"""
    submission = db.query(Submission).filter(Submission.id == data.submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.student_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己互评")
    
    # 检查是否已评过
    existing = db.query(Evaluation).filter(
        Evaluation.submission_id == data.submission_id,
        Evaluation.evaluator_id == current_user.id,
        Evaluation.evaluation_type == EvaluationType.PEER
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已对该提交进行过互评")
    
    evaluation = Evaluation(
        submission_id=data.submission_id,
        evaluator_id=current_user.id,
        evaluation_type=EvaluationType.PEER,
        peer_evaluation_json={
            "quality": data.quality,
            "clarity": data.clarity,
            "highlights": data.highlights,
            "suggestions": data.suggestions,
        },
        is_anonymous=True,  # 互评默认匿名
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/submission/{submission_id}", response_model=EvaluationListResponse)
async def list_submission_evaluations(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取某提交的所有评价。"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    
    # 学生只能看自己的提交的评价
    from app.models.user import UserRole
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此提交的评价")
    
    evaluations = db.query(Evaluation).filter(Evaluation.submission_id == submission_id).all()
    return {"evaluations": evaluations, "total": len(evaluations)}


@router.post("/ai-assist")
async def ai_assist_evaluation(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """AI-assisted evaluation suggestion."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="submission not found")

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="assignment not found")

    rubric = assignment.rubric_json or {}
    rubric_dims = _normalize_rubric_dimensions(rubric)
    phase = None
    if isinstance(assignment.phases_json, list) and assignment.phases_json:
        if submission.phase_index is not None and submission.phase_index < len(assignment.phases_json):
            phase = assignment.phases_json[submission.phase_index]
    phase_context = _format_phase_context(phase)

    content_json = submission.content_json or {}
    submission_text = content_json.get("text") if isinstance(content_json, dict) else None
    if not submission_text:
        submission_text = json.dumps(content_json, ensure_ascii=False)

    attachments = submission.attachments_json or []
    checkpoints = submission.checkpoints_json or {}

    system_prompt = (
        "You are a rigorous teacher. Score each rubric dimension from 0-100, "
        "cite evidence from the submission, and compute a weighted overall score. "
        "Return JSON only."
    )

    rubric_text = json.dumps({"dimensions": rubric_dims}, ensure_ascii=False)
    objectives_text = json.dumps(assignment.objectives_json or {}, ensure_ascii=False)

    user_prompt = (
        "Assignment context:\n"
        f"- Title: {assignment.title}\n"
        f"- Topic: {assignment.topic}\n"
        f"- Description: {assignment.description or ''}\n"
        f"- Objectives JSON: {objectives_text}\n\n"
        f"Current phase tasks:\n{phase_context}\n\n"
        "Submission content:\n"
        f"- text: {submission_text}\n"
        f"- attachments: {attachments}\n"
        f"- checkpoints: {checkpoints}\n\n"
        "Rubric (dimensions with weights and descriptions):\n"
        f"{rubric_text}\n\n"
        "Return JSON with fields:\n"
        "- suggested_score (0-100, weighted by rubric)\n"
        "- suggested_level (A/B/C/D)\n"
        "- dimension_scores (object with keys exactly matching rubric dimension names)\n"
        "- feedback (concise)\n"
        "- evidence (list of {source, quote, reason})\n"
    )

    settings = get_settings()
    client = DeepSeekJSONClient(settings, temperature=0.2, max_output_tokens=1200)
    suggestion: AIEvaluationSuggestion | None = None
    if client.is_available:
        try:
            suggestion = client.structured_predict(AIEvaluationSuggestion, system_prompt, user_prompt)
        except Exception:
            suggestion = None

    if suggestion is None:
        fallback_scores = {dim["name"]: 70 for dim in rubric_dims}
        overall = _compute_weighted_score(rubric_dims, fallback_scores)
        suggestion = AIEvaluationSuggestion(
            suggested_level=_score_to_level(overall),
            suggested_score=overall,
            dimension_scores=fallback_scores,
            feedback="Provide more concrete evidence and align each step with rubric requirements.",
            evidence=[],
        )

    normalized_scores: Dict[str, int] = {}
    for dim in rubric_dims:
        name = dim["name"]
        raw_value = suggestion.dimension_scores.get(name, suggestion.suggested_score)
        normalized_scores[name] = _clamp_score(raw_value)
    overall_score = _compute_weighted_score(rubric_dims, normalized_scores)
    suggestion.suggested_score = overall_score
    suggestion.suggested_level = _score_to_level(overall_score)
    suggestion.dimension_scores = normalized_scores

    return {
        "message": "AI evaluation suggestion generated",
        "suggestion": suggestion.model_dump(),
    }


@router.get("/my-received", response_model=EvaluationListResponse)
async def list_my_received_evaluations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """学生查看自己收到的所有评价。"""
    # 找到学生的所有提交
    my_submissions = db.query(Submission).filter(Submission.student_id == current_user.id).all()
    submission_ids = [s.id for s in my_submissions]
    
    evaluations = db.query(Evaluation).filter(Evaluation.submission_id.in_(submission_ids)).all()
    return {"evaluations": evaluations, "total": len(evaluations)}
