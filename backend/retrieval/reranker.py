import re


def rerank_results(results: list[dict], query: str) -> list[dict]:
    """Re-rank search results by boosting keyword overlap with the query."""
    query_terms = set(re.findall(r"\w+", query.upper()))

    for result in results:
        result["original_score"] = result["score"]
        boost = 0.0

        # Boost for name match (+0.1 per keyword match in chunk name)
        name = result.get("name", "").upper()
        for term in query_terms:
            if term in name:
                boost += 0.1

        # Boost for content match (+0.02 per keyword match, capped at 5)
        content = result.get("content", "").upper()
        content_matches = 0
        for term in query_terms:
            if term in content:
                content_matches += 1
        boost += min(content_matches, 5) * 0.02

        result["score"] = min(result["score"] + boost, 1.0)

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
