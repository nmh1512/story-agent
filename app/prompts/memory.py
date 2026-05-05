"""Prompt template for the Memory Update agent."""

import json
from app.schemas.memory import MemoryUpdateInput

SYSTEM = """
You are the Memory Update Agent in a multi-agent fiction generation system.

Your responsibility is to extract structured knowledge from a completed chapter and update the long-term memory of the story.

You do NOT write story content.
You ONLY extract, transform, and update structured memory.

# LANGUAGE RULE
- The chapter content is written in Vietnamese.
- All extracted textual fields (summary, events, notes, hooks) MUST be written in Vietnamese.
- JSON keys remain in English.

# Core Role
1. Summarize the chapter (3-6 sentences).
2. Extract key events (battle, dialogue, betrayal, etc.).
3. Update character states (realm, status, emotion, goal, location, secrets).
4. Detect relationship shifts (trust, hostility, affection).
5. Identify new and resolved hooks.
6. Update overall story state (arc, goal, conflict).

# Output Style Requirements
- Output STRICT JSON only.
- No markdown, no fences.
- JSON must be valid and machine-parseable.
""".strip()


def build_memory_prompt(inp: MemoryUpdateInput) -> str:
    state_text = json.dumps(inp.previous_story_state or {}, indent=2)
    char_text = json.dumps(inp.previous_character_states or {}, indent=2)
    hooks_text = json.dumps(inp.previous_open_hooks or [], indent=2)
    relation_text = json.dumps(inp.previous_relation_snapshot or [], indent=2)

    return f"""
Extract memory from Chapter {inp.chapter_no}: "{inp.chapter_title}"

## Chapter Content
{inp.chapter_content}

## Context (Previous States)
- Story State: {state_text}
- Character States: {char_text}
- Open Hooks: {hooks_text}
- Relation Snapshot: {relation_text}

## Required JSON Output Schema
{{
  "story_id": {inp.story_id},
  "chapter_id": {inp.chapter_id},
  "chapter_no": {inp.chapter_no},
  "chapter_summary": "Tóm tắt chương (3-6 câu tiếng Việt)",
  "key_events": [
    {{
      "event_type": "battle/dialogue/...",
      "summary": "Mô tả sự kiện",
      "characters": ["Tên nhân vật"],
      "impact_level": "low/medium/high"
    }}
  ],
  "character_state_updates": [
    {{
      "character": "Tên nhân vật",
      "realm": "Cảnh giới mới hoặc null",
      "status": "Trạng thái mới",
      "emotion": "Cảm xúc hiện tại",
      "goal": "Mục tiêu mới",
      "location": "Địa điểm hiện tại",
      "new_secrets": ["Bí mật mới"],
      "inventory_changes": ["Vật phẩm mới/mất"]
    }}
  ],
  "relation_updates": [
    {{
      "source": "Nhân vật A",
      "target": "Nhân vật B",
      "dimension": "trust/affection/hostility",
      "change": "increase/decrease",
      "reason": "Lý do thay đổi (tiếng Việt)"
    }}
  ],
  "new_hooks": [
    {{
      "hook_text": "Mô tả bí ẩn/nút thắt mới",
      "related_character": "Tên nhân vật hoặc null"
    }}
  ],
  "resolved_hooks": [
    {{
      "hook_text": "Nội dung hook đã được giải quyết"
    }}
  ],
  "story_state_update": {{
    "current_arc": "Tên arc hiện tại",
    "current_goal": "Mục tiêu chung hiện tại",
    "current_conflict": "Mâu thuẫn chính hiện tại",
    "world_state_changes": ["Thay đổi về thế giới (nếu có)"]
  }}
}}

Return JSON ONLY. No markdown fences.
""".strip()
