"""Step 4 前端对接所需的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.step0 import Group, Member, Submission, SubmissionContent


class CreateGroupRequest(BaseModel):
    """创建小组的入参。"""

    assignment_id: int
    name: str
    members: list[Member] = Field(default_factory=list)


class CreateSubmissionRequest(BaseModel):
    """保存阶段性提交的入参（不触发 AI 评价）。"""

    assignment_id: int
    group_id: int
    milestone_index: int
    content: SubmissionContent


class GroupResponse(Group):
    """便于 FastAPI 返回的 Group alias。"""

    pass


class SubmissionResponse(Submission):
    """便于 FastAPI 返回的 Submission alias。"""

    pass
