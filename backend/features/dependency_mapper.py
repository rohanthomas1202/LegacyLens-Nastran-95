import json

from backend.retrieval.search import semantic_search


def map_dependencies(name: str, top_k: int = 5) -> dict:
    """Map what a code entity calls and what calls it."""
    # Find the entity itself
    results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=top_k)

    calls = []
    called_by = []

    for r in results:
        # Extract outgoing calls from dependencies metadata
        deps = r.get("dependencies", [])
        if isinstance(deps, str):
            try:
                deps = json.loads(deps)
            except json.JSONDecodeError:
                deps = []

        for dep in deps:
            if dep.startswith("CALL:"):
                target = dep.replace("CALL:", "")
                if target not in calls:
                    calls.append(target)
            elif dep.startswith("COMMON:"):
                block = dep.replace("COMMON:", "")
                if f"COMMON:{block}" not in calls:
                    calls.append(f"COMMON:{block}")
            elif dep.startswith("INCLUDE:"):
                inc = dep.replace("INCLUDE:", "")
                if f"INCLUDE:{inc}" not in calls:
                    calls.append(f"INCLUDE:{inc}")

    # Find callers (who calls this entity)
    caller_results = semantic_search(f"CALL {name}", top_k=top_k)
    for r in caller_results:
        # Check if this chunk actually calls the target
        content_upper = r.get("content", "").upper()
        if f"CALL {name.upper()}" in content_upper:
            caller_info = {
                "name": r["name"],
                "file_path": r["file_path"],
                "start_line": r["start_line"],
                "end_line": r["end_line"],
                "chunk_type": r["chunk_type"],
            }
            if caller_info not in called_by:
                called_by.append(caller_info)

    sources = [
        {"file_path": r["file_path"], "start_line": r["start_line"], "end_line": r["end_line"], "name": r["name"]}
        for r in results
    ]

    return {
        "name": name,
        "calls": calls,
        "called_by": called_by,
        "sources": sources,
    }
