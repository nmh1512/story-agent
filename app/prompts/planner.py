"""Prompt template for the Planner agent."""

import json
from app.schemas.planner import PlannerInput

SYSTEM = """
You are the Lead Story Architect. Your goal is to ensure a masterpiece-level narrative progression without repetition.
Produce STRICT JSON only. All narrative content MUST be in VIETNAMESE.
""".strip()

def build_planner_prompt(inp: PlannerInput) -> str:
    state_text = json.dumps(inp.current_story_state or {}, indent=2)
    hooks_text = json.dumps(inp.open_hooks, indent=2)
    summaries_text = json.dumps(inp.recent_chapter_summaries, indent=2)
    world_bible_text = json.dumps(inp.world_bible, indent=2)

    # --- PHASE 1: STORY GENESIS ---
    if inp.planner_mode == "story_genesis":
        return f"""
You are creating a NEW story. Focus on the high-level Act Structure.

## MANDATORY RULES:
1. Generate Title, Genre, Premise, and a deep Backstory.
2. Generate 3 ACT SUMMARIES (Hồi 1, Hồi 2, Hồi 3). 
   - Act 1 (Setup): The inciting incident.
   - Act 2 (Conflict): The main struggles and major twists.
   - Act 3 (Climax): The final resolution.
3. ALL narrative content MUST be in VIETNAMESE.

## JSON Schema:
{{
  "reasoning": "Tôi sẽ xây dựng cốt truyện thuộc thể loại [Thể loại], với điểm nhấn khác biệt là...",
  "title": "...",
  "genre": "...",
  "premise": "...",
  "backstory": "...",
  "act_summaries": [
     {{ "title": "Hồi 1: ...", "summary": "Tóm tắt..." }},
     {{ "title": "Hồi 2: ...", "summary": "Tóm tắt..." }},
     {{ "title": "Hồi 3: ...", "summary": "Tóm tắt..." }}
  ],
  "initial_characters": [{{ "code": "CHAR_1", "name": "...", "role": "...", "description": "..." }}],
  "world_bible": {{ "rules": [], "locations": [] }}
}}
""".strip()

    # --- PHASE 2: SINGLE CHAPTER ROADMAP (Iterative Planning) ---
    if inp.planner_mode == "single_chapter_roadmap":
        act_no = inp.current_story_state.get("target_act_no", 1)
        act_summary = inp.current_story_state.get("target_act_summary", "")
        pacing_instruction = inp.current_story_state.get("pacing_instruction", "")
        previous_chapters = inp.current_story_state.get("previous_chapters_roadmap", "None")
        genre = str(inp.genre or "hành động")

        return f"""
You are planning ONE NEXT CHAPTER (Chapter {inp.target_chapter_no}) for the story "{inp.story_title}" (Genre: {genre}).

## North Star (Act {act_no} Goal): 
{act_summary}

## PACING INSTRUCTION (CRITICAL):
{pacing_instruction}

## History (ALL Previous Chapters):
{previous_chapters}

## TASK:
Based on the History, write the plan for the VERY NEXT CHAPTER.
1. Self-Reflection: First, fill in `recent_events_analysis` to briefly state what just happened in the immediate previous chapter.
2. Contrast Decision: Then, fill in `new_direction_decision` to declare a COMPLETELY DIFFERENT focus for this current chapter (e.g., if previous was action, this must be emotional; if previous was discovery, this must be conflict).
3. DO NOT REPEAT the events, goals, or conflicts from the History. Break the pattern!
4. ALL narrative content in VIETNAMESE.

## JSON Schema:
{{
  "recent_events_analysis": "Chương vừa rồi, nhân vật đã...",
  "new_direction_decision": "Để phá vỡ sự lặp lại, chương này tôi quyết định đổi trọng tâm sang...",
  "theme": "Tên chương ấn tượng",
  "summary": "Tóm tắt: Diễn biến cốt lõi của duy nhất chương tiếp theo."
}}
""".strip()

    # --- PHASE 3: CHAPTER PLANNING (Just-In-Time detailed outline) ---
    return f"""
You are planning the DETAILED SCENE-BY-SCENE outline for Chapter {inp.target_chapter_no} of "{inp.story_title}".

## Context:
- Roadmap Goal for this chapter: {inp.current_story_state.get('roadmap_summary', 'N/A') if inp.current_story_state else 'N/A'}
- History: {summaries_text}
- World Bible: {world_bible_text}
- Open Hooks: {hooks_text}

## RULES:
1. Self-Reflection: Use `recent_events_analysis` to state what just happened, and `new_direction_decision` to confirm how this chapter's scenes will feel different.
2. Focus on VIVID SENSORY DETAILS and HIGH TENSION.
3. Every scene must change the status quo.

## Required JSON Schema:
{{
  "recent_events_analysis": "So sánh với History, tôi thấy...",
  "new_direction_decision": "Để tạo sự mới mẻ, các cảnh trong chương này sẽ...",
  "chapter_no": {inp.target_chapter_no},
  "theme": "...",
  "summary": "...",
  "outline": {{
    "chapter_goal": "...",
    "scene_list": [
      {{ "scene_no": 1, "location": "...", "scene_goal": "...", "conflict": "...", "expected_outcome": "..." }}
    ],
    "ending_hook": "...",
    "tone": "..."
  }},
  "creates_write_task": true
}}
""".strip()
