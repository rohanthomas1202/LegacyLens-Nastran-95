import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import FRONTEND_DIST, CODEBASES_DIR
from backend.retrieval.search import semantic_search
from backend.retrieval.reranker import rerank_results
from backend.retrieval.generator import generate_answer
from backend.vector_store.pinecone_client import PineconeStore
from backend.utils.logger import logger, CostTracker

app = FastAPI(title="LegacyLens - NASTRAN-95", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request models ----------

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    language: str = None
    file_path: str = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    language: str = None
    file_path: str = None


class IngestRequest(BaseModel):
    codebase_path: str


class EntityRequest(BaseModel):
    name: str
    top_k: int = 5


class FileRequest(BaseModel):
    file_path: str


# ---------- API Endpoints ----------

@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "LegacyLens NASTRAN-95"}


@app.post("/api/query")
def query(req: QueryRequest):
    """Semantic search + AI-generated answer."""
    start = time.time()
    cost_tracker = CostTracker()
    cost_tracker.track_query()

    try:
        # Search
        results = semantic_search(
            req.query, top_k=req.top_k, language=req.language, file_path=req.file_path
        )

        # Rerank
        reranked = rerank_results(results, req.query)

        # Generate answer
        answer_data = generate_answer(req.query, reranked)

        elapsed = time.time() - start
        return {
            "answer": answer_data["answer"],
            "sources": reranked,
            "query_time_ms": round(elapsed * 1000),
            "input_tokens": answer_data["input_tokens"],
            "output_tokens": answer_data["output_tokens"],
        }
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
def search(req: SearchRequest):
    """Search only — no LLM generation."""
    start = time.time()

    try:
        results = semantic_search(
            req.query, top_k=req.top_k, language=req.language, file_path=req.file_path
        )
        reranked = rerank_results(results, req.query)

        elapsed = time.time() - start
        return {
            "results": reranked,
            "query_time_ms": round(elapsed * 1000),
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
def ingest(req: IngestRequest):
    """Trigger codebase ingestion."""
    from backend.ingest import ingest_codebase

    try:
        result = ingest_codebase(req.codebase_path)
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/explain")
def explain(req: EntityRequest):
    """Explain a code entity in plain English."""
    from backend.features.code_explainer import explain_code
    try:
        return explain_code(req.name, req.top_k)
    except Exception as e:
        logger.error(f"Explain failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dependencies")
def dependencies(req: EntityRequest):
    """Map dependencies of a code entity."""
    from backend.features.dependency_mapper import map_dependencies
    try:
        return map_dependencies(req.name, req.top_k)
    except Exception as e:
        logger.error(f"Dependencies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/patterns")
def patterns(req: EntityRequest):
    """Find similar code patterns."""
    from backend.features.pattern_detector import detect_patterns
    try:
        return detect_patterns(req.name, req.top_k)
    except Exception as e:
        logger.error(f"Patterns failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-docs")
def generate_docs(req: EntityRequest):
    """Generate documentation for a code entity."""
    from backend.features.doc_generator import generate_documentation
    try:
        return generate_documentation(req.name, req.top_k)
    except Exception as e:
        logger.error(f"Doc generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/business-rules")
def business_rules(req: EntityRequest):
    """Extract business rules from a code entity."""
    from backend.features.business_logic import extract_business_logic
    try:
        return extract_business_logic(req.name, req.top_k)
    except Exception as e:
        logger.error(f"Business rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def stats():
    """Return index stats and cost tracking."""
    try:
        store = PineconeStore()
        index_stats = store.get_stats()
        cost_tracker = CostTracker()
        costs = cost_tracker.get_costs()
        return {"index": index_stats, "costs": costs}
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file")
def get_file(req: FileRequest):
    """Return full file content for drill-down context."""
    # Search across all codebase directories
    if not CODEBASES_DIR.exists():
        raise HTTPException(status_code=404, detail="No codebases directory found")
    for codebase_dir in CODEBASES_DIR.iterdir():
        if not codebase_dir.is_dir():
            continue
        full_path = (codebase_dir / req.file_path).resolve()
        codebase_resolved = codebase_dir.resolve()

        # Security: ensure path is within codebase
        if not str(full_path).startswith(str(codebase_resolved)):
            continue

        if full_path.exists():
            content = full_path.read_text(encoding="utf-8", errors="replace")
            return {
                "file_path": req.file_path,
                "content": content,
                "total_lines": content.count("\n") + 1,
            }

    raise HTTPException(status_code=404, detail="File not found")


# ---------- Static file serving ----------

# Serve frontend if dist exists
if FRONTEND_DIST.exists():
    # Mount assets directory
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"))

    # SPA catch-all (must be last)
    @app.get("/{path:path}")
    def serve_spa(path: str):
        file = FRONTEND_DIST / path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
