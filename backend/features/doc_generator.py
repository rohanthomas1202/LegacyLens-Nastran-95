import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS
from backend.retrieval.search import semantic_search
from backend.utils.logger import CostTracker

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def generate_documentation(name: str, top_k: int = 5) -> dict:
    """Generate structured documentation for a code entity."""
    results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=top_k)

    if not results:
        return {"name": name, "documentation": "No matching code found.", "sources": []}

    context = "\n\n".join(
        f"--- {r['name']} ({r['chunk_type']}) in {r['file_path']}:{r['start_line']}-{r['end_line']} ---\n{r['content']}"
        for r in results
    )

    client = _get_client()
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": f"""Generate structured documentation for '{name}' from the NASTRAN-95 Fortran codebase.

Use this format:
## Overview
Brief description of purpose

## Parameters
List input/output parameters and their types

## Logic Flow
Step-by-step explanation of the algorithm

## Dependencies
What it calls and what data it uses (COMMON blocks, etc.)

## Business Rules
Any validation, calculations, or domain logic

## Notes
Special considerations, limitations, or NASTRAN-specific details

Code context:
{context}""",
        }],
    )

    cost_tracker = CostTracker()
    cost_tracker.track_llm(response.usage.input_tokens, response.usage.output_tokens)

    sources = [
        {"file_path": r["file_path"], "start_line": r["start_line"], "end_line": r["end_line"], "name": r["name"]}
        for r in results
    ]

    return {
        "name": name,
        "documentation": response.content[0].text,
        "sources": sources,
    }
