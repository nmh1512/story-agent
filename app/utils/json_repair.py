"""JSON parse helper with fallback repair for malformed LLM output."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _extract_json_block(text: str) -> str:
    """Extract the first JSON object or array from a string, prioritizing objects."""
    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        return fenced.group(1).strip()

    # Try to find the first { (Object) first, as it's our primary target
    obj_start = text.find("{")
    arr_start = text.find("[")

    # If { exists and is before [ (or [ doesn't exist), prefer {
    if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
        start_char, end_char = "{", "}"
        start = obj_start
    elif arr_start != -1:
        start_char, end_char = "[", "]"
        start = arr_start
    else:
        return text

    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


def _balance_json(text: str) -> str:
    """Attempt to close any unclosed braces or brackets at the end of a truncated string."""
    text = text.strip()
    if not text:
        return text

    # Remove any trailing incomplete key/value or comma
    # e.g. "key": "val", "oth... -> "key": "val"
    text = re.sub(r',?\s*["\w]*\s*:?\s*[^}\]]*$', '', text)

    stack = []
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if char == '"' and not escape:
            in_string = not in_string
        if in_string:
            if char == '\\' and not escape:
                escape = True
            else:
                escape = False
            continue
        
        if char in '{[':
            stack.append(char)
        elif char in '}]':
            if not stack:
                continue # Malformed
            if (char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '['):
                stack.pop()

    # If we are inside a string, close it
    if in_string:
        text += '"'

    # Close the stack in reverse
    while stack:
        opening = stack.pop()
        text += '}' if opening == '{' else ']'
    
    return text


def parse_json_safe(text: str) -> Any:
    """
    Attempt to parse JSON from LLM output with multiple repair strategies.
    1. Direct parse
    2. Extract block
    3. Clean trailing commas
    4. Balance truncated braces
    """
    if not text:
        return {}

    # Strategy 1: Direct or Fenced
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    extracted = _extract_json_block(text)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Clean and Balance
    cleaned = re.sub(r",\s*([}\]])", r"\1", extracted)
    balanced = _balance_json(cleaned)
    
    try:
        return json.loads(balanced)
    except json.JSONDecodeError:
        try:
            # Last ditch attempt with a simpler balance
            last_ditch = cleaned.rstrip()
            if not last_ditch.endswith(('}', ']')):
                last_ditch += '}'
            return json.loads(last_ditch)
        except:
            logger.error("Failed to parse JSON even after repair. Header (300): %s", text[:300])
            return {}
