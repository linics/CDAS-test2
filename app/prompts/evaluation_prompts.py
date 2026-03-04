"""Evaluation prompt builders."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationPromptContext:
    assignment_title: str
    assignment_topic: str
    assignment_description: str
    objectives_json: str
    phase_context: str
    submission_text: str
    attachments: str
    checkpoints: str
    rubric_text: str


def build_evaluation_prompt(ctx: EvaluationPromptContext) -> tuple[str, str]:
    system_prompt = (
        "You are a rigorous K12 teacher evaluator. "
        "Use only the provided submission evidence. "
        "Do not fabricate facts. "
        "Return JSON only."
    )

    user_prompt = (
        "Assignment context:\n"
        f"- Title: {ctx.assignment_title}\n"
        f"- Topic: {ctx.assignment_topic}\n"
        f"- Description: {ctx.assignment_description}\n"
        f"- Objectives JSON: {ctx.objectives_json}\n\n"
        f"Current phase tasks:\n{ctx.phase_context}\n\n"
        "Submission evidence:\n"
        f"- text: {ctx.submission_text}\n"
        f"- attachments: {ctx.attachments}\n"
        f"- checkpoints: {ctx.checkpoints}\n\n"
        "Rubric (dimensions with levels):\n"
        f"{ctx.rubric_text}\n\n"
        "Scoring constraints:\n"
        "1) Score each rubric dimension strictly from 1-4.\n"
        "2) dimension_scores keys must exactly match rubric dimension names.\n"
        "3) If evidence is insufficient, lower the score and explain why.\n"
        "4) evidence must include short quotes from submission text or explicit attachment/checkpoint references.\n"
        "5) feedback should have three concise parts: strengths, gaps, next focus.\n"
        "6) action_items should be 2-3 concrete next-step suggestions for the student.\n\n"
        "Return JSON with fields:\n"
        "- suggested_score (1-4, average)\n"
        "- suggested_level (excellent/good/pass/improve)\n"
        "- dimension_scores (object)\n"
        "- feedback (single string)\n"
        "- evidence (list of {source, quote, reason})\n"
        "- action_items (list of strings)\n"
    )

    return system_prompt, user_prompt
