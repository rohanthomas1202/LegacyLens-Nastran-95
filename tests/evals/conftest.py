"""Shared fixtures for eval tests."""

import pytest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def graph_data():
    """Load the cached call graph once for all graph evals."""
    cache = PROJECT_ROOT / "backend" / "graph_cache.json"
    if not cache.exists():
        pytest.skip("graph_cache.json not found — run graph build first")
    return json.loads(cache.read_text())


@pytest.fixture(scope="session")
def call_graph():
    """Build CallGraph object from cache."""
    from backend.features.graph_builder import load_graph
    g = load_graph()
    if g is None:
        pytest.skip("graph_cache.json not found — run graph build first")
    return g


@pytest.fixture(scope="session")
def sample_fortran_files():
    """Return a list of real Fortran files from the codebase."""
    from backend.ingestion.file_discovery import discover_files
    codebases = PROJECT_ROOT / "codebases"
    subdirs = [d for d in codebases.iterdir() if d.is_dir()]
    if not subdirs:
        pytest.skip("No codebase found in codebases/")
    return discover_files(str(subdirs[0]))


@pytest.fixture(scope="session")
def api_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from backend.app import app
    return TestClient(app)
