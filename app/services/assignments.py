"""Assignment & frontend-facing service functions (Step 4).

提供前端渲染需要的聚合数据：AssignmentConfig、Group 列表、
Submission 详情等。保持与 Step 0 Pydantic 模型一致，方便直接
在 API 响应中返回。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Assignment, ProjectGroup, Submission
from app.schemas.step0 import (
    AssignmentConfig,
    CPOTEExtraction,
    EvaluationResult,
    Group,
    Member,
    Milestone,
    Rubric,
    Submission as SubmissionSchema,
    SubmissionContent,
)


class AssignmentService:
    """封装与作业、分组、提交相关的查询与创建逻辑。"""

    def _format_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

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

    def _serialize_group(self, group: ProjectGroup) -> Group:
        return Group(
            id=group.id,
            assignment_id=group.assignment_id,
            name=group.name,
            members=[Member.model_validate(m) for m in (group.members_json or [])],
        )

    def _serialize_submission(self, submission: Submission) -> SubmissionSchema:
        content = SubmissionContent.model_validate(submission.content_json or {"text": ""})
        ai_evaluation = (
            EvaluationResult.model_validate(submission.ai_evaluation_json)
            if submission.ai_evaluation_json
            else None
        )
        return SubmissionSchema(
            id=submission.id,
            group_id=submission.group_id,
            assignment_id=submission.assignment_id,
            milestone_index=submission.milestone_index,
            submitted_at=self._format_datetime(submission.submitted_at),
            content=content,
            ai_evaluation=ai_evaluation,
        )

    def get_assignment_config(self, db: Session, assignment_id: int) -> AssignmentConfig:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")
        if not assignment.cpote_json:
            raise ValueError("Assignment missing CPOTE data")

        rubric_data = assignment.rubric_json or self._default_rubric()
        cpote = CPOTEExtraction.model_validate(assignment.cpote_json)
        milestones = [Milestone.model_validate(m) for m in assignment.milestones_json or []]
        groups = [self._serialize_group(group) for group in assignment.groups]

        return AssignmentConfig(
            assignment_id=assignment.id,
            title=assignment.title,
            cpote=cpote,
            milestones=milestones,
            groups=groups,
            rubric=Rubric.model_validate(rubric_data),
        )

    def list_groups(self, db: Session, assignment_id: int | None = None) -> list[Group]:
        query = db.query(ProjectGroup)
        if assignment_id is not None:
            query = query.filter(ProjectGroup.assignment_id == assignment_id)
        groups: Iterable[ProjectGroup] = query.order_by(ProjectGroup.id.asc()).all()
        return [self._serialize_group(group) for group in groups]

    def create_group(
        self, db: Session, assignment_id: int, name: str, members: list[Member]
    ) -> Group:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")

        group = ProjectGroup(
            assignment_id=assignment_id,
            name=name,
            members_json=[m.model_dump() for m in members],
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        return self._serialize_group(group)

    def create_submission(
        self,
        db: Session,
        assignment_id: int,
        group_id: int,
        milestone_index: int,
        content: SubmissionContent,
    ) -> SubmissionSchema:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")

        group = db.get(ProjectGroup, group_id)
        if not group or group.assignment_id != assignment_id:
            raise ValueError("Group not found for assignment")

        submission = Submission(
            assignment_id=assignment_id,
            group_id=group_id,
            milestone_index=milestone_index,
            content_json=content.model_dump(),
            ai_evaluation_json=None,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return self._serialize_submission(submission)

    def get_submission(self, db: Session, submission_id: int) -> SubmissionSchema:
        submission = db.get(Submission, submission_id)
        if not submission:
            raise ValueError("Submission not found")
        return self._serialize_submission(submission)
