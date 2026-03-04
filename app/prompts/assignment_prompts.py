"""Assignment generation prompt builders."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssignmentPreviewPromptContext:
    title: str
    topic: str
    description: str
    school_stage: str
    grade: int
    assignment_type: str
    subtype: str
    main_subject: str
    related_subjects: str
    reference_document: str
    type_guidance: str
    subtype_guidance: str
    inquiry_depth: str
    submission_mode: str
    duration_weeks: int
    depth_guidance: str
    template_json: str
    rag_context: str


@dataclass(frozen=True)
class LessonPlanPromptContext:
    title: str
    topic: str
    school_stage: str
    grade: int
    assignment_type: str
    inquiry_depth: str
    submission_mode: str
    duration_weeks: int
    main_subject: str
    related_subjects: str
    lesson_plan_excerpt: str
    template_json: str


def build_assignment_preview_prompt(ctx: AssignmentPreviewPromptContext) -> tuple[str, str]:
    system_prompt = (
        "You are an expert K12 assignment designer. "
        "Return exactly one JSON object with keys: objectives, phases, rubric. "
        "objectives must include knowledge/process/emotion. "
        "phases must include name/order/steps. "
        "Use phase titles to express scenario progression and continuity. "
        "Each step must include name/description/checkpoints. "
        "step.description must act as learning scaffold, not task name repetition. "
        "Each checkpoint must include content/evidence_type where evidence_type is one of "
        "text/document/image/video/confirm/link. "
        "Keep checkpoints actionable and not duplicate the step description. "
        "Avoid formulaic repetition across phases and steps."
    )

    user_prompt = (
        "Generate a structured assignment draft from the following teaching context.\n"
        f"- Title: {ctx.title}\n"
        f"- Topic: {ctx.topic}\n"
        f"- Description: {ctx.description or 'none'}\n"
        f"- School stage: {ctx.school_stage}\n"
        f"- Grade: {ctx.grade}\n"
        f"- Assignment type: {ctx.assignment_type}\n"
        f"- Subtype: {ctx.subtype}\n"
        f"- Main subject: {ctx.main_subject}\n"
        f"- Related subjects: {ctx.related_subjects}\n"
        f"- Reference document: {ctx.reference_document or 'none'}\n"
        f"- Type guidance: {ctx.type_guidance or 'none'}\n"
        f"- Subtype guidance: {ctx.subtype_guidance or 'none'}\n"
        f"- Inquiry depth: {ctx.inquiry_depth}\n"
        f"- Submission mode: {ctx.submission_mode}\n"
        f"- Duration weeks: {ctx.duration_weeks}\n"
        f"- Depth guidance: {ctx.depth_guidance}\n\n"
        "Output requirements:\n"
        "1) objectives should be specific and concise.\n"
        "2) phases should remain coherent with increasing progression, and each phase title should show story continuity.\n"
        "3) each step should include 1-2 checkpoints only.\n"
        "4) rubric should have 5-6 dimensions with level descriptions (excellent/good/pass/improve).\n"
        "5) write step descriptions as scaffolding prompts with context, hints, and expected thinking path.\n"
        "6) avoid repeated sentence templates such as identical openings for all steps.\n"
        "7) preserve phase structure compatibility with this template (you may enrich descriptions/checkpoints):\n"
        f"{ctx.template_json}\n"
    )

    if ctx.rag_context:
        user_prompt += f"\nSubject-specific context (reference only):\n{ctx.rag_context}\n"

    return system_prompt, user_prompt


def build_lesson_plan_prompt(ctx: LessonPlanPromptContext) -> tuple[str, str]:
    system_prompt = (
        "You are an expert curriculum-to-assignment converter for K12 teachers. "
        "Read a lesson plan and produce a practical assignment draft. "
        "Return exactly one JSON object with keys: objectives, phases, rubric. "
        "Preserve lesson-plan intent and scenario continuity. "
        "Use realistic classroom language, concise wording, and actionable checkpoints."
    )

    user_prompt = (
        "Task: convert this lesson plan into a student assignment draft.\n"
        "Follow constraints:\n"
        "- objectives includes knowledge/process/emotion\n"
        "- phases includes name/order/steps\n"
        "- each phase should include a scenario title that naturally continues from previous phase\n"
        "- each step includes name/description/checkpoints\n"
        "- step.description should be a learning scaffold sentence with context and hint\n"
        "- each checkpoint includes content/evidence_type (text/document/image/video/confirm/link)\n"
        "- rubric includes 5-6 dimensions with levels excellent/good/pass/improve\n"
        "- keep progression from task understanding to evidence production and reflection\n\n"
        f"Seed profile:\n- title={ctx.title}\n- topic={ctx.topic}\n"
        f"- school_stage={ctx.school_stage}\n- grade={ctx.grade}\n"
        f"- assignment_type={ctx.assignment_type}\n- inquiry_depth={ctx.inquiry_depth}\n"
        f"- submission_mode={ctx.submission_mode}\n- duration_weeks={ctx.duration_weeks}\n"
        f"- main_subject={ctx.main_subject}\n- related_subjects={ctx.related_subjects}\n\n"
        "Lesson plan excerpt:\n"
        f"{ctx.lesson_plan_excerpt}\n\n"
        "Structure template (keep compatible order/shape, enrich content):\n"
        f"{ctx.template_json}\n\n"
        "Quality constraints:\n"
        "- keep each step concise and practical for classroom execution\n"
        "- each step checkpoints count should be 1-2 only\n"
        "- avoid generic placeholders and repeated slogans\n"
    )
    return system_prompt, user_prompt
