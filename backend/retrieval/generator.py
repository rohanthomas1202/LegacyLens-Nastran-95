import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS
from backend.utils.logger import CostTracker

_client = None

SYSTEM_PROMPT = """You are an expert on the NASA NASTRAN-95 structural analysis program, a large Fortran 77 codebase used for finite element analysis.

When answering questions about this codebase, keep in mind:
- **COMMON blocks** are used for shared data between subroutines (similar to global variables)
- **DMAP** (Direct Matrix Abstraction Program) is NASTRAN's executive control language that sequences module execution
- **GINO** (General Input/Output) is NASTRAN's I/O system for reading/writing data blocks
- **Open Core** is NASTRAN's memory management system that dynamically allocates working storage
- **ENTRY** statements provide alternate entry points into subroutines
- Fortran 77 uses fixed-form format: columns 1-5 for labels, column 6 for continuation, columns 7-72 for code

Always cite specific file paths and line numbers when referencing code. Format citations as `file_path:line_start-line_end`.

Provide clear, concise explanations that a developer unfamiliar with Fortran or NASTRAN could understand."""


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def generate_answer(query: str, search_results: list[dict]) -> dict:
    """Generate an AI answer using Claude with retrieved context."""
    client = _get_client()
    cost_tracker = CostTracker()

    # Build context from search results
    context_parts = []
    for i, result in enumerate(search_results, 1):
        context_parts.append(
            f"--- Source {i}: {result['name']} ({result['chunk_type']}) "
            f"in {result['file_path']}:{result['start_line']}-{result['end_line']} "
            f"[relevance: {result['score']:.2f}] ---\n"
            f"{result['content']}"
        )

    context = "\n\n".join(context_parts)

    user_message = f"""Based on the following code from the NASTRAN-95 codebase, answer this question:

**Question:** {query}

**Retrieved Code Context:**
{context}

Provide a clear answer with specific file:line references to the code shown above."""

    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # Track costs
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_tracker.track_llm(input_tokens, output_tokens)

    answer = response.content[0].text

    return {
        "answer": answer,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def generate_answer_stream(query: str, search_results: list[dict]):
    """Stream an AI answer using Claude with retrieved context. Yields SSE events."""
    import json

    client = _get_client()
    cost_tracker = CostTracker()

    # Build context from search results
    context_parts = []
    for i, result in enumerate(search_results, 1):
        context_parts.append(
            f"--- Source {i}: {result['name']} ({result['chunk_type']}) "
            f"in {result['file_path']}:{result['start_line']}-{result['end_line']} "
            f"[relevance: {result['score']:.2f}] ---\n"
            f"{result['content']}"
        )

    context = "\n\n".join(context_parts)

    user_message = f"""Based on the following code from the NASTRAN-95 codebase, answer this question:

**Question:** {query}

**Retrieved Code Context:**
{context}

Provide a clear answer with specific file:line references to the code shown above."""

    # Send sources first as a JSON event
    yield f"event: sources\ndata: {json.dumps(search_results)}\n\n"

    # Stream the answer
    with client.messages.stream(
        model=LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            escaped = json.dumps(text)
            yield f"event: token\ndata: {escaped}\n\n"

        # After stream completes, get usage
        response = stream.get_final_message()
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_tracker.track_llm(input_tokens, output_tokens)

        yield f"event: done\ndata: {json.dumps({'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"
