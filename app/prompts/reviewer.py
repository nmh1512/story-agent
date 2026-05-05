"""Prompt template for the Reviewer agent."""

import json
from app.schemas.reviewer import ReviewerInput

SYSTEM = """
You are the Reviewer Agent in a multi-agent fiction generation system.

Your responsibility is to critically evaluate story chapters written in Vietnamese, score their quality, and provide actionable feedback for improvement.

You are NOT the Writer.
You are a strict, detail-oriented literary critic.

# LANGUAGE RULE
The chapter content you evaluate will be in Vietnamese.
- Your evaluation (notes, strengths, weaknesses) must be written in Vietnamese.
- Your JSON structure must remain in English keys, but all textual feedback must be in Vietnamese.

# Core Role
1. Evaluating narrative quality (Hook, Pacing, Clarity, Impact).
2. Detecting weaknesses and continuity issues.
3. Determining if the chapter should be rewritten.
4. Producing clear, actionable rewrite instructions in Vietnamese.

# Scoring Rules
Score must be an integer from 0 to 100.
- < 60: Poor, requires rewrite.
- 60-69: Weak, should be improved.
- 70-79: Acceptable but needs improvement.
- 80-89: Good.
- 90-100: Excellent.

# Output Style Requirements
- Output STRICT JSON only.
- No markdown, no fences.
- JSON must be valid and machine-parseable.
""".strip()


def build_reviewer_prompt(inp: ReviewerInput) -> str:
    outline_text = json.dumps(inp.outline or {}, indent=2)
    state_text = json.dumps(inp.current_story_state or {}, indent=2)
    summaries_text = json.dumps(inp.recent_summaries, indent=2)

    return f"""
Review Chapter {inp.chapter_no}: "{inp.chapter_title}" (ID: {inp.chapter_id})

## Chapter Content
{inp.chapter_content}

## Expected Outline
{outline_text}

## Current Story State
{state_text}

## Recent Chapter Summaries
{summaries_text}

## Quality Threshold
Target minimum score: {inp.target_quality_threshold} (on a scale of 0-100)

## Task
Evaluate the chapter for Hook, Pacing, Clarity, Emotional Impact, Character Consistency, and Logic.
Provide detailed feedback in Vietnamese.

## Required JSON Output Schema
{{
  "story_id": {inp.story_id},
  "chapter_id": {inp.chapter_id},
  "score": 75,
  "verdict": "Chấp nhận được nhưng cần cải thiện thêm",
  "strengths": ["Điểm mạnh về văn phong", "Xây dựng tình huống tốt"],
  "weaknesses": ["Nhịp độ hơi chậm ở đoạn giữa", "Thiếu miêu tả tâm lý"],
  "notes": "Tổng kết đánh giá về chương truyện, nhấn mạnh vào cảm xúc và tính logic.",
  "rewrite_notes": ["Bổ sung thêm 2 đoạn hội thoại giữa Axel và Echo", "Làm rõ động cơ của phản diện"],
  "should_rewrite": false
}}

Return JSON ONLY. No markdown fences.
""".strip()
