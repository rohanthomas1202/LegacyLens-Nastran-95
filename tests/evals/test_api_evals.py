"""
Eval 3 — API Contract & Integration
Tests that all API endpoints return correct schemas, handle edge cases,
and respond within performance budgets.
"""

import time
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# E3.1  Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_status_200(self, api_client):
        r = api_client.get("/api/health")
        assert r.status_code == 200

    def test_schema(self, api_client):
        data = api_client.get("/api/health").json()
        assert "status" in data
        assert "service" in data


# ---------------------------------------------------------------------------
# E3.2  Graph endpoints
# ---------------------------------------------------------------------------

class TestGraphAPI:
    def test_full_graph(self, api_client):
        r = api_client.get("/api/graph")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data

    def test_subgraph_default(self, api_client):
        r = api_client.post("/api/graph/subgraph", json={"name": "NASTRN", "depth": 1})
        assert r.status_code == 200
        data = r.json()
        assert "center" in data
        assert data["center"] == "NASTRN"
        assert data["node_count"] > 0
        assert data["edge_count"] > 0

    def test_subgraph_not_found(self, api_client):
        r = api_client.post("/api/graph/subgraph", json={"name": "ZZZZNOTREAL", "depth": 1})
        assert r.status_code == 200
        data = r.json()
        assert "error" in data

    def test_subgraph_depth_range(self, api_client):
        for depth in [1, 2, 3]:
            r = api_client.post("/api/graph/subgraph", json={"name": "NASTRN", "depth": depth})
            assert r.status_code == 200, f"Failed at depth {depth}"

    def test_subgraph_latency(self, api_client):
        """Subgraph should respond within 3 seconds."""
        t0 = time.time()
        api_client.post("/api/graph/subgraph", json={"name": "NASTRN", "depth": 1})
        elapsed = time.time() - t0
        assert elapsed < 3.0, f"Subgraph took {elapsed:.1f}s — expected < 3s"


# ---------------------------------------------------------------------------
# E3.3  Autocomplete endpoint
# ---------------------------------------------------------------------------

class TestAutocomplete:
    def test_returns_suggestions(self, api_client):
        r = api_client.post("/api/autocomplete", json={"prefix": "NAS", "limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0

    def test_all_suggestions_match_prefix(self, api_client):
        r = api_client.post("/api/autocomplete", json={"prefix": "SDR", "limit": 10})
        data = r.json()
        for s in data["suggestions"]:
            assert s["name"].startswith("SDR"), f"'{s['name']}' doesn't start with SDR"

    def test_limit_respected(self, api_client):
        r = api_client.post("/api/autocomplete", json={"prefix": "S", "limit": 3})
        data = r.json()
        assert len(data["suggestions"]) <= 3

    def test_empty_prefix(self, api_client):
        r = api_client.post("/api/autocomplete", json={"prefix": "", "limit": 5})
        assert r.status_code in [200, 422]

    def test_no_match_prefix(self, api_client):
        r = api_client.post("/api/autocomplete", json={"prefix": "ZZZZ", "limit": 5})
        assert r.status_code == 200
        assert r.json()["suggestions"] == []


# ---------------------------------------------------------------------------
# E3.4  Flow trace endpoint
# ---------------------------------------------------------------------------

class TestFlowTraceAPI:
    def test_valid_trace(self, api_client):
        r = api_client.post("/api/flow-trace", json={"source": "NASTRN", "target": "XSORT"})
        assert r.status_code == 200
        data = r.json()
        assert "path" in data or "error" in data

    def test_same_source_target(self, api_client):
        r = api_client.post("/api/flow-trace", json={"source": "NASTRN", "target": "NASTRN"})
        assert r.status_code == 200
        data = r.json()
        assert "error" in data

    def test_nonexistent_source(self, api_client):
        r = api_client.post("/api/flow-trace", json={"source": "FAKE123", "target": "NASTRN"})
        assert r.status_code == 200
        assert "error" in r.json()


# ---------------------------------------------------------------------------
# E3.5  Search endpoint (mocked — no Pinecone dependency)
# ---------------------------------------------------------------------------

class TestSearchAPI:
    @patch("backend.retrieval.search.semantic_search")
    def test_returns_results_and_timing(self, mock_search, api_client):
        mock_search.return_value = [
            {"name": "TEST", "content": "code", "score": 0.9,
             "file_path": "test.f", "start_line": 1, "end_line": 10,
             "chunk_type": "subroutine", "language": "fortran", "dependencies": []}
        ]
        r = api_client.post("/api/search", json={"query": "matrix operations"})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "query_time_ms" in data
        assert data["query_time_ms"] >= 0


# ---------------------------------------------------------------------------
# E3.6  File endpoint security
# ---------------------------------------------------------------------------

class TestFileAPISecurity:
    def test_path_traversal_blocked(self, api_client):
        payloads = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "codebases/../../.env",
        ]
        for payload in payloads:
            r = api_client.post("/api/file", json={"file_path": payload})
            assert r.status_code in [404, 403, 400], \
                f"Path traversal not blocked for: {payload}"

    def test_missing_file_404(self, api_client):
        r = api_client.post("/api/file", json={"file_path": "nonexistent/file.f"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# E3.7  Dead code endpoint
# ---------------------------------------------------------------------------

class TestDeadCodeAPI:
    def test_returns_structure(self, api_client):
        r = api_client.get("/api/dead-code")
        assert r.status_code == 200
        data = r.json()
        assert "dead_routines" in data
        assert "stats" in data
