"""作业设计CRUD API。"""

import copy
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models import (
    Assignment, 
    ProjectGroup,
    User,
    AssignmentType,
    PracticalSubType,
    InquirySubType,
    InquiryDepth,
    SubmissionMode,
    SchoolStage,
    Subject,
)
from app.api.v2.auth import get_current_user, require_teacher
from app.services.ai import DeepSeekJSONClient
from app.services.inventory import InventoryService

router = APIRouter()


# === Schemas ===

class StepSchema(BaseModel):
    name: str
    description: str
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_checkpoint(cls, values: Any) -> Any:
        if isinstance(values, dict) and "checkpoint" in values and "checkpoints" not in values:
            values["checkpoints"] = [values["checkpoint"]]
        return values


class PhaseSchema(BaseModel):
    name: str
    order: int
    steps: List[StepSchema] = Field(default_factory=list)


class ObjectivesSchema(BaseModel):
    knowledge: str = ""  # 知识与技能
    process: str = ""    # 过程与方法
    emotion: str = ""    # 情感态度


class RubricDimensionSchema(BaseModel):
    name: str
    weight: int
    description: str


class RubricSchema(BaseModel):
    dimensions: List[RubricDimensionSchema] = Field(default_factory=list)


class AIAssignmentOutput(BaseModel):
    objectives: ObjectivesSchema
    phases: List[PhaseSchema]
    rubric: RubricSchema


class AssignmentCreate(BaseModel):
    title: str
    topic: str
    description: Optional[str] = None
    school_stage: SchoolStage
    grade: int = Field(ge=1, le=9)
    main_subject_id: int
    related_subject_ids: List[int] = Field(default_factory=list)
    assignment_type: AssignmentType
    practical_subtype: Optional[PracticalSubType] = None
    inquiry_subtype: Optional[InquirySubType] = None
    inquiry_depth: InquiryDepth = InquiryDepth.INTERMEDIATE
    submission_mode: SubmissionMode = SubmissionMode.PHASED
    duration_weeks: int = 2
    deadline: Optional[datetime] = None
    objectives_json: Optional[Dict[str, Any]] = None
    phases_json: Optional[List[Dict[str, Any]]] = None
    rubric_json: Optional[Dict[str, Any]] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    description: Optional[str] = None
    objectives_json: Optional[Dict[str, Any]] = None
    phases_json: Optional[List[Dict[str, Any]]] = None
    rubric_json: Optional[Dict[str, Any]] = None
    deadline: Optional[datetime] = None


class AssignmentResponse(BaseModel):
    id: int
    title: str
    topic: str
    description: Optional[str]
    school_stage: SchoolStage
    grade: int
    main_subject_id: int
    related_subject_ids: List[int]
    assignment_type: AssignmentType
    practical_subtype: Optional[PracticalSubType]
    inquiry_subtype: Optional[InquirySubType]
    inquiry_depth: InquiryDepth
    submission_mode: SubmissionMode
    duration_weeks: int
    deadline: Optional[datetime]
    objectives_json: Dict[str, Any]
    phases_json: List[Dict[str, Any]]
    rubric_json: Dict[str, Any]
    is_published: bool
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponse]
    total: int


class AssignmentPreviewResponse(BaseModel):
    objectives_json: Dict[str, Any]
    phases_json: List[Dict[str, Any]]
    rubric_json: Dict[str, Any]


class GroupCreate(BaseModel):
    name: str
    members_json: List[Dict[str, Any]] = Field(default_factory=list)


class GroupResponse(BaseModel):
    id: int
    assignment_id: int
    name: str
    members_json: List[Dict[str, Any]]

    class Config:
        from_attributes = True


# === API 端点 ===

@router.post("/preview", response_model=AssignmentPreviewResponse)
async def preview_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(require_teacher),
):
    """生成作业的 AI 预览内容，不入库。"""
    objectives = data.objectives_json or {}
    phases = data.phases_json or []
    rubric = data.rubric_json or {}
    if _is_empty_json(objectives) or _is_empty_json(phases) or _is_empty_json(rubric):
        gen_objectives, gen_phases, gen_rubric = _generate_ai_content(data)
        if _is_empty_json(objectives):
            objectives = gen_objectives
        if _is_empty_json(phases):
            phases = gen_phases
        if _is_empty_json(rubric):
            rubric = gen_rubric
    objectives, phases, rubric = _ensure_ai_defaults(data, objectives, phases, rubric)
    return {
        "objectives_json": objectives,
        "phases_json": phases,
        "rubric_json": rubric,
    }


@router.get("/ai-status")
async def ai_status(
    current_user: User = Depends(require_teacher),
):
    settings = get_settings()
    return {"available": bool(settings.deepseek_api_key), "model": settings.deepseek_model}


