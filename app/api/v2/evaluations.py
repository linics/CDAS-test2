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
    score_numeric: int
    score_level: Optional[EvaluationLevel] = None
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
    score_level_label: Optional[str] = None
    dimension_level_labels: Dict[str, str] = Field(default_factory=dict)
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


_LEVEL_LABELS = {
    "excellent": "优秀",
    "good": "良好",
    "pass": "合格",
    "improve": "需改进",
}


def _level_label(level: str) -> str:
    return _LEVEL_LABELS.get(level, "")


def _normalize_level_input(value: Any) -> str:
    if isinstance(value, EvaluationLevel):
        return value.value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in _LEVEL_LABELS:
            return cleaned
        if cleaned in {"a", "b", "c", "d"}:
            return {"a": "excellent", "b": "good", "c": "pass", "d": "improve"}[cleaned]
        if cleaned in {"优秀", "良好", "合格", "需改进"}:
            return {
                "优秀": "excellent",
                "良好": "good",
                "合格": "pass",
                "需改进": "improve",
            }[cleaned]
    try:
        numeric = int(float(value))
    except Exception:
        return "improve"
    if numeric >= 90:
        return "excellent"
    if numeric >= 75:
        return "good"
    if numeric >= 60:
        return "pass"
    if numeric >= 4:
        return "excellent"
    if numeric == 3:
        return "good"
    if numeric == 2:
        return "pass"
    return "improve"


def _normalize_rubric_dimensions(rubric: Dict[str, Any]) -> List[Dict[str, Any]]:
    dimensions = rubric.get("dimensions") or []
    normalized: List[Dict[str, Any]] = []
    if isinstance(dimensions, list):
        for idx, dim in enumerate(dimensions, start=1):
            if isinstance(dim, dict):
                name = dim.get("name") or dim.get("dimension") or f"Dimension {idx}"
                levels = dim.get("levels") if isinstance(dim.get("levels"), dict) else {}
                normalized.append({"name": name, "levels": levels})
            elif isinstance(dim, str):
                normalized.append({"name": dim, "levels": {}})
    return normalized


def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except Exception:
        return 1
    return max(1, min(4, score))


def _level_to_score(level: str) -> int:
    return {
        "excellent": 4,
        "good": 3,
        "pass": 2,
        "improve": 1,
    }.get(level, 2)


def _normalize_dimension_scores(
    dimensions: List[Dict[str, Any]],
    scores: Dict[str, Any],
    fallback: int = 2,
) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    for dim in dimensions:
        name = dim.get("name")
        raw_value = scores.get(name, fallback)
        level = _normalize_level_input(raw_value)
        normalized[name] = _clamp_score(_level_to_score(level))
    return normalized


def _compute_average_score(scores: Dict[str, int]) -> int:
    if not scores:
        return 0
    average = sum(scores.values()) / len(scores)
    return _clamp_score(int(average + 0.5))


def _build_dimension_labels(scores: Dict[str, int]) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for name, score in scores.items():
        labels[name] = _level_label(_score_to_level(score))
    return labels


def _build_evaluation_response(evaluation: Evaluation) -> EvaluationResponse:
    response = EvaluationResponse.model_validate(evaluation, from_attributes=True)
    if response.score_level is not None:
        response.score_level_label = _level_label(response.score_level.value)
    response.dimension_level_labels = _build_dimension_labels(response.dimension_scores_json or {})
    return response


def _score_to_level(score: int) -> str:
    return _normalize_level_input(score)


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

    level_map = {
        4: EvaluationLevel.EXCELLENT,
        3: EvaluationLevel.GOOD,
        2: EvaluationLevel.PASS,
        1: EvaluationLevel.IMPROVE,
    }
    if data.score_numeric not in level_map:
        raise HTTPException(status_code=400, detail="score_numeric must be 1-4")
    score_level = data.score_level or level_map[data.score_numeric]
    
    evaluation = Evaluation(
        submission_id=data.submission_id,
        evaluator_id=current_user.id,
        evaluation_type=EvaluationType.TEACHER,
        score_level=score_level,
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
    return _build_evaluation_response(evaluation)


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
    return _build_evaluation_response(evaluation)


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
    return _build_evaluation_response(evaluation)


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
    return {"evaluations": [_build_evaluation_response(item) for item in evaluations], "total": len(evaluations)}


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
        "You are a rigorous teacher. Score each rubric dimension from 1-4, "
        "cite evidence from the submission, and compute an overall average score. "
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
        "Rubric (dimensions with levels):\n"
        f"{rubric_text}\n\n"
        "Return JSON with fields:\n"
        "- suggested_score (1-4, average)\n"
        "- suggested_level (excellent/good/pass/improve)\n"
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
        fallback_scores = {dim["name"]: 2 for dim in rubric_dims}
        overall = _compute_average_score(fallback_scores)
        suggestion = AIEvaluationSuggestion(
            suggested_level=_score_to_level(overall),
            suggested_score=overall,
            dimension_scores=fallback_scores,
            feedback="Provide more concrete evidence and align each step with rubric requirements.",
            evidence=[],
        )

    normalized_scores = _normalize_dimension_scores(
        rubric_dims,
        suggestion.dimension_scores,
        fallback=suggestion.suggested_score,
    )
    overall_score = _compute_average_score(normalized_scores)
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
    return {"evaluations": [_build_evaluation_response(item) for item in evaluations], "total": len(evaluations)}
