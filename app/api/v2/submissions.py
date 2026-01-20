"""作业提交API。"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import (
    Submission,
    Assignment,
    User,
    SubmissionStatus,
    SubmissionMode,
)
from app.api.v2.auth import get_current_user, require_student

router = APIRouter()


# === Schemas ===

class AttachmentSchema(BaseModel):
    filename: str
    url: str
    type: str
    size_bytes: Optional[int] = None


class SubmissionCreate(BaseModel):
    assignment_id: int
    phase_index: int
    step_index: Optional[int] = None
    group_id: Optional[int] = None
    content_json: Dict[str, Any] = Field(default_factory=dict)
    attachments_json: List[AttachmentSchema] = Field(default_factory=list)
    checkpoints_json: Dict[str, bool] = Field(default_factory=dict)


class SubmissionUpdate(BaseModel):
    content_json: Optional[Dict[str, Any]] = None
    attachments_json: Optional[List[Dict[str, Any]]] = None
    checkpoints_json: Optional[Dict[str, bool]] = None


# 嵌套的作业简要信息
class AssignmentBrief(BaseModel):
    id: int
    title: str
    topic: str
    description: Optional[str]
    assignment_type: str
    phases_json: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    group_id: Optional[int]
    phase_index: int
    step_index: Optional[int]
    status: SubmissionStatus
    content_json: Dict[str, Any]
    attachments_json: List[Dict[str, Any]]
    checkpoints_json: Dict[str, bool]
    created_at: datetime
    submitted_at: Optional[datetime]
    # 嵌套作业信息
    assignment: Optional[AssignmentBrief] = None
    next_submission_id: Optional[int] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    submissions: List[SubmissionResponse]
    total: int


# === Helpers ===

def _normalize_status(value: Any) -> str:
    if isinstance(value, SubmissionStatus):
        return value.value
    if isinstance(value, str):
        return value.lower()
    return str(value)


# === API 端点 ===

@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """创建新提交（学生权限）。"""
    # 验证作业存在
    assignment = db.query(Assignment).filter(Assignment.id == data.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not assignment.is_published:
        raise HTTPException(status_code=400, detail="作业尚未发布")
    
    submission = Submission(
        assignment_id=data.assignment_id,
        student_id=current_user.id,
        group_id=data.group_id,
        phase_index=data.phase_index,
        step_index=data.step_index,
        content_json=data.content_json,
        attachments_json=[a.model_dump() for a in data.attachments_json],
        checkpoints_json=data.checkpoints_json,
        status=SubmissionStatus.DRAFT,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/my", response_model=SubmissionListResponse)
async def list_my_submissions(
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """学生查看自己的提交历史。"""
    query = db.query(Submission).options(joinedload(Submission.assignment)).filter(Submission.student_id == current_user.id)
    
    if assignment_id:
        query = query.filter(Submission.assignment_id == assignment_id)
    
    submissions = query.order_by(Submission.created_at.desc()).all()
    
    # 手动构造响应以包含嵌套的 assignment 信息
    result = []
    for sub in submissions:
        sub_dict = {
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "student_id": sub.student_id,
            "group_id": sub.group_id,
            "phase_index": sub.phase_index,
            "step_index": sub.step_index,
            "status": _normalize_status(sub.status),
            "content_json": sub.content_json or {},
            "attachments_json": sub.attachments_json or [],
            "checkpoints_json": sub.checkpoints_json or {},
            "created_at": sub.created_at,
            "submitted_at": sub.submitted_at,
            "assignment": {
                "id": sub.assignment.id,
                "title": sub.assignment.title,
                "topic": sub.assignment.topic,
                "description": sub.assignment.description,
                "assignment_type": sub.assignment.assignment_type.value,
                "phases_json": sub.assignment.phases_json or [],
            } if sub.assignment else None
        }
        result.append(sub_dict)
    
    return {"submissions": result, "total": len(result)}


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get submission detail."""
    submission = (
        db.query(Submission)
        .filter(Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="submission not found")

    from app.models.user import UserRole
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="forbidden")

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()

    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "student_id": submission.student_id,
        "group_id": submission.group_id,
        "phase_index": submission.phase_index,
        "step_index": submission.step_index,
        "status": _normalize_status(submission.status),
        "content_json": submission.content_json or {},
        "attachments_json": submission.attachments_json or [],
        "checkpoints_json": submission.checkpoints_json or {},
        "created_at": submission.created_at,
        "submitted_at": submission.submitted_at,
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "topic": assignment.topic,
            "description": assignment.description,
            "assignment_type": assignment.assignment_type.value,
            "phases_json": assignment.phases_json or [],
        } if assignment else None,
    }

@router.put("/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: int,
    data: SubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """更新提交（截止前）。"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能修改自己的提交")
    if submission.status == SubmissionStatus.GRADED:
        raise HTTPException(status_code=400, detail="已评分的提交不能修改")
    
    # 检查截止时间
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    if assignment.deadline and datetime.now(timezone.utc) > assignment.deadline:
        raise HTTPException(status_code=400, detail="已过截止时间，不能修改")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(submission, key, value)
    
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/{submission_id}/submit", response_model=SubmissionResponse)
async def submit_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """正式提交（从草稿变为已提交）。"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能提交自己的草稿")
    
    submission.status = SubmissionStatus.SUBMITTED
    submission.submitted_at = datetime.now(timezone.utc)

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    next_submission_id: Optional[int] = None
    if assignment and assignment.submission_mode != SubmissionMode.ONCE:
        phases = assignment.phases_json or []
        next_phase_index = submission.phase_index + 1
        if next_phase_index < len(phases):
            existing = (
                db.query(Submission)
                .filter(
                    Submission.assignment_id == submission.assignment_id,
                    Submission.student_id == submission.student_id,
                    Submission.phase_index == next_phase_index,
                )
                .first()
            )
            if existing:
                next_submission_id = existing.id
            else:
                next_submission = Submission(
                    assignment_id=submission.assignment_id,
                    student_id=submission.student_id,
                    group_id=submission.group_id,
                    phase_index=next_phase_index,
                    content_json={},
                    attachments_json=[],
                    checkpoints_json={},
                    status=SubmissionStatus.DRAFT,
                )
                db.add(next_submission)
                db.flush()
                next_submission_id = next_submission.id

    db.commit()
    db.refresh(submission)
    setattr(submission, "next_submission_id", next_submission_id)
    return submission


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """删除草稿提交。"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的提交")
    if submission.status != SubmissionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能删除草稿状态的提交")
    
    db.delete(submission)
    db.commit()


# === 教师端 ===

@router.get("/assignment/{assignment_id}", response_model=SubmissionListResponse)
async def list_assignment_submissions(
    assignment_id: int,
    phase_index: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """教师查看作业的所有提交。"""
    from app.models.user import UserRole
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="需要教师权限")
    
    query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
    
    if phase_index is not None:
        query = query.filter(Submission.phase_index == phase_index)
    
    submissions = query.order_by(Submission.submitted_at.desc()).all()
    return {"submissions": submissions, "total": len(submissions)}
