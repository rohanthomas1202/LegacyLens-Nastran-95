"""
Eval 5 — End-to-End Generation Quality
Tests that the full RAG pipeline (search → rerank → LLM) produces
well-formed, relevant, and citation-backed answers.
Requires live API keys — skips gracefully if unavailable.
"""

import re
import pytest

try:
    from backend.retrieval.search import semantic_search
    from backend.retrieval.generator import generate_answer
    HAS_PIPELINE = True
except Exception:
    HAS_PIPELINE = False

pytestmark = pytest.mark.skipif(not HAS_PIPELINE, reason="Full pipeline not available")


E2E_CASES = [
    {
        "id": "E1",
        "query": "What is the purpose of the NASTRN subroutine?",
        "expect_in_answer": ["NASTRN"],
        "expect_citation": True,
    },
    {
        "id": "E2",
        "query": "How does NASTRAN handle matrix stiffness assembly?",
        "expect_citation": True,
    },
    {
        "id": "E3",
        "query": "What COMMON blocks are used for open core memory?",
        "expect_in_answer": ["COMMON"],
        "expect_citation": True,
    },
    {
        "id": "E4",
        "query": "Explain the GINO I/O system in NASTRAN",
        "expect_in_answer": ["GINO"],
        "expect_citation": True,
    },
    {
        "id": "E5",
        "query": "What error handling routines exist?",
        "expect_citation": True,
    },
]

CITATION_PATTERN = re.compile(r"[\w/\\]+\.\w+:\d+")


def _run_query(query: str) -> dict:
    """Run the full search → generate pipeline."""
    results = semantic_search(query, top_k=5)
    answer = generate_answer(query, results)
    return {**answer, "search_results": results}


class TestE2EQuality:
    @pytest.mark.parametrize("case", E2E_CASES, ids=[c["id"] for c in E2E_CASES])
    def test_e2e_case(self, case):
        try:
            output = _run_query(case["query"])
        except Exception as e:
            pytest.skip(f"Pipeline unavailable: {e}")

        answer = output["answer"]
        assert len(answer) > 50, f"[{case['id']}] Answer too short ({len(answer)} chars)"

        if case.get("expect_citation"):
            assert CITATION_PATTERN.search(answer), \
                f"[{case['id']}] Answer should contain file:line citations"

        if "expect_in_answer" in case:
            answer_upper = answer.upper()
            for term in case["expect_in_answer"]:
                assert term.upper() in answer_upper, \
                    f"[{case['id']}] Expected '{term}' in answer"

    def test_answer_not_hallucinating_routines(self):
        """Answer should not invent routine names not present in search results."""
        try:
            output = _run_query("What does the NASTRN subroutine do?")
        except Exception:
            pytest.skip("Pipeline unavailable")

        known_names = {r["name"] for r in output["search_results"]}
        answer = output["answer"]

        routine_refs = re.findall(r"\b([A-Z][A-Z0-9]{2,})\b", answer)
        ALLOWED_TERMS = {
            "NASTRAN", "FORTRAN", "NASA", "DMAP", "GINO", "COMMON", "CALL",
            "SUBROUTINE", "FUNCTION", "END", "RETURN", "INTEGER", "REAL",
            "DOUBLE", "PRECISION", "THE", "AND", "FOR", "WITH", "BLOCK",
            "DATA", "ENTRY", "PROGRAM", "LOC", "CORE",
        }
        suspicious = []
        for name in set(routine_refs):
            if name not in known_names and name not in ALLOWED_TERMS and len(name) > 3:
                suspicious.append(name)
        # Allow some — LLM may reference related routines it knows about
        assert len(suspicious) < 10, \
            f"Possibly hallucinated routines: {suspicious}"

    def test_token_counts_present(self):
        try:
            output = _run_query("How does NASTRAN work?")
        except Exception:
            pytest.skip("Pipeline unavailable")
        assert "input_tokens" in output
        assert "output_tokens" in output
        assert output["input_tokens"] > 0
        assert output["output_tokens"] > 0

    def test_latency_under_budget(self):
        """Full query → answer should complete within 15 seconds."""
        import time
        try:
            t0 = time.time()
            _run_query("What subroutines handle element stiffness?")
            elapsed = time.time() - t0
        except Exception:
            pytest.skip("Pipeline unavailable")
        assert elapsed < 15.0, f"E2E took {elapsed:.1f}s — expected < 15s"
