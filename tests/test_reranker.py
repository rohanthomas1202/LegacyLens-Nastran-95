import pytest
from backend.retrieval.reranker import rerank_results


class TestReranker:
    def test_boosts_name_match(self):
        results = [
            {"name": "OTHER", "content": "some code", "score": 0.7},
            {"name": "SDR2A", "content": "some code", "score": 0.7},
        ]
        reranked = rerank_results(results, "Find SDR2A subroutine")
        # SDR2A gets +0.1 name boost, so should be first
        assert reranked[0]["name"] == "SDR2A"

    def test_preserves_original_score(self):
        results = [{"name": "TEST", "content": "code", "score": 0.5}]
        reranked = rerank_results(results, "something else")
        assert "original_score" in reranked[0]
        assert reranked[0]["original_score"] == 0.5

    def test_score_capped_at_1(self):
        results = [{"name": "TEST", "content": "TEST TEST TEST TEST TEST TEST", "score": 0.95}]
        reranked = rerank_results(results, "TEST")
        assert reranked[0]["score"] <= 1.0

    def test_content_boost(self):
        results = [
            {"name": "A", "content": "MATRIX STIFFNESS ASSEMBLY", "score": 0.5},
            {"name": "B", "content": "unrelated code", "score": 0.5},
        ]
        reranked = rerank_results(results, "stiffness matrix assembly")
        assert reranked[0]["name"] == "A"

    def test_empty_results(self):
        assert rerank_results([], "query") == []

    def test_sorted_descending(self):
        results = [
            {"name": "LOW", "content": "", "score": 0.3},
            {"name": "HIGH", "content": "", "score": 0.9},
            {"name": "MID", "content": "", "score": 0.6},
        ]
        reranked = rerank_results(results, "unrelated")
        scores = [r["score"] for r in reranked]
        assert scores == sorted(scores, reverse=True)

    def test_case_insensitive(self):
        results = [
            {"name": "nastrn", "content": "", "score": 0.5},
        ]
        reranked = rerank_results(results, "NASTRN program")
        assert reranked[0]["score"] > 0.5
