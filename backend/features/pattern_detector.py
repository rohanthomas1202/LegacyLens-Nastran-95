from backend.retrieval.search import semantic_search


def detect_patterns(name: str, top_k: int = 10) -> dict:
    """Find similar code patterns by embedding similarity."""
    # Search for the entity to get its code
    entity_results = semantic_search(f"SUBROUTINE FUNCTION {name}", top_k=2)

    if not entity_results:
        return {"name": name, "similar_patterns": [], "sources": []}

    # Use the entity's content as a query to find similar code
    entity_content = entity_results[0]["content"]
    # Take first 500 chars as the search query for similarity
    search_query = entity_content[:500]

    similar_results = semantic_search(search_query, top_k=top_k)

    # Filter out the entity itself and build pattern list
    similar_patterns = []
    entity_name = name.upper()
    for r in similar_results:
        if r["name"].upper() == entity_name and r["file_path"] == entity_results[0]["file_path"]:
            continue  # Skip self
        similar_patterns.append({
            "name": r["name"],
            "file_path": r["file_path"],
            "start_line": r["start_line"],
            "end_line": r["end_line"],
            "chunk_type": r["chunk_type"],
            "similarity": round(r["score"], 3),
            "content_preview": r["content"][:200],
        })

    sources = [
        {"file_path": r["file_path"], "start_line": r["start_line"], "end_line": r["end_line"], "name": r["name"]}
        for r in entity_results
    ]

    return {
        "name": name,
        "similar_patterns": similar_patterns,
        "sources": sources,
    }
