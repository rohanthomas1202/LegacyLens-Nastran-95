"""
Eval 4 — Retrieval Quality
Tests that semantic search returns relevant chunks for known queries.
These require a live Pinecone index — skip gracefully if unavailable.
"""

import pytest

try:
    from backend.retrieval.search import semantic_search
    HAS_SEARCH = True
except Exception:
    HAS_SEARCH = False

pytestmark = pytest.mark.skipif(not HAS_SEARCH, reason="Search module not available")

RETRIEVAL_CASES = [
    {
        "id": "R1",
        "query": "What does the main NASTRAN driver subroutine do?",
        "expect_names": ["NASTRN"],
        "expect_types": ["subroutine"],
        "top_k": 5,
    },
    {
        "id": "R2",
        "query": "matrix assembly and stiffness",
        "expect_language": "fortran",
        "top_k": 5,
    },
    {
        "id": "R3",
        "query": "COMMON block for system memory management",
        "expect_in_content": ["COMMON"],
        "top_k": 5,
    },
    {
        "id": "R4",
        "query": "eigenvalue solver routine",
        "expect_types": ["subroutine", "function"],
        "top_k": 5,
    },
    {
        "id": "R5",
        "query": "error handling and diagnostics",
        "top_k": 5,
        "min_results": 1,
    },
]


class TestRetrievalQuality:
    @pytest.mark.parametrize("case", RETRIEVAL_CASES, ids=[c["id"] for c in RETRIEVAL_CASES])
    def test_retrieval_case(self, case):
        try:
            results = semantic_search(case["query"], top_k=case.get("top_k", 5))
        except Exception as e:
            pytest.skip(f"Search unavailable: {e}")

        min_results = case.get("min_results", 1)
        assert len(results) >= min_results, \
            f"[{case['id']}] Expected >= {min_results} results, got {len(results)}"

        if "expect_names" in case:
            found_names = {r["name"] for r in results}
            for name in case["expect_names"]:
                assert name in found_names, \
                    f"[{case['id']}] Expected '{name}' in top-{case['top_k']}, got {found_names}"

        if "expect_types" in case:
            found_types = {r["chunk_type"] for r in results}
            assert found_types & set(case["expect_types"]), \
                f"[{case['id']}] Expected types {case['expect_types']}, got {found_types}"

        if "expect_language" in case:
            for r in results:
                assert r["language"] == case["expect_language"], \
                    f"[{case['id']}] Expected language '{case['expect_language']}', got '{r['language']}'"

        if "expect_in_content" in case:
            all_content = " ".join(r.get("content", "") for r in results)
            for term in case["expect_in_content"]:
                assert term.upper() in all_content.upper(), \
                    f"[{case['id']}] Expected '{term}' in retrieved content"

    def test_scores_descending(self):
        try:
            results = semantic_search("subroutine call graph", top_k=5)
        except Exception:
            pytest.skip("Search unavailable")
        if len(results) < 2:
            pytest.skip("Not enough results")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Scores should be in descending order"

    def test_results_have_complete_metadata(self):
        try:
            results = semantic_search("input output file operations", top_k=3)
        except Exception:
            pytest.skip("Search unavailable")
        required = {"name", "file_path", "start_line", "end_line", "chunk_type", "score", "content"}
        for r in results:
            missing = required - set(r.keys())
            assert not missing, f"Result '{r.get('name', '?')}' missing fields: {missing}"
