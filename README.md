# LegacyLens for NASTRAN-95

A RAG-powered system that makes the NASA NASTRAN-95 Fortran 77 structural analysis codebase queryable through natural language. Ask questions about the code and receive AI-generated answers with specific file/line references.

## Architecture

```
React Frontend → FastAPI Backend → Pinecone (Vector Search) + OpenAI (Embeddings) + Claude (LLM)
```

**Ingestion**: File Discovery → Fortran 77 Preprocessing → Syntax-Aware Chunking → Embedding → Pinecone
**Retrieval**: Query Embedding → Vector Search (top-k) → Keyword Reranking → Claude Answer Generation

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11 / FastAPI / Uvicorn |
| Frontend | React 19 / Vite |
| Vector DB | Pinecone (serverless, cosine similarity) |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| LLM | Claude Sonnet |
| Deployment | Docker / Railway |

## Features

- **Natural Language Query**: Ask questions about NASTRAN-95 code and get AI answers with file:line citations
- **Syntax-Aware Chunking**: Fortran 77 column-aware parser detects SUBROUTINE/FUNCTION/PROGRAM boundaries
- **Code Explanation**: Plain-English explanations of any subroutine or function
- **Dependency Mapping**: See what a routine calls and what calls it (CALL targets, COMMON blocks)
- **Pattern Detection**: Find structurally similar code across the codebase
- **Documentation Generation**: Auto-generate structured docs for any code entity
- **Business Logic Extraction**: Extract IF conditions, validations, and calculations as structured rules
- **Full File Drill-Down**: Click any source reference to view the full file with syntax highlighting
- **Cost Tracking**: Real-time monitoring of embedding and LLM token usage

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- API keys: OpenAI, Anthropic, Pinecone

### Install

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Configure

```bash
cp .env.example .env
# Edit .env with your API keys:
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
#   PINECONE_API_KEY=pcsk_...
#   PINECONE_INDEX_NAME=nastran95
```

### Ingest Codebase

```bash
# Clone NASTRAN-95 (if not already present)
git clone https://github.com/nasa/NASTRAN-95.git codebases/nastran95

# Run ingestion
python -m backend.ingest codebases/nastran95
```

### Run

```bash
# Backend (dev)
python -m uvicorn backend.app:app --reload

# Frontend (dev, separate terminal)
cd frontend && npm run dev

# Production (serves frontend from backend)
cd frontend && npm run build && cd ..
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t legacylens .
docker run -p 8000:8000 --env-file .env legacylens
```

### Test

```bash
python -m pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/query` | Semantic search + AI answer |
| POST | `/api/search` | Search only (no LLM) |
| POST | `/api/ingest` | Trigger codebase ingestion |
| POST | `/api/explain` | Explain a code entity |
| POST | `/api/dependencies` | Map code dependencies |
| POST | `/api/patterns` | Find similar patterns |
| POST | `/api/generate-docs` | Generate documentation |
| POST | `/api/business-rules` | Extract business rules |
| GET | `/api/stats` | Index and cost stats |
| POST | `/api/file` | Retrieve full file content |

## Project Structure

```
├── backend/
│   ├── app.py                  # FastAPI application + endpoints
│   ├── config.py               # Configuration + constants
│   ├── ingest.py               # Ingestion orchestrator
│   ├── ingestion/
│   │   ├── file_discovery.py   # Recursive file scanner
│   │   ├── preprocessor.py     # Encoding detection + F77 preprocessing
│   │   ├── chunker.py          # Syntax-aware code chunking
│   │   └── embedder.py         # OpenAI embedding with retry
│   ├── retrieval/
│   │   ├── search.py           # Semantic search
│   │   ├── reranker.py         # Keyword-based reranking
│   │   └── generator.py        # Claude LLM answer generation
│   ├── features/
│   │   ├── code_explainer.py   # Code explanation
│   │   ├── dependency_mapper.py# Dependency analysis
│   │   ├── pattern_detector.py # Similar code detection
│   │   ├── doc_generator.py    # Documentation generation
│   │   └── business_logic.py   # Business rule extraction
│   ├── vector_store/
│   │   └── pinecone_client.py  # Pinecone operations
│   └── utils/
│       └── logger.py           # Logging + cost tracking
├── frontend/
│   └── src/
│       ├── App.jsx             # React SPA (Query, Analysis, Stats tabs)
│       └── App.css             # Dark theme styles
├── tests/
│   ├── test_chunker.py         # 38 chunker tests
│   ├── test_reranker.py        # 7 reranker tests
│   ├── test_preprocessor.py    # 10 preprocessor tests
│   └── test_api.py             # 8 API endpoint tests
├── docs/
│   ├── pre-search.md           # Pre-search decision document
│   ├── architecture.md         # RAG architecture deep-dive
│   └── cost-analysis.md        # AI cost projections
└── codebases/
    └── nastran95/              # Cloned NASTRAN-95 repo
```

## Codebase Stats

- **Source files**: 1,846 Fortran 77 files
- **Lines of code**: 418,349
- **Chunks indexed**: 4,040
- **Embedding tokens**: 4,680,546
- **Tests**: 64 (all passing)

## Documentation

- [Pre-Search Document](docs/pre-search.md) — Constraints, architecture decisions, evaluation criteria
- [RAG Architecture](docs/architecture.md) — Vector DB selection, embedding strategy, chunking approach, failure modes
- [AI Cost Analysis](docs/cost-analysis.md) — Development costs, production projections, optimization strategies
