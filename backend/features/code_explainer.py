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


def explain_code(name: str, top_k: int = 5) -> dict:
    """Find a code entity and explain what it does in plain English."""
    results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=top_k)

    if not results:
        return {"name": name, "explanation": "No matching code found.", "sources": []}

    # Build context
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
            "content": f"""Explain what the code entity '{name}' does in the NASTRAN-95 codebase.
Provide a clear, plain-English explanation covering:
1. Purpose and functionality
2. Key inputs and outputs
3. Important business logic or algorithms
4. How it fits into the larger system

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
        "explanation": response.content[0].text,
        "sources": sources,
    }
