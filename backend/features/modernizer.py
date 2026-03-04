import re

import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL
from backend.retrieval.search import semantic_search
from backend.utils.logger import CostTracker

_client = None

VALID_LANGUAGES = {"python", "c", "java", "rust"}

LANGUAGE_HINTS = {
    "python": "Use Python 3.11+ idioms. Use type hints. Use dataclasses or classes where COMMON blocks exist. Use numpy for array operations if appropriate.",
    "c": "Use C11 standard. Use structs for COMMON block data. Use proper header includes. Replace GOTO with structured control flow.",
    "java": "Use Java 17+. Create a class for each subroutine/function. Use records or classes for COMMON block data.",
    "rust": "Use idiomatic Rust. Use structs for COMMON block data. Handle errors with Result types. Use iterators instead of explicit loops where appropriate.",
}


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _extract_section(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def modernize_code(name: str, target_language: str, top_k: int = 5) -> dict:
    """Translate a Fortran 77 entity to a modern language."""
    if target_language not in VALID_LANGUAGES:
        return {"error": f"Unsupported language: {target_language}. Choose from: {', '.join(sorted(VALID_LANGUAGES))}"}

    results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=top_k)

    if not results:
        return {"name": name, "target_language": target_language, "error": "No matching code found."}

    context = "\n\n".join(
        f"--- {r['name']} ({r['chunk_type']}) in {r['file_path']}:{r['start_line']}-{r['end_line']} ---\n{r['content']}"
        for r in results
    )

    original_code = results[0]["content"]
    lang_hints = LANGUAGE_HINTS[target_language]

    client = _get_client()
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""Translate the Fortran 77 entity '{name}' from the NASTRAN-95 codebase into {target_language}.

{lang_hints}

Return your response in exactly this format:

<translated_code>
(The complete translated code, with inline comments for non-obvious mappings)
</translated_code>

<migration_notes>
## Idiom Mappings
- Each Fortran idiom and its modern equivalent

## COMMON Block Handling
- How shared data was restructured

## Control Flow Changes
- GOTOs, computed GOTOs, arithmetic IFs that were restructured

## Type Mappings
- Fortran types to {target_language} types (INTEGER*4 -> int, REAL*8 -> double, etc.)

## Caveats
- Anything that could not be directly translated or requires manual review
</migration_notes>

Original Fortran code context:
{context}""",
        }],
    )

    cost_tracker = CostTracker()
    cost_tracker.track_llm(response.usage.input_tokens, response.usage.output_tokens)

    answer_text = response.content[0].text
    translated_code = _extract_section(answer_text, "translated_code")
    migration_notes = _extract_section(answer_text, "migration_notes")

    sources = [
        {"file_path": r["file_path"], "start_line": r["start_line"], "end_line": r["end_line"], "name": r["name"]}
        for r in results
    ]

    return {
        "name": name,
        "target_language": target_language,
        "original_code": original_code,
        "translated_code": translated_code or answer_text,
        "migration_notes": migration_notes or "",
        "sources": sources,
    }
