import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.config import FRONTEND_DIST, CODEBASES_DIR
from backend.retrieval.search import semantic_search
from backend.retrieval.reranker import rerank_results
from backend.retrieval.generator import generate_answer, generate_answer_stream
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


class ModernizeRequest(BaseModel):
    name: str
    target_language: str
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


@app.post("/api/modernize")
def modernize(req: ModernizeRequest):
    """Translate Fortran code to a modern language."""
    from backend.features.modernizer import modernize_code
    try:
        return modernize_code(req.name, req.target_language, req.top_k)
    except Exception as e:
        logger.error(f"Modernize failed: {e}")
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


# ---------- Graph Endpoints ----------

class SubgraphRequest(BaseModel):
    name: str = None
    depth: int = 2
    include_common: bool = False


@app.get("/api/graph")
def get_graph():
    """Return the full call graph (builds if not cached)."""
    from backend.features.graph_builder import load_or_build_graph
    try:
        graph = load_or_build_graph()
        return graph.to_dict()
    except Exception as e:
        logger.error(f"Graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/build")
def build_graph():
    """Force rebuild of the call graph cache."""
    from backend.features.graph_builder import build_call_graph
    try:
        graph = build_call_graph()
        data = graph.to_dict()
        return {"status": "built", "stats": data["stats"]}
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/subgraph")
def subgraph(req: SubgraphRequest):
    """Return a subgraph centered on a node."""
    from backend.features.graph_builder import get_subgraph
    try:
        return get_subgraph(
            center=req.name or "NASTRN",
            depth=req.depth,
            include_common=req.include_common,
        )
    except Exception as e:
        logger.error(f"Subgraph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Flow Tracer ----------

class FlowTraceRequest(BaseModel):
    source: str
    target: str


@app.post("/api/flow-trace")
def flow_trace(req: FlowTraceRequest):
    """Find shortest call path between two routines."""
    from backend.features.flow_tracer import trace_flow
    try:
        return trace_flow(req.source, req.target)
    except Exception as e:
        logger.error(f"Flow trace failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Autocomplete ----------

class AutocompleteRequest(BaseModel):
    prefix: str
    limit: int = 10


@app.post("/api/autocomplete")
def autocomplete(req: AutocompleteRequest):
    """Search graph node names by prefix for autocomplete."""
    from backend.features.graph_builder import load_or_build_graph
    try:
        graph = load_or_build_graph()
        prefix = req.prefix.upper()
        matches = []
        for name, info in graph.nodes.items():
            if name.startswith(prefix):
                matches.append({"name": name, **info})
                if len(matches) >= req.limit:
                    break
        return {"suggestions": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Dead Code ----------

@app.get("/api/dead-code")
def dead_code():
    """Detect potentially dead (unreachable) routines."""
    from backend.features.dead_code import detect_dead_code
    try:
        return detect_dead_code()
    except Exception as e:
        logger.error(f"Dead code detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- COMMON Blocks ----------

@app.get("/api/common-blocks")
def common_blocks():
    """Inspect all COMMON blocks and their shared routines."""
    from backend.features.common_blocks import get_common_blocks
    try:
        return get_common_blocks()
    except Exception as e:
        logger.error(f"Common blocks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Impact Analysis ----------

class ImpactRequest(BaseModel):
    name: str
    max_depth: int = 5


@app.post("/api/impact")
def impact(req: ImpactRequest):
    """Analyze impact of changing a routine."""
    from backend.features.impact_analyzer import analyze_impact
    try:
        return analyze_impact(req.name, req.max_depth)
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Complexity Metrics ----------

class ComplexityRequest(BaseModel):
    name: str = None
    top_n: int = 20


@app.post("/api/complexity")
def complexity(req: ComplexityRequest):
    """Compute code complexity metrics."""
    from backend.features.complexity import get_complexity
    try:
        return get_complexity(req.name, req.top_n)
    except Exception as e:
        logger.error(f"Complexity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Architecture Map ----------

@app.get("/api/architecture")
def architecture():
    """Module-level architecture map."""
    from backend.features.architecture import get_architecture
    try:
        return get_architecture()
    except Exception as e:
        logger.error(f"Architecture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Variable Cross-Reference ----------

class XrefRequest(BaseModel):
    variable: str
    limit: int = 50


@app.post("/api/xref")
def xref(req: XrefRequest):
    """Cross-reference a variable across routines."""
    from backend.features.xref import cross_reference
    try:
        return cross_reference(req.variable, req.limit)
    except Exception as e:
        logger.error(f"Xref failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Call Stack Simulator ----------

class SimulateRequest(BaseModel):
    entry_point: str
    max_steps: int = 200


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    """Simulate call stack execution from an entry point."""
    from backend.features.call_simulator import simulate_calls
    try:
        return simulate_calls(req.entry_point, req.max_steps)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Batch Modernization ----------

class BatchModernizeRequest(BaseModel):
    names: list[str] = None
    directory: str = None
    target_language: str = "python"


@app.post("/api/modernize/batch")
def batch_modernize(req: BatchModernizeRequest):
    """Batch modernize multiple routines with dependency ordering."""
    from backend.features.batch_modernizer import batch_modernize
    try:
        return batch_modernize(req.names, req.directory, req.target_language)
    except Exception as e:
        logger.error(f"Batch modernize failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Streaming Query ----------

@app.post("/api/query/stream")
def query_stream(req: QueryRequest):
    """Semantic search + streamed AI answer via SSE."""
    try:
        results = semantic_search(
            req.query, top_k=req.top_k, language=req.language, file_path=req.file_path
        )
        reranked = rerank_results(results, req.query)

        cost_tracker = CostTracker()
        cost_tracker.track_query()

        return StreamingResponse(
            generate_answer_stream(req.query, reranked),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        logger.error(f"Stream query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- File ----------

@app.post("/api/file")
def get_file(req: FileRequest):
    """Return full file content for drill-down context."""
    # Normalize backslashes to forward slashes for cross-platform compatibility
    normalized_path = req.file_path.replace("\\", "/")

    # Search across all codebase directories
    if not CODEBASES_DIR.exists():
        raise HTTPException(status_code=404, detail="No codebases directory found")
    for codebase_dir in CODEBASES_DIR.iterdir():
        if not codebase_dir.is_dir():
            continue
        full_path = (codebase_dir / normalized_path).resolve()
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
