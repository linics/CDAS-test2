"""面向前端的作业、分组与提交接口（Step 4）。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.frontend import (
    CreateGroupRequest,
    CreateSubmissionRequest,
    GroupResponse,
    SubmissionResponse,
)
from app.schemas.step0 import AssignmentConfig, Group, Submission
from app.services.assignments import AssignmentService


router = APIRouter(tags=["frontend"])
assignment_service = AssignmentService()


@router.get("/assignments/{assignment_id}", response_model=AssignmentConfig, tags=["assignments"])
def get_assignment_config(assignment_id: int, db: Session = Depends(get_db)) -> AssignmentConfig:
    try:
        return assignment_service.get_assignment_config(db, assignment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/groups", response_model=list[Group], tags=["groups"])
def list_groups(
    assignment_id: int | None = Query(None, description="按作业过滤小组"),
    db: Session = Depends(get_db),
) -> list[Group]:
    return assignment_service.list_groups(db, assignment_id)


@router.post("/groups", response_model=GroupResponse, tags=["groups"])
def create_group(payload: CreateGroupRequest, db: Session = Depends(get_db)) -> GroupResponse:
    try:
        return assignment_service.create_group(
            db=db, assignment_id=payload.assignment_id, name=payload.name, members=payload.members
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submissions", response_model=SubmissionResponse, tags=["submissions"])
def create_submission(
    payload: CreateSubmissionRequest, db: Session = Depends(get_db)
) -> SubmissionResponse:
    try:
        return assignment_service.create_submission(
            db=db,
            assignment_id=payload.assignment_id,
            group_id=payload.group_id,
            milestone_index=payload.milestone_index,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/submissions/{submission_id}", response_model=Submission, tags=["submissions"])
def get_submission(submission_id: int, db: Session = Depends(get_db)) -> Submission:
    try:
        return assignment_service.get_submission(db, submission_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
