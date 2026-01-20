"""作业相关枚举定义 - 作业类型、探究深度、提交模式等。"""

import enum


class AssignmentType(str, enum.Enum):
    """作业类型枚举。
    
    根据产品设计文档 4.2 节，跨学科作业分为三大类型。
    """
    PRACTICAL = "practical"      # 实践性作业
    INQUIRY = "inquiry"          # 探究性作业
    PROJECT = "project"          # 项目式作业


class PracticalSubType(str, enum.Enum):
    """实践性作业子类型。
    
    根据产品设计文档 4.2.1 节定义。
    """
    VISIT = "visit"              # 参观考察型
    SIMULATION = "simulation"    # 模拟表演型
    OBSERVATION = "observation"  # 观察体验型


class InquirySubType(str, enum.Enum):
    """探究性作业子类型。
    
    根据产品设计文档 4.2.2 节定义。
    """
    LITERATURE = "literature"    # 文献探究
    SURVEY = "survey"            # 调查探究
    EXPERIMENT = "experiment"    # 实验探究


class InquiryDepth(str, enum.Enum):
    """探究深度分级。
    
    根据产品设计文档 4.3 节的基础-中等-深度三档分级。
    """
    BASIC = "basic"              # 基础探究：理解与掌握学科核心概念
    INTERMEDIATE = "intermediate" # 中等探究：在情境中运用知识解决问题
    DEEP = "deep"                # 深度探究：综合运用多学科知识


class SubmissionMode(str, enum.Enum):
    """提交模式。
    
    根据产品设计文档 6.1 节定义。
    """
    PHASED = "phased"            # 过程性提交：按阶段分多次提交
    ONCE = "once"                # 一次性提交：完成后一次性提交
    MIXED = "mixed"              # 混合提交：关键节点强制提交


class SubmissionStatus(str, enum.Enum):
    """提交状态。"""
    DRAFT = "draft"              # 草稿
    SUBMITTED = "submitted"      # 已提交
    GRADED = "graded"            # 已评分


class EvaluationType(str, enum.Enum):
    """评价类型。
    
    根据产品设计文档 7.3 节定义。
    """
    TEACHER = "teacher"          # 教师评价
    SELF = "self"                # 学生自评
    PEER = "peer"                # 学生互评


class EvaluationLevel(str, enum.Enum):
    """评价等级。
    
    根据产品设计文档 7.2 节的四级评分制。
    """
    A = "A"  # 超出预期/优秀 90-100
    B = "B"  # 达到预期/良好 75-89
    C = "C"  # 基本达到/合格 60-74
    D = "D"  # 未达到/需改进 0-59


class SchoolStage(str, enum.Enum):
    """学段。"""
    PRIMARY = "primary"          # 小学
    MIDDLE = "middle"            # 初中
