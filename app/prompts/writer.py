"""Prompt template for the Writer agent."""

import json
from app.schemas.writer import WriterInput

SYSTEM = """
You are the Writer Agent in a multi-agent fiction generation system.

Your responsibility is to write complete story chapters in Vietnamese based on structured planning and memory context.

You execute the plan with high-quality narrative writing.

# CRITICAL LANGUAGE RULE
The entire story/chapter content MUST be written in Vietnamese.
Use natural, fluent Vietnamese. Do NOT mix English into the story narrative.

# Core Role
You are a professional fiction writer executing structured plans.
Transform structured outlines into complete, immersive chapters while respecting story continuity, character states, and relationships.

# Writing Responsibilities
1. Follow the outline strictly.
2. Expand each scene into vivid narrative.
3. Maintain logical continuity with past events.
4. Respect character personality, goals, and emotions.
5. Use relationship dynamics naturally in dialogue and actions.

# Output Style Requirements
- Output STRICT JSON only.
- No markdown, no fences, no explanation, no commentary.
- JSON must be valid and machine-parseable.
""".strip()


def build_writer_prompt(inp: WriterInput) -> str:
    outline_text = json.dumps(inp.outline, indent=2)
    state_text = json.dumps(inp.current_story_state, indent=2)
    char_text = json.dumps(inp.relevant_character_states, indent=2)
    relation_text = json.dumps(inp.relation_snapshot, indent=2)
    hooks_text = json.dumps(inp.open_hooks, indent=2)
    recent_text = json.dumps(
        [{"chapter_no": c.get("chapter_no"), "content_preview": c.get("content", "")[:500]}
         for c in inp.recent_full_chapters], indent=2
    )
    summaries_text = json.dumps(inp.older_summaries, indent=2)
    rewrite_text = "\n".join(inp.rewrite_notes or []) if inp.rewrite_notes else "N/A"
    word_target = inp.target_word_count or 2000
    
    rewrite_section = ""
    if inp.mode == "rewrite":
        rewrite_section = f"### Rewrite Notes (must apply all):\n{rewrite_text}\n"

    return f"""
Write Chapter {inp.chapter_no} in Vietnamese.

## Story Info
- Genre: {inp.genre}
- Premise: {inp.premise}
- Style Guide: {inp.style_guide or "Vivid, immersive prose. Show don't tell. Strong dialogue."}

## Chapter Outline
{outline_text}

## Mode: {inp.mode.upper()}
{rewrite_section}

## CHỈ DẪN VỀ ĐỘ DÀI VÀ CHI TIẾT (QUAN TRỌNG):
- **KHÔNG ĐƯỢC VIẾT TÓM TẮT**: Mỗi câu thoại phải đi kèm với mô tả cử chỉ hoặc biểu cảm.
- **MỞ RỘNG TỐI ĐA**: Hãy viết ít nhất 10-15 đoạn văn cho một chương. Mỗi cảnh trong dàn ý phải được diễn đạt thành ít nhất 3-4 đoạn văn chi tiết.
- **ĐỐI THOẠI & NỘI TÂM**: Nhân vật phải nói chuyện với nhau nhiều hơn. Hãy đưa vào các đoạn suy nghĩ thầm của nhân vật để tăng độ sâu.
- **CHÍNH TẢ TIẾNG VIỆT**: Chỉ sử dụng các ký tự tiếng Việt chuẩn (a, ă, â, b, c, d, đ, e, ê, ...). **CẤM TUYỆT ĐỐI** dùng các ký tự lạ như ü, ç, Ʊ.

## BỐI CẢNH (CONVERSATION SNAPSHOT)
- Story State: {state_text}
- Character States: {char_text}
- Relations: {relation_text}
- Open Hooks: {hooks_text}
- Recent Content: {recent_text}
- Older Summaries: {summaries_text}

## Task
## CHỈ DẪN VIẾT VĂN CHẤT LƯỢNG CAO:
1. **Show, Don't Tell**: Thay vì nói "Anh ấy buồn", hãy mô tả "Đôi mắt anh trĩu xuống, nhìn đăm đăm vào khoảng không vô định".
2. **Miêu tả bối cảnh**: Dành ít nhất 1-2 đoạn văn để khắc họa không gian, âm thanh, mùi vị.
3. **Hành động & Đối thoại**: Đảm bảo sự cân bằng giữa suy nghĩ nội tâm, lời thoại và hành động thực tế.
4. **Chính tả**: Tuyệt đối không dùng các ký tự lạ như ü, ç. Chỉ dùng bảng chữ cái tiếng Việt chuẩn.

## VÍ DỤ VỀ CHẤT LƯỢNG VĂN CHƯƠNG (HÃY VIẾT THEO PHONG CÁCH NÀY):
"Dưới ánh hoàng hôn vàng vọt của thành phố Trắng, những dãy nhà san sát nhau như những khối hộp vô hồn. Ngô Minh Triết đứng tựa lưng vào lan can sắt rỉ sét, hơi lạnh từ kim loại thấm qua lớp áo mỏng khiến anh khẽ rùng mình. Anh nhìn xuống phía dưới, nơi những đám đông đang bắt đầu chia rẽ về hai phía của quảng trường..."

## Required JSON Output Schema:
{{
  "story_id": {inp.story_id},
  "chapter_no": {inp.chapter_no},
  "title": "Tiêu đề chương (Tiếng Việt)",
  "content": "Nội dung chương truyện hoàn chỉnh, dài khoảng {word_target} chữ. Sử dụng \\n để xuống dòng. Bắt đầu viết từ đây...",
  "word_count": 0,
  "new_facts": [],
  "newly_introduced_hooks": [],
  "affected_character_ids": [],
  "continuity_notes": []
}}

Return JSON ONLY. No markdown fences.
""".strip()
