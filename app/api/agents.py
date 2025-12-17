"""Agent 相关路由（Step 3）。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_db
from app.schemas.agents import (
    EvaluateSubmissionRequest,
    EvaluateSubmissionResponse,
    ParseCPOTERequest,
    ParseCPOTEResponse,
)
from app.schemas.step0 import CPOTEExtraction, EvaluationResult, Milestone
from app.services.agents import AgentService


router = APIRouter(prefix="/agents", tags=["agents"])
agent_service = AgentService(get_settings())


@router.post("/parse_cpote", response_model=ParseCPOTEResponse)
def parse_cpote(
    payload: ParseCPOTERequest, db: Session = Depends(get_db)
) -> ParseCPOTEResponse:
    try:
        assignment = agent_service.parse_cpote(
            db, document_id=payload.document_id, assignment_title=payload.assignment_title
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    cpote = CPOTEExtraction.model_validate(assignment.cpote_json)
    milestones = [Milestone.model_validate(m) for m in assignment.milestones_json]
    return ParseCPOTEResponse(
        assignment_id=assignment.id,
        cpote=cpote,
        milestones=milestones,
    )


@router.post("/evaluate_submission", response_model=EvaluateSubmissionResponse)
def evaluate_submission(
    payload: EvaluateSubmissionRequest, db: Session = Depends(get_db)
) -> EvaluateSubmissionResponse:
    try:
        submission, evaluation = agent_service.evaluate_submission(
            db,
            group_id=payload.group_id,
            milestone_index=payload.milestone_index,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    eval_model = EvaluationResult.model_validate(evaluation.model_dump())
    return EvaluateSubmissionResponse(submission_id=submission.id, evaluation=eval_model)
