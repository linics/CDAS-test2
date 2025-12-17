"""Step 0 data contract definitions used across CDAS services.

These Pydantic models mirror the unified JSON contracts described in
``docs/CDAS_step_plan.md`` so backend and frontend can share consistent
schemas during the refactor. All fields use snake_case and are designed
for direct serialization.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """Reference to the original document chunk used for CPOTE extraction."""

    document_id: Union[str, int]
    page: int
    chunk_id: str
    text: str


class CPOTEExtraction(BaseModel):
    """C-POTE structure extracted from curriculum documents."""

    context: str
    problem: str
    objective: str
    task: str
    evaluation: str
    source_refs: List[SourceRef] = Field(default_factory=list)


class Milestone(BaseModel):
    """Milestone within an assignment, ordered by a 1-based index."""

    index: int
    name: str
    description: str
    due_at: str
    submission_requirements: Optional[str] = None


class Member(BaseModel):
    """Member participating in a project group."""

    name: str
    role: str
    contact: Optional[str] = None


class Group(BaseModel):
    """Project group container with members."""

    id: Union[str, int]
    assignment_id: Union[str, int]
    name: str
    members: List[Member] = Field(default_factory=list)


class Rubric(BaseModel):
    """Rubric used to keep evaluation consistent across submissions."""

    dimensions: List[str]
    scale: str
    criteria: Dict[str, str]


class Attachment(BaseModel):
    """Optional attachment for a submission."""

    filename: str
    url: str
    type: str


class SubmissionContent(BaseModel):
    """Structured submission content with optional attachments."""

    text: str
    attachments: List[Attachment] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """Five-dimension score breakdown with overall aggregate."""

    participation: int
    collaboration: int
    inquiry: int
    innovation: int
    result: int
    overall: int


class RadarPoint(BaseModel):
    """Single radar chart datapoint for the evaluation dimensions."""

    dimension: str
    score: int


class EvidenceItem(BaseModel):
    """Evidence supporting evaluation scores."""

    source: str
    quote: str
    reason: str


class EvaluationResult(BaseModel):
    """AI evaluation output attached to submissions."""

    scores: ScoreBreakdown
    radar_data: List[RadarPoint] = Field(default_factory=list)
    summary: str
    improvements: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)


class Submission(BaseModel):
    """Submission for a milestone within an assignment."""

    id: Union[str, int]
    group_id: Union[str, int]
    assignment_id: Union[str, int]
    milestone_index: int
    submitted_at: str
    content: SubmissionContent
    ai_evaluation: Optional[EvaluationResult] = None


class AssignmentConfig(BaseModel):
    """Aggregated assignment configuration shared with clients."""

    assignment_id: Union[str, int]
    title: str
    cpote: CPOTEExtraction
    milestones: List[Milestone] = Field(default_factory=list)
    groups: List[Group] = Field(default_factory=list)
    rubric: Rubric
