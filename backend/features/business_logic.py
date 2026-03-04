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


def extract_business_logic(name: str, top_k: int = 5) -> dict:
    """Extract business rules and logic from a code entity."""
    results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=top_k)

    if not results:
        return {"name": name, "rules": "No matching code found.", "sources": []}

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
            "content": f"""Extract business rules and logic from '{name}' in the NASTRAN-95 codebase.

For each rule found, provide:
- **Rule ID**: BR-001, BR-002, etc.
- **Condition**: What triggers this rule (IF conditions, validations)
- **Action**: What happens when the condition is met
- **Location**: file:line reference
- **Category**: validation, calculation, control-flow, error-handling, or data-transformation

Focus on:
1. IF/THEN conditions and what they control
2. Mathematical formulas and calculations
3. Error checking and validation
4. Data transformations
5. Control flow decisions

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
        "rules": response.content[0].text,
        "sources": sources,
    }
