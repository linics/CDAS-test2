"""Agent layer API 模型定义（Step 3）。

提供 CPOTE 解析与提交评价的请求/响应模型，复用 Step 0
的数据契约以保持前后端一致性。
"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.step0 import CPOTEExtraction, EvaluationResult, Milestone, SubmissionContent


class ParseCPOTERequest(BaseModel):
    """解析文档为 C-POTE 以及默认里程碑的入参。"""

    document_id: int
    assignment_title: str


class ParseCPOTEResponse(BaseModel):
    """返回生成的作业配置片段。"""

    assignment_id: int
    cpote: CPOTEExtraction
    milestones: list[Milestone]


class EvaluateSubmissionRequest(BaseModel):
    """对提交内容进行五维评价的入参。"""

    group_id: int
    milestone_index: int
    content: SubmissionContent


class EvaluateSubmissionResponse(BaseModel):
    """返回评价结果与关联的提交 ID。"""

    submission_id: int
    evaluation: EvaluationResult
