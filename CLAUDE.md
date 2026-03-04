# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LegacyLens for NASTRAN-95: a RAG-powered system that makes the NASA NASTRAN-95 Fortran 77 structural analysis codebase queryable through natural language. Users ask questions about the code and receive AI-generated answers with specific file/line references.

Target codebase: `codebases/nastran95` (clone from `https://github.com/nasa/NASTRAN-95.git`). Minimum 10,000+ LOC across 50+ files.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn
- **Frontend**: React 19 / Vite
- **Vector DB**: Pinecone (serverless, AWS us-east-1, cosine similarity)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **LLM**: Claude Sonnet for answer generation
- **Deployment**: Docker / Railway

## Commands

```bash
# Install
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Configure
cp .env.example .env   # then fill in API keys

# Ingest a codebase
python -m backend.ingest codebases/nastran95

# Run backend (dev)
uvicorn backend.app:app --reload

# Run backend (prod)
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# Run frontend (dev)
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint

# Docker
docker build -t legacylens . && docker run -p 8000:8000 --env-file .env legacylens
```

## Architecture

Two-pipeline design:

**Ingestion Pipeline** (`backend/ingest.py` orchestrator):
```
file_discovery → preprocessor → chunker → embedder → pinecone_client
```
- `backend/ingestion/file_discovery.py` — Recursively scan codebase, detect language from extensions (`.f`, `.f77`, `.f90` for Fortran; `.cob`, `.cbl` for COBOL; `.c`, `.h` for C). Skips NASTRAN-specific `bin/inp/um` directories.
- `backend/ingestion/preprocessor.py` — Encoding detection (chardet), Fortran 77 column truncation (cols 73-80 are sequence numbers), whitespace normalization.
- `backend/ingestion/chunker.py` — **Core module** (~500 lines). Syntax-aware chunking per language. For Fortran 77: column-aware parsing (cols 1-6 labels, col 6 continuation, cols 7-72 code), recognizes SUBROUTINE/FUNCTION/BLOCK DATA/PROGRAM/ENTRY keywords, tracks bare END statements. Extracts CALL targets, COMMON blocks, INCLUDE dependencies. Falls back to fixed-size (40 lines, 10-line overlap).
- `backend/ingestion/embedder.py` — Batches of 100 chunks, prepends metadata header `[LANGUAGE TYPE 'name' in file:lines]` before embedding.
- `backend/vector_store/pinecone_client.py` — Singleton PineconeStore. Upserts in 100-vector batches. 40KB metadata limit per vector.

**Retrieval Pipeline** (triggered via API endpoints):
```
query → embed_query → pinecone search (top-k) → rerank → Claude LLM generation
```
- `backend/retrieval/search.py` — Semantic search with metadata filtering
- `backend/retrieval/reranker.py` — Re-rank by relevance score
- `backend/retrieval/generator.py` — Claude LLM with NASTRAN-specific prompt (explains COMMON blocks, DMAP executive control, GINO I/O, Open Core memory). Enforces citation of file:line references.

**Features** (`backend/features/`): Code explanation, dependency mapping, pattern detection, doc generation, business logic extraction.

**Frontend** (`frontend/src/App.jsx`): Single React SPA with Query, Code Analysis, and Stats tabs. Calls backend at `http://localhost:8000/api/`.

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

## Configuration

Environment variables (`.env`):
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PINECONE_API_KEY` — required
- `PINECONE_INDEX_NAME` — defaults to `nastran95`

Key constants (`backend/config.py`):
- `EMBEDDING_DIMENSIONS = 1536`
- `CHUNK_SIZE_TOKENS = 800` (200-token overlap)
- `TOP_K = 5` (default results per query)

## Fortran 77 / NASTRAN-95 Specifics

The chunker handles Fortran 77 fixed-form format:
- **Columns 1-5**: Statement label
- **Column 6**: Continuation character (any non-blank/non-zero)
- **Columns 7-72**: Source code
- **Columns 73-80**: Sequence numbers (stripped during preprocessing)
- Comments: `C` or `*` in column 1

NASTRAN-specific patterns to be aware of:
- ENTRY statements (alternate entry points to subroutines)
- COMMON blocks for shared data
- DMAP sequences (executive control language)
- GINO (General Input/Output) system calls
- Open Core memory management

## Cost Tracking

`backend/utils/logger.py` has a CostTracker that persists to `logs/costs.json`. Tracks embedding tokens ($0.02/1M) and LLM tokens ($3/$15 per 1M input/output). Exposed via `/api/stats`.

## Performance Targets

- Query latency: <3 seconds end-to-end
- Retrieval precision: >70% relevant chunks in top-5
- Codebase coverage: 100% of files indexed
- Ingestion throughput: 10,000+ LOC in <5 minutes