@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """创建新作业（教师权限）。"""
    objectives = data.objectives_json or {}
    phases = data.phases_json or []
    rubric = data.rubric_json or {}
    if _is_empty_json(objectives) or _is_empty_json(phases) or _is_empty_json(rubric):
        gen_objectives, gen_phases, gen_rubric = _generate_ai_content(data)
        if _is_empty_json(objectives):
            objectives = gen_objectives
        if _is_empty_json(phases):
            phases = gen_phases
        if _is_empty_json(rubric):
            rubric = gen_rubric
    objectives, phases, rubric = _ensure_ai_defaults(data, objectives, phases, rubric)
    assignment_payload = data.model_dump(
        exclude={"objectives_json", "phases_json", "rubric_json"}
    )
    assignment = Assignment(
        **assignment_payload,
        objectives_json=objectives,
        phases_json=phases,
        rubric_json=rubric,
        created_by=current_user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    db.execute(
        update(Assignment)
        .where(Assignment.id == assignment.id)
        .values(
            objectives_json=objectives,
            phases_json=phases,
            rubric_json=rubric,
        )
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/", response_model=AssignmentListResponse)
async def list_assignments(
    page: int = 1,
    page_size: int = 20,
    published_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取作业列表。教师看自己创建的，学生看已发布的。"""
    try:
        print(f"DEBUG: list_assignments ENTERED. User: {current_user.id}, Role: {current_user.role}")
        from app.models.user import UserRole
        
        query = db.query(Assignment)
        print(f"DEBUG: Query created")
        
        if current_user.role == UserRole.TEACHER:
            print("DEBUG: User is TEACHER")
            query = query.filter(Assignment.created_by == current_user.id)
        else:
            print("DEBUG: User is STUDENT")
            query = query.filter(Assignment.is_published == True)
            if current_user.grade is not None:
                query = query.filter(Assignment.grade == current_user.grade)
        
        if published_only:
            query = query.filter(Assignment.is_published == True)
        
        print("DEBUG: Executing count query...")
        total = query.count()
        print(f"DEBUG: Total count: {total}")
        
        print("DEBUG: Executing fetch query...")
        assignments = query.offset((page - 1) * page_size).limit(page_size).all()
        print(f"DEBUG: Fetched {len(assignments)} assignments")
        
        return {"assignments": assignments, "total": total}
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in list_assignments: {e}")
        print(traceback.format_exc())
        raise


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取作业详情。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """更新作业（教师权限）。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己创建的作业")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)
    
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """删除作业（教师权限）。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己创建的作业")
    
    db.delete(assignment)
    db.commit()


@router.post("/{assignment_id}/publish", response_model=AssignmentResponse)
async def publish_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """发布作业。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="只能发布自己创建的作业")
    
    assignment.is_published = True
    assignment.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{assignment_id}/generate-steps")
async def generate_steps(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """AI生成分步骤任务引导（待实现）。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    data = AssignmentCreate(
        title=assignment.title,
        topic=assignment.topic,
        description=assignment.description,
        school_stage=assignment.school_stage,
        grade=assignment.grade,
        main_subject_id=assignment.main_subject_id,
        related_subject_ids=assignment.related_subject_ids or [],
        assignment_type=assignment.assignment_type,
        practical_subtype=assignment.practical_subtype,
        inquiry_subtype=assignment.inquiry_subtype,
        inquiry_depth=assignment.inquiry_depth,
        submission_mode=assignment.submission_mode,
        duration_weeks=assignment.duration_weeks,
        deadline=assignment.deadline,
    )
    objectives, phases, rubric = _generate_ai_content(data)
    objectives, phases, rubric = _ensure_ai_defaults(data, objectives, phases, rubric)
    assignment.objectives_json = objectives
    assignment.phases_json = phases
    assignment.rubric_json = rubric
    db.commit()
    db.execute(
        update(Assignment)
        .where(Assignment.id == assignment.id)
        .values(
            objectives_json=objectives,
            phases_json=phases,
            rubric_json=rubric,
        )
    )
    db.commit()
    
    return {"message": "任务引导生成成功", "phases": phases}


# === 小组管理 ===

@router.post("/{assignment_id}/groups", response_model=GroupResponse)
async def create_group(
    assignment_id: int,
    data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """为作业创建小组。"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    group = ProjectGroup(
        assignment_id=assignment_id,
        name=data.name,
        members_json=data.members_json,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{assignment_id}/groups", response_model=List[GroupResponse])
async def list_groups(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取作业的所有小组。"""
    groups = db.query(ProjectGroup).filter(ProjectGroup.assignment_id == assignment_id).all()
    return groups


# === 辅助函数 ===

def _cp(content: str, evidence_type: str) -> Dict[str, Any]:
    return {"content": content, "evidence_type": evidence_type}


def _get_template_phases(data: AssignmentCreate) -> List[Dict[str, Any]]:
    """根据作业类型与子类型返回模板阶段（来源：产品设计文档 5.2.3）。"""
    if data.assignment_type == AssignmentType.PRACTICAL:
        phases = [
            {"name": "任务理解", "order": 1, "steps": [
                {"name": "阅读任务单", "description": "明确实践主题、目标、具体要求", "checkpoints": [_cp("确认已阅读任务单", "confirm")]},
                {"name": "了解评价标准", "description": "知道作业如何被评价", "checkpoints": [_cp("能复述评价要点", "text")]},
            ]},
            {"name": "实践准备", "order": 2, "steps": [
                {"name": "制定计划", "description": "确定时间、地点、所需材料", "checkpoints": [_cp("有书面准备清单", "document")]},
                {"name": "分工协作", "description": "明确小组成员分工", "checkpoints": [_cp("有分工表", "document")]},
            ]},
            {"name": "实践体验", "order": 3, "steps": [
                {"name": "参与实践活动", "description": "按计划完成参观/观察/体验", "checkpoints": [_cp("时间线记录", "text")]},
                {"name": "过程记录", "description": "用文字、照片、视频等记录过程", "checkpoints": [_cp("照片/视频/笔记", "image")]},
            ]},
            {"name": "跨学科解释", "order": 4, "steps": [
                {"name": "知识联结", "description": "用多学科知识解释观察到的现象", "checkpoints": [_cp("跨学科概念对应表", "document")]},
                {"name": "深度思考", "description": "分析现象背后的原因和规律", "checkpoints": [_cp("分析文字（至少200字）", "text")]},
            ]},
            {"name": "成果展示", "order": 5, "steps": [
                {"name": "制作成果", "description": "制作海报/PPT/视频/表演稿", "checkpoints": [_cp("成果材料", "document")]},
                {"name": "汇报展示", "description": "向全班或小组汇报", "checkpoints": [_cp("汇报记录", "document")]},
            ]},
            {"name": "反思总结", "order": 6, "steps": [
                {"name": "个人反思", "description": "写出收获、困难、改进点", "checkpoints": [_cp("反思文字（至少150字）", "text")]},
                {"name": "互评", "description": "对同学的成果给出评价", "checkpoints": [_cp("互评表", "document")]},
            ]},
        ]
        return _apply_depth_scaffold(phases, data.inquiry_depth)

    if data.assignment_type == AssignmentType.INQUIRY:
        subtype = data.inquiry_subtype or InquirySubType.LITERATURE
        if subtype == InquirySubType.SURVEY:
            phases = [
                {"name": "确定问题", "order": 1, "steps": [
                    {"name": "明确调查目的", "description": "确定要调查什么、为什么调查", "checkpoints": [_cp("调查目的描述", "text")]},
                    {"name": "确定调查对象", "description": "明确调查谁、多少人", "checkpoints": [_cp("调查对象说明", "text")]},
                ]},
                {"name": "设计方案", "order": 2, "steps": [
                    {"name": "选择调查方法", "description": "问卷/访谈/观察", "checkpoints": [_cp("方法选择说明", "text")]},
                    {"name": "设计调查工具", "description": "设计问卷/访谈提纲", "checkpoints": [_cp("调查工具（问卷/提纲）", "document")]},
                ]},
                {"name": "实施调查", "order": 3, "steps": [
                    {"name": "开展调查", "description": "按计划实施调查", "checkpoints": [_cp("调查过程记录", "document")]},
                    {"name": "收集数据", "description": "整理收回的数据", "checkpoints": [_cp("原始数据", "document")]},
                ]},
                {"name": "数据分析", "order": 4, "steps": [
                    {"name": "数据整理", "description": "清洗、分类、统计数据", "checkpoints": [_cp("数据统计表", "document")]},
                    {"name": "数据可视化", "description": "用图表呈现数据", "checkpoints": [_cp("图表（至少2个）", "image")]},
                ]},
                {"name": "得出结论", "order": 5, "steps": [
                    {"name": "分析发现", "description": "基于数据分析得出结论", "checkpoints": [_cp("分析结论", "text")]},
                    {"name": "提出建议", "description": "基于结论提出建议或对策", "checkpoints": [_cp("建议部分", "text")]},
                ]},
                {"name": "撰写报告", "order": 6, "steps": [
                    {"name": "撰写调查报告", "description": "按规范格式撰写", "checkpoints": [_cp("调查报告", "document")]},
                ]},
            ]
        elif subtype == InquirySubType.EXPERIMENT:
            phases = [
                {"name": "提出问题与假设", "order": 1, "steps": [
                    {"name": "观察现象", "description": "观察并描述要研究的现象", "checkpoints": [_cp("现象描述", "text")]},
                    {"name": "提出问题", "description": "基于观察提出探究问题", "checkpoints": [_cp("探究问题", "text")]},
                    {"name": "作出假设", "description": "对问题给出可验证的假设", "checkpoints": [_cp("假设陈述", "text")]},
                ]},
                {"name": "设计实验", "order": 2, "steps": [
                    {"name": "确定变量", "description": "明确自变量、因变量、控制变量", "checkpoints": [_cp("变量确认表", "document")]},
                    {"name": "设计步骤", "description": "写出实验操作步骤", "checkpoints": [_cp("实验方案", "document")]},
                    {"name": "准备材料", "description": "列出所需器材和材料", "checkpoints": [_cp("材料清单", "document")]},
                ]},
                {"name": "实施实验", "order": 3, "steps": [
                    {"name": "按步骤操作", "description": "规范操作，注意安全", "checkpoints": [_cp("操作过程照片/视频", "image")]},
                    {"name": "记录数据", "description": "如实记录实验数据", "checkpoints": [_cp("原始数据记录表", "document")]},
                    {"name": "重复实验", "description": "至少重复2次以确保可靠性", "checkpoints": [_cp("多次实验数据", "document")]},
                ]},
                {"name": "分析与结论", "order": 4, "steps": [
                    {"name": "数据处理", "description": "计算平均值、绘制图表", "checkpoints": [_cp("数据分析图表", "image")]},
                    {"name": "得出结论", "description": "判断假设是否成立", "checkpoints": [_cp("结论陈述", "text")]},
                ]},
                {"name": "交流与反思", "order": 5, "steps": [
                    {"name": "撰写报告", "description": "按实验报告格式撰写", "checkpoints": [_cp("实验报告", "document")]},
                    {"name": "反思改进", "description": "分析误差来源和改进方向", "checkpoints": [_cp("反思部分", "text")]},
                ]},
            ]
        else:
            phases = [
                {"name": "确定问题", "order": 1, "steps": [
                    {"name": "提出探究问题", "description": "基于主题确定要探究的核心问题", "checkpoints": [_cp("探究问题描述", "text")]},
                    {"name": "形成假设", "description": "对问题的初步回答或猜想", "checkpoints": [_cp("假设陈述", "text")]},
                ]},
                {"name": "检索资料", "order": 2, "steps": [
                    {"name": "确定检索策略", "description": "明确关键词、资料来源类型", "checkpoints": [_cp("检索计划", "document")]},
                    {"name": "收集资料", "description": "从课本、图书、网络等收集资料", "checkpoints": [_cp("资料清单（含来源）", "document")]},
                ]},
                {"name": "阅读分析", "order": 3, "steps": [
                    {"name": "精读资料", "description": "提取关键信息，做标注笔记", "checkpoints": [_cp("阅读笔记", "document")]},
                    {"name": "信息整合", "description": "整理归纳不同来源的信息", "checkpoints": [_cp("信息整合表/思维导图", "document")]},
                ]},
                {"name": "形成结论", "order": 4, "steps": [
                    {"name": "论证分析", "description": "基于证据论证假设是否成立", "checkpoints": [_cp("论证过程记录", "text")]},
                    {"name": "得出结论", "description": "形成对探究问题的回答", "checkpoints": [_cp("结论陈述", "text")]},
                ]},
                {"name": "撰写报告", "order": 5, "steps": [
                    {"name": "撰写探究报告", "description": "按规范格式撰写报告", "checkpoints": [_cp("探究报告", "document")]},
                    {"name": "反思局限", "description": "分析探究的局限性和改进方向", "checkpoints": [_cp("反思部分", "text")]},
                ]},
            ]
        return _apply_depth_scaffold(phases, data.inquiry_depth)

    phases = [
        {"name": "立项启动", "order": 1, "steps": [
            {"name": "理解真实问题", "description": "深入理解要解决的问题及其背景", "checkpoints": [_cp("问题分析文档", "document")]},
            {"name": "明确项目目标", "description": "确定成果形式、受众、成功标准", "checkpoints": [_cp("项目立项卡", "document")]},
            {"name": "组建团队", "description": "确定成员、角色分工", "checkpoints": [_cp("团队分工表", "document")]},
        ]},
        {"name": "规划设计", "order": 2, "steps": [
            {"name": "调研分析", "description": "收集相关信息，分析已有方案", "checkpoints": [_cp("调研报告", "document")]},
            {"name": "制定计划", "description": "确定时间节点、里程碑", "checkpoints": [_cp("项目计划表（甘特图）", "document")]},
            {"name": "方案设计", "description": "设计解决方案", "checkpoints": [_cp("设计方案", "document")]},
        ]},
        {"name": "第一轮迭代", "order": 3, "steps": [
            {"name": "实施制作", "description": "按设计方案制作初版成果", "checkpoints": [_cp("初版成果（原型）", "image")]},
            {"name": "测试验证", "description": "测试初版成果是否达成目标", "checkpoints": [_cp("测试记录", "document")]},
            {"name": "收集反馈", "description": "向同学、老师或用户收集反馈", "checkpoints": [_cp("反馈汇总", "document")]},
        ]},
        {"name": "第二轮迭代", "order": 4, "steps": [
            {"name": "分析问题", "description": "基于反馈分析需要改进的问题", "checkpoints": [_cp("问题清单", "document")]},
            {"name": "改进优化", "description": "针对问题进行改进", "checkpoints": [_cp("改进记录+终版成果", "document")]},
        ]},
        {"name": "展示汇报", "order": 5, "steps": [
            {"name": "准备汇报材料", "description": "制作PPT/海报/视频等", "checkpoints": [_cp("汇报材料", "document")]},
            {"name": "进行展示", "description": "向全班/评审进行汇报", "checkpoints": [_cp("展示照片/视频", "image")]},
            {"name": "答辩交流", "description": "回答提问，交流心得", "checkpoints": [_cp("答辩记录", "document")]},
        ]},
        {"name": "复盘总结", "order": 6, "steps": [
            {"name": "团队复盘", "description": "回顾过程，分析成功与不足", "checkpoints": [_cp("复盘报告", "document")]},
            {"name": "个人反思", "description": "每位成员写个人反思", "checkpoints": [_cp("个人反思文字", "text")]},
            {"name": "归档存档", "description": "整理所有过程材料", "checkpoints": [_cp("项目档案袋", "document")]},
        ]},
    ]
    return _apply_depth_scaffold(phases, data.inquiry_depth)


def _apply_depth_scaffold(
    phases: List[Dict[str, Any]],
    depth: InquiryDepth,
) -> List[Dict[str, Any]]:
    if depth == InquiryDepth.BASIC:
        suffix = "提示：可参考示例或模板，按步骤完成。"
    elif depth == InquiryDepth.DEEP:
        suffix = "提示：说明你的选择依据，体现独立思考。"
    else:
        suffix = "提示：注意记录来源与过程。"

    for phase in phases:
        for step in phase.get("steps", []):
            description = step.get("description", "")
            if suffix and suffix not in description:
                step["description"] = f"{description} {suffix}".strip()
    return phases


def _summarize_text(text: str, max_length: int = 360) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    return cleaned[:max_length] + ("..." if len(cleaned) > max_length else "")


def _resolve_subject_names(subject_ids: List[int]) -> List[str]:
    if not subject_ids:
        return []
    with SessionLocal() as db:
        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    id_to_name = {subject.id: subject.name for subject in subjects}
    return [id_to_name.get(subject_id, f"id={subject_id}") for subject_id in subject_ids]


def _build_rag_context(data: AssignmentCreate, subject_ids: List[int]) -> str:
    query = " ".join(
        [part for part in [data.title, data.topic, data.description or ""] if part]
    ).strip()
    if not query:
        return ""
    inventory = InventoryService(get_settings())
    chunks = inventory.query_chunks(query, subject_ids=subject_ids, limit=10)
    if not chunks:
        return ""
    lines: List[str] = []
    for chunk in chunks[:6]:
        snippet = _summarize_text(chunk.get("text", ""))
        meta_parts: List[str] = []
        if chunk.get("subject_name"):
            meta_parts.append(f"subject={chunk['subject_name']}")
        elif chunk.get("subject_id") is not None:
            meta_parts.append(f"subject_id={chunk['subject_id']}")
        if chunk.get("page") is not None:
            meta_parts.append(f"page={chunk['page']}")
        meta = " ".join(meta_parts)
        meta = f" {meta}" if meta else ""
        lines.append(f"[chunk_id={chunk.get('id','')}{meta}] {snippet}")
    return "\n".join(lines)


def _default_objectives(data: AssignmentCreate) -> Dict[str, str]:
    if data.assignment_type == AssignmentType.PRACTICAL:
        return {
            "knowledge": f"理解与{data.topic}相关的核心概念与实践知识。",
            "process": "通过实践体验、过程记录与成果表达完成任务。",
            "emotion": "培养参与意识、责任感与服务社会的态度。",
        }
    if data.assignment_type == AssignmentType.PROJECT:
        return {
            "knowledge": f"掌握与{data.topic}相关的跨学科知识与应用方法。",
            "process": "经历项目规划、协作实施与迭代改进的完整过程。",
            "emotion": "培养合作意识、创新精神与社会责任感。",
        }
    return {
        "knowledge": f"理解与{data.topic}相关的核心概念与学科知识。",
        "process": "通过资料检索、调查分析与合作探究完成任务。",
        "emotion": "培养科学探究精神与协作意识。",
    }


def _default_rubric(assignment_type: AssignmentType) -> Dict[str, Any]:
    if assignment_type == AssignmentType.PRACTICAL:
        return {
            "dimensions": [
                {"name": "实践准备", "weight": 10, "description": "计划完整性与材料准备情况"},
                {"name": "实践参与", "weight": 25, "description": "任务完成度与参与积极性"},
                {"name": "过程记录", "weight": 15, "description": "记录的完整性与真实性"},
                {"name": "跨学科运用", "weight": 20, "description": "多学科知识应用与解释能力"},
                {"name": "成果表达", "weight": 20, "description": "成果质量与表达清晰度"},
                {"name": "反思能力", "weight": 10, "description": "反思深度与改进意识"},
            ]
        }
    if assignment_type == AssignmentType.PROJECT:
        return {
            "dimensions": [
                {"name": "问题分析", "weight": 10, "description": "对真实问题的理解深度"},
                {"name": "规划协作", "weight": 15, "description": "计划合理性与团队协作"},
                {"name": "迭代改进", "weight": 20, "description": "改进次数与优化质量"},
                {"name": "成果质量", "weight": 25, "description": "成果完成度与创新性"},
                {"name": "展示汇报", "weight": 15, "description": "表达清晰度与答辩表现"},
                {"name": "复盘反思", "weight": 15, "description": "复盘深度与个人成长"},
            ]
        }
    return {
        "dimensions": [
            {"name": "问题意识", "weight": 15, "description": "问题价值性与可探究性"},
            {"name": "方案设计", "weight": 20, "description": "方法选择与步骤可操作性"},
            {"name": "探究过程", "weight": 25, "description": "数据真实性与过程规范性"},
            {"name": "结论质量", "weight": 25, "description": "论证逻辑性与结论可靠性"},
            {"name": "反思能力", "weight": 15, "description": "反思深度与改进思路"},
        ]
    }


def _generate_ai_content(data: AssignmentCreate) -> tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    settings = get_settings()
    client = DeepSeekJSONClient(settings)
    _log_ai_debug("generate_called")
    template_phases = _get_template_phases(data)
    default_objectives = _default_objectives(data)
    default_rubric = _default_rubric(data.assignment_type)

    if not client.is_available:
        return default_objectives, template_phases, default_rubric

    type_map = {
        AssignmentType.PRACTICAL: "实践性作业",
        AssignmentType.INQUIRY: "探究性作业",
        AssignmentType.PROJECT: "项目式作业",
    }
    stage_map = {
        SchoolStage.PRIMARY: "小学",
        SchoolStage.MIDDLE: "初中",
    }
    depth_map = {
        InquiryDepth.BASIC: "基础",
        InquiryDepth.INTERMEDIATE: "中等",
        InquiryDepth.DEEP: "深度",
    }
    submission_map = {
        SubmissionMode.PHASED: "过程性提交",
        SubmissionMode.ONCE: "一次性提交",
        SubmissionMode.MIXED: "混合提交",
    }

    subtype_label = "无"
    if data.assignment_type == AssignmentType.PRACTICAL and data.practical_subtype:
        subtype_label = {
            PracticalSubType.VISIT: "参观考察",
            PracticalSubType.SIMULATION: "模拟表演",
            PracticalSubType.OBSERVATION: "观察体验",
        }.get(data.practical_subtype, data.practical_subtype.value)
    if data.assignment_type == AssignmentType.INQUIRY and data.inquiry_subtype:
        subtype_label = {
            InquirySubType.LITERATURE: "文献探究",
            InquirySubType.SURVEY: "调查探究",
            InquirySubType.EXPERIMENT: "实验探究",
        }.get(data.inquiry_subtype, data.inquiry_subtype.value)

    subject_ids = [data.main_subject_id] + [
        subject_id for subject_id in (data.related_subject_ids or [])
        if subject_id != data.main_subject_id
    ]
    subject_labels = _resolve_subject_names(subject_ids)
    main_subject_label = subject_labels[0] if subject_labels else f"id={data.main_subject_id}"
    related_subjects_label = ", ".join(subject_labels[1:]) if len(subject_labels) > 1 else "none"
    rag_context = _build_rag_context(data, subject_ids)

    type_guidance = {
        AssignmentType.PRACTICAL: "å¼ºè°ƒçœŸå®žæƒ…å¢ƒä½“éªŒã€è¿‡ç¨‹è®°å½•ã€æˆæžœå±•ç¤ºä¸Žåæ€æ€»ç»“ã€‚",
        AssignmentType.INQUIRY: "å›´ç»•é—®é¢˜-è¯æ®-ç»“è®ºï¼Œå¼ºè°ƒæ£€ç´¢/è°ƒæŸ¥/å®žéªŒä¸Žè®ºè¯è¿‡ç¨‹ã€‚",
        AssignmentType.PROJECT: "çªå‡ºçœŸå®žé—®é¢˜ã€å›¢é˜Ÿåä½œä¸Žè¿­ä»£ä¼˜åŒ–ï¼Œé‡ç‚¹å±•ç¤ºæˆæžœä¸Žå½’çº³åæ€?ã€‚",
    }.get(data.assignment_type, "")

    subtype_guidance = ""
    if data.assignment_type == AssignmentType.PRACTICAL and data.practical_subtype:
        subtype_guidance = {
            PracticalSubType.VISIT: "å‚è§‚è€ƒå¯Ÿï¼šå¼ºè°ƒè§‚å¯Ÿè¦ç‚¹ã€çºªå®žè®°å½•ä¸Žè§„èŒƒè¡¨è¾¾ã€‚",
            PracticalSubType.SIMULATION: "æ¨¡æ‹Ÿè¡¨æ¼”ï¼šå¼ºè°ƒè§’è‰²åˆ†å·¥ã€æƒ…å¢ƒå†çŽ°ä¸Žå¿ƒå¾—è®°å½•ã€‚",
            PracticalSubType.OBSERVATION: "è§‚å¯Ÿä½“éªŒï¼šå¼ºè°ƒè¿žç»­è§‚å¯Ÿã€è®°å½•è¡¨æ ¼ä¸Žå½’çº³åˆ†æžã€‚",
        }.get(data.practical_subtype, "")
    elif data.assignment_type == AssignmentType.INQUIRY and data.inquiry_subtype:
        subtype_guidance = {
            InquirySubType.LITERATURE: "æ–‡çŒ®æŽ¢ç©¶ï¼šå¼ºè°ƒæ–‡çŒ®æ£€ç´¢ã€é˜…è¯»æ‰¹æ³¨ã€è§‚ç‚¹æ•´åˆä¸Žå¼•ç”¨è§„èŒƒã€‚",
            InquirySubType.SURVEY: "è°ƒæŸ¥æŽ¢ç©¶ï¼šå¼ºè°ƒé—®å·/è®¿è°ˆè®¾è®¡ã€æ ·æœ¬è¯´æ˜Žã€ç»Ÿè®¡åˆ†æžã€‚",
            InquirySubType.EXPERIMENT: "å®žéªŒæŽ¢ç©¶ï¼šå¼ºè°ƒå˜é‡æŽ§åˆ¶ã€æ­¥éª¤è§„èŒƒã€é‡å¤éªŒè¯ä¸Žè¯¯å·®åˆ†æžã€‚",
        }.get(data.inquiry_subtype, "")

    depth_guidance = {
        InquiryDepth.BASIC: "基础：高度脚手架，提供明确指令、示例与模板，检查点具体可核对。",
        InquiryDepth.INTERMEDIATE: "中等：给出步骤框架与关键提示，检查点指向性强但留空间。",
        InquiryDepth.DEEP: "深度：开放引导，仅给阶段目标和核心问题，检查点强调质量。",
    }.get(data.inquiry_depth, "中等：给出步骤框架与关键提示。")

    system_prompt = (
        "????????????????K12????????"
        "???????????????JSON????objectives, phases, rubric?"
        "??????????objectives(knowledge/process/emotion)?"
        "phases(name/order/steps)?steps(name/description/checkpoints)?"
        "checkpoints(content/evidence_type)?"
        "???????????/??/??/?????????"
        "????????description?????1-2?checkpoints?"
        "checkpoints????????/???????description?"
        "????title/content/step/checkpoint??????"
    )

    template_json = json.dumps(template_phases, ensure_ascii=False, indent=2)

    user_prompt = (
        "??????????????????????????\n"
        f"- ??: {data.title}\n"
        f"- ??: {data.topic}\n"
        f"- ??: {data.description or '?'}\n"
        f"- ??: {stage_map.get(data.school_stage, data.school_stage)}\n"
        f"- ??: {data.grade}\n"
        f"- ????: {type_map.get(data.assignment_type, data.assignment_type)}\n"
        f"- ???: {subtype_label}\n"
        f"- Main subject: {main_subject_label}\n"
        f"- Related subjects: {related_subjects_label}\n"
        f"- ?????: {type_guidance or '?'}\n"
        f"- ??????: {subtype_guidance or '?'}\n"
        f"- ????: {depth_map.get(data.inquiry_depth, data.inquiry_depth)}\n"
        f"- ????: {submission_map.get(data.submission_mode, data.submission_mode)}\n"
        f"- ??: {data.duration_weeks} ?\n\n"
        f"????: {depth_guidance}\n\n"
        "??JSON???\n"
        "1) objectives ?? knowledge/process/emotion ?????????\n"
        "2) phases ?????????name/order/steps????????????\n"
        "3) ?? step ?????name???? description ? checkpoints?\n"
        "4) checkpoints ????1-2???????content ? evidence_type?\n"
        "5) checkpoints ??? description ???????????????\n"
        "6) evidence_type ???text/document/image/video/confirm/link?\n"
        "7) rubric ??5-6??weight??????=100???????\n\n"
        "???????????\n"
        "- description: \"?????????????\"\n"
        "- checkpoints: [\"?????????????\"]\n"
        "?????\n"
        "- description: \"?????????????\"\n"
        "- checkpoints: [\"?????200????\",\"??????\"]\n\n"
        "???????????description/checkpoints???? name/order/steps??\n"
        f"{template_json}\n"
    )

    if rag_context:
        user_prompt += f"\nSubject-specific context (reference only):\n{rag_context}\n"

    try:
        raw_payload = client.predict_json(system_prompt, user_prompt)
        normalized = _normalize_ai_assignment_output(raw_payload)
        objectives = normalized.get("objectives") or default_objectives
        ai_phases = normalized.get("phases") or []
        phases = _merge_phases(copy.deepcopy(template_phases), ai_phases)
        rubric = normalized.get("rubric") or {}
        if not rubric.get("dimensions"):
            rubric = default_rubric
        return objectives, phases, rubric
    except Exception as exc:
        _log_ai_generation_error(exc)
        return default_objectives, template_phases, default_rubric


_ALLOWED_EVIDENCE_TYPES = {"text", "document", "image", "video", "confirm", "link"}


def _normalize_text_for_compare(text: str) -> str:
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"[\\s\\W_]+", "", text, flags=re.UNICODE)


def _clean_checkpoints(description: str, checkpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not checkpoints:
        return []
    norm_desc = _normalize_text_for_compare(description)
    seen: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    for cp in checkpoints:
        content = (cp.get("content") or "").strip()
        if not content:
            continue
        norm_content = _normalize_text_for_compare(content)
        if not norm_content:
            continue
        if norm_desc and (norm_content == norm_desc or norm_desc in norm_content or norm_content in norm_desc):
            continue
        if norm_content in seen:
            continue
        seen.add(norm_content)
        cleaned.append(cp)
    return cleaned


def _infer_evidence_type(text: str) -> str:
    if not text:
        return "text"
    if not isinstance(text, str):
        text = str(text)
    lowered = text.lower()
    if "http" in lowered or "www." in lowered or "链接" in text or "网址" in text:
        return "link"
    if any(keyword in text for keyword in ("视频", "录像", "录屏", "音频", "录音")):
        return "video"
    if any(keyword in text for keyword in ("图片", "照片", "图表", "截图", "海报", "插图", "流程图", "折线图", "柱状图")):
        return "image"
    if any(keyword in text for keyword in ("确认", "勾选", "完成", "已读", "签字")):
        return "confirm"
    if any(keyword in text for keyword in ("报告", "文档", "表格", "清单", "记录", "方案", "计划", "汇报", "笔记", "问卷", "档案", "日志", "摘要", "论文")):
        return "document"
    if any(keyword in lowered for keyword in ("ppt", "pdf", "doc", "docx", "xls", "xlsx")):
        return "document"
    return "text"


def _merge_phases(
    template_phases: List[Dict[str, Any]],
    ai_phases: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(template_phases, list):
        return template_phases
    if not ai_phases:
        return template_phases

    ai_phase_list = [phase for phase in ai_phases if isinstance(phase, dict)]
    if not ai_phase_list:
        return template_phases

    ai_by_order: Dict[int, Dict[str, Any]] = {}
    ai_by_name: Dict[str, Dict[str, Any]] = {}
    for phase in ai_phase_list:
        order_value = phase.get("order")
        if isinstance(order_value, int):
            ai_by_order[order_value] = phase
        name_value = phase.get("name")
        if isinstance(name_value, str) and name_value:
            ai_by_name[name_value] = phase

    for index, phase in enumerate(template_phases):
        if not isinstance(phase, dict):
            continue
        match = None
        order_value = phase.get("order")
        if isinstance(order_value, int) and order_value in ai_by_order:
            match = ai_by_order[order_value]
        else:
            name_value = phase.get("name")
            if isinstance(name_value, str) and name_value in ai_by_name:
                match = ai_by_name[name_value]
            elif index < len(ai_phase_list):
                match = ai_phase_list[index]
        if not match:
            continue

        phase_title = match.get("title")
        if phase_title:
            phase["title"] = phase_title

        template_steps = phase.get("steps") or []
        ai_steps = match.get("steps") or []
        if isinstance(ai_steps, dict):
            ai_steps = [ai_steps]
        ai_steps = [step for step in ai_steps if isinstance(step, dict)]
        ai_steps_by_name = {step.get("name"): step for step in ai_steps if step.get("name")}

        for step_index, step in enumerate(template_steps):
            if not isinstance(step, dict):
                continue
            ai_step = None
            step_name = step.get("name")
            if step_name and step_name in ai_steps_by_name:
                ai_step = ai_steps_by_name[step_name]
            elif step_index < len(ai_steps):
                ai_step = ai_steps[step_index]
            if not ai_step:
                continue

            description = ai_step.get("description")
            if description:
                step["description"] = description

            content = ai_step.get("content")
            if content:
                step["content"] = content

            ai_checkpoints = ai_step.get("checkpoints") or []
            if isinstance(ai_checkpoints, dict):
                ai_checkpoints = [ai_checkpoints]
            normalized_checkpoints: List[Dict[str, Any]] = []
            if isinstance(ai_checkpoints, list):
                for cp in ai_checkpoints:
                    if isinstance(cp, str):
                        content = cp
                        evidence_type = _infer_evidence_type(content or description)
                    elif isinstance(cp, dict):
                        content = cp.get("content") or cp.get("text") or cp.get("description") or ""
                        evidence_type = cp.get("evidence_type")
                        if evidence_type not in _ALLOWED_EVIDENCE_TYPES:
                            evidence_type = _infer_evidence_type(content or description)
                    else:
                        content = str(cp)
                        evidence_type = _infer_evidence_type(content or description)
                    normalized_checkpoints.append({"content": content, "evidence_type": evidence_type})
            if normalized_checkpoints:
                step["checkpoints"] = _clean_checkpoints(description or "", normalized_checkpoints)

        phase["steps"] = template_steps

    return template_phases


def _normalize_ai_assignment_output(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    objectives = payload.get("objectives") or {}
    if isinstance(objectives, list):
        objectives = {
            "knowledge": objectives[0] if len(objectives) > 0 else "",
            "process": objectives[1] if len(objectives) > 1 else "",
            "emotion": objectives[2] if len(objectives) > 2 else "",
        }
    elif isinstance(objectives, str):
        objectives = {"knowledge": objectives, "process": "", "emotion": ""}
    if not isinstance(objectives, dict):
        objectives = {}
    for key in ("knowledge", "process", "emotion"):
        objectives.setdefault(key, "")
    payload["objectives"] = objectives

    phases = payload.get("phases") or payload.get("phase") or []
    if isinstance(phases, dict):
        phases = [phases]
    if isinstance(phases, str):
        phases = [{"title": phases}]
    normalized_phases: List[Dict[str, Any]] = []
    for idx, phase in enumerate(phases, start=1):
        if isinstance(phase, str):
            phase = {"title": phase}
        if not isinstance(phase, dict):
            continue
        order_value = phase.get("order")
        try:
            order_value = int(order_value)
        except Exception:
            order_value = idx
        phase_title = phase.get("title")
        phase_name = phase.get("name") or phase_title or phase.get("phase") or f"阶段{idx}"
        steps = phase.get("steps") or phase.get("step") or phase.get("items") or []
        if isinstance(steps, dict):
            steps = [steps]
        if isinstance(steps, str):
            steps = [{"content": steps}]
        normalized_steps: List[Dict[str, Any]] = []
        for step in steps if isinstance(steps, list) else []:
            if isinstance(step, str):
                step = {"content": step}
            if not isinstance(step, dict):
                continue
            raw_content = step.get("content")
            description = step.get("description") or raw_content or step.get("detail") or ""
            step_name = step.get("name") or step.get("title") or step.get("label") or ""
            checkpoints = step.get("checkpoints")
            if checkpoints is None and "checkpoint" in step:
                checkpoints = step.get("checkpoint")
            if checkpoints is None and "outputs" in step:
                checkpoints = step.get("outputs")
            if isinstance(checkpoints, dict):
                checkpoints = [checkpoints]
            if isinstance(checkpoints, str):
                checkpoints = [checkpoints]
            normalized_checkpoints: List[Dict[str, Any]] = []
            if isinstance(checkpoints, list):
                for cp in checkpoints:
                    if isinstance(cp, str):
                        content = cp
                        evidence_type = _infer_evidence_type(content or description)
                    elif isinstance(cp, dict):
                        content = cp.get("content") or cp.get("text") or cp.get("description") or ""
                        evidence_type = cp.get("evidence_type")
                        if evidence_type not in _ALLOWED_EVIDENCE_TYPES:
                            evidence_type = _infer_evidence_type(content or description)
                    else:
                        content = str(cp)
                        evidence_type = _infer_evidence_type(content or description)
                    normalized_checkpoints.append({"content": content, "evidence_type": evidence_type})
            if not step_name:
                if description:
                    step_name = description[:12]
                elif normalized_checkpoints:
                    step_name = normalized_checkpoints[0]["content"][:12]
                else:
                    step_name = "步骤"
            if not description and normalized_checkpoints:
                description = normalized_checkpoints[0]["content"]
            normalized_step = {
                "name": step_name,
                "description": description,
                "checkpoints": normalized_checkpoints,
            }
            if raw_content:
                normalized_step["content"] = raw_content
            normalized_steps.append(normalized_step)
        normalized_phase = {
            "name": phase_name,
            "order": order_value,
            "steps": normalized_steps,
        }
        if phase_title:
            normalized_phase["title"] = phase_title
        normalized_phases.append(normalized_phase)
    payload["phases"] = normalized_phases

    rubric = payload.get("rubric") or {}
    if isinstance(rubric, list):
        rubric = {"dimensions": rubric}
    if not isinstance(rubric, dict):
        rubric = {}
    dimensions = rubric.get("dimensions") or rubric.get("criteria") or []
    if isinstance(dimensions, dict):
        dimensions = [
            {"name": name, "weight": weight if isinstance(weight, int) else 20, "description": str(weight)}
            for name, weight in dimensions.items()
        ]
    normalized_dims: List[Dict[str, Any]] = []
    for dim in dimensions if isinstance(dimensions, list) else []:
        if isinstance(dim, str):
            normalized_dims.append({"name": dim, "weight": 20, "description": ""})
        elif isinstance(dim, dict):
            name = dim.get("name") or dim.get("criterion") or dim.get("dimension") or "维度"
            weight = dim.get("weight")
            try:
                weight = int(weight)
            except Exception:
                weight = 20
            description = dim.get("description") or dim.get("desc") or ""
            normalized_dims.append({"name": name, "weight": weight, "description": description})
    payload["rubric"] = {"dimensions": normalized_dims}
    return payload


def _log_ai_generation_error(error: Exception, payload: Dict[str, Any] | None = None) -> None:
    try:
        with open("storage/ai_debug.log", "a", encoding="utf-8") as handle:
            handle.write(f"[assignments] {type(error).__name__}: {error}\n---\n")
            if payload is not None:
                handle.write(f"{payload}\n---\n")
    except Exception:
        pass


def _log_ai_debug(message: str) -> None:
    try:
        with open("storage/ai_debug.log", "a", encoding="utf-8") as handle:
            handle.write(f"[debug] {message}\n---\n")
    except Exception:
        pass


def _ensure_ai_defaults(
    data: AssignmentCreate,
    objectives: Dict[str, Any],
    phases: List[Dict[str, Any]],
    rubric: Dict[str, Any],
) -> tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    if not objectives or not objectives.get("knowledge"):
        objectives = _default_objectives(data)
    if not phases:
        phases = _get_template_phases(data)
    if not rubric or not rubric.get("dimensions"):
        rubric = _default_rubric(data.assignment_type)
    return objectives, phases, rubric


def _is_empty_json(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list)):
        return not value
    if isinstance(value, str):
        return value.strip() in ("{}", "[]", "")
    return False
