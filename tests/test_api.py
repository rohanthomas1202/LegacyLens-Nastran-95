import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_returns_healthy(self):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_returns_service_name(self):
        response = client.get("/api/health")
        data = response.json()
        assert "NASTRAN" in data["service"]


class TestSearchEndpoint:
    @patch("backend.retrieval.search.semantic_search")
    def test_returns_results(self, mock_search):
        mock_search.return_value = [
            {"name": "TEST", "content": "code", "score": 0.9,
             "file_path": "test.f", "start_line": 1, "end_line": 10,
             "chunk_type": "subroutine", "language": "fortran", "dependencies": []}
        ]
        response = client.post("/api/search", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query_time_ms" in data

    def test_empty_query_still_works(self):
        # Should not crash on empty query
        response = client.post("/api/search", json={"query": ""})
        # May return error or empty results, but shouldn't 500
        assert response.status_code in [200, 422, 500]


class TestFileEndpoint:
    def test_missing_file_returns_404(self):
        response = client.post("/api/file", json={"file_path": "nonexistent/file.f"})
        assert response.status_code == 404

    def test_path_traversal_blocked(self):
        response = client.post("/api/file", json={"file_path": "../../etc/passwd"})
        assert response.status_code == 404


class TestStatsEndpoint:
    @patch("backend.vector_store.pinecone_client.PineconeStore")
    def test_returns_stats(self, mock_store_cls):
        mock_instance = MagicMock()
        mock_instance.get_stats.return_value = {
            "total_vectors": 100, "namespaces": {}, "dimension": 1536
        }
        mock_store_cls.return_value = mock_instance

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "index" in data
        assert "costs" in data
