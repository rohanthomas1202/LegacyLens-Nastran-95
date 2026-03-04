# Pre-Search Document: LegacyLens for NASTRAN-95

## Phase 1: Constraints

### Scale
- **Codebase size**: NASA NASTRAN-95 — 1,846 Fortran 77 files, 418,349 lines of code
- **Expected chunks**: ~4,000 code chunks after syntax-aware parsing
- **Embedding dimensions**: 1,536 per vector
- **Storage**: ~24MB of vector data in Pinecone

### Budget
- **Development**: Free tier services where possible
- **Pinecone**: Free starter plan (serverless, 100K vectors)
- **OpenAI embeddings**: ~$0.10 for full ingestion (~4.7M tokens at $0.02/1M)
- **Claude Sonnet**: ~$0.05 per query ($3/$15 per 1M input/output tokens)
- **Target**: Keep total dev cost under $5

### Timeline
- Single-week sprint
- MVP: ingestion + search + query UI in 3 days
- Features + polish in remaining days

### Data Sensitivity
- NASTRAN-95 is public domain (NASA open source)
- No PII or sensitive data concerns
- API keys stored in `.env`, never committed

### Skills
- Python/FastAPI for backend
- React 19/Vite for frontend
- OpenAI and Anthropic API experience
- Vector database fundamentals

---

## Phase 2: Architecture Discovery

### Vector Database Selection

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Pinecone** | Managed, free tier, metadata filtering, serverless | Vendor lock-in | **Selected** |
| ChromaDB | Open source, local | No managed hosting, limited scale | Rejected |
| Weaviate | Feature-rich, hybrid search | Complex setup, overkill for project | Rejected |
| pgvector | Familiar SQL, self-hosted | Requires Postgres hosting, no free managed tier | Rejected |

**Rationale**: Pinecone's serverless free tier provides 100K vectors with zero infrastructure management. Metadata filtering enables language/file-based search narrowing. The managed service eliminates operational complexity.

### Embedding Strategy

| Option | Dimensions | Cost/1M tokens | Quality | Decision |
|--------|-----------|-----------------|---------|----------|
| **text-embedding-3-small** | 1,536 | $0.02 | Good | **Selected** |
| text-embedding-3-large | 3,072 | $0.13 | Better | Rejected (cost) |
| text-embedding-ada-002 | 1,536 | $0.10 | Good | Rejected (older, more expensive) |

**Rationale**: text-embedding-3-small offers the best cost/quality ratio. At $0.02/1M tokens, full ingestion of NASTRAN-95 costs ~$0.10. The 1,536 dimensions provide sufficient semantic resolution for code search.

### Chunking Approach

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Syntax-aware** | Preserves routine boundaries, meaningful units | Language-specific parser needed | **Selected** |
| Fixed-size | Simple, universal | Breaks mid-function, loses context | Fallback only |
| AST-based | Precise boundaries | No Fortran 77 AST parser available | Not feasible |

**Rationale**: Fortran 77's fixed-form format (columns 1-72, continuation markers, C/\* comments) enables reliable regex-based boundary detection without a full parser. SUBROUTINE/FUNCTION/PROGRAM/BLOCK DATA keywords in columns 7+ reliably mark routine boundaries. Fixed-size chunking serves as fallback for files without clear routine structure.

### Retrieval Pipeline

```
User Query → Embed (OpenAI) → Vector Search (Pinecone top-k) → Rerank (keyword boost) → Generate (Claude Sonnet)
```

**Reranking strategy**: Lightweight keyword-based boosting rather than a cross-encoder model. Boosts chunks where the query terms appear in the routine name (+0.1) or content (+0.02 per match, capped). This avoids additional API costs while improving precision for exact name lookups.

### LLM Selection

| Option | Input $/1M | Output $/1M | Quality | Decision |
|--------|-----------|-------------|---------|----------|
| **Claude Sonnet** | $3.00 | $15.00 | Excellent | **Selected** |
| GPT-4o | $2.50 | $10.00 | Excellent | Rejected (already using OpenAI for embeddings, want diversity) |
| Claude Haiku | $0.25 | $1.25 | Good | Rejected (lower quality for code explanation) |

**Rationale**: Claude Sonnet provides excellent code understanding at reasonable cost. Using Claude for generation and OpenAI for embeddings provides vendor diversity and leverages each provider's strengths.

### Web Framework

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **FastAPI** | Async, auto-docs, type hints, fast | — | **Selected** |
| Flask | Simple, familiar | No async, manual docs | Rejected |
| Django | Full-featured | Too heavy for API service | Rejected |

---

## Phase 3: Refinement

### Failure Modes

1. **No relevant results**: Query doesn't match any code semantically
   - Mitigation: Return empty results with helpful message, suggest alternative queries

2. **Ambiguous queries**: "How does it work?" without specific context
   - Mitigation: System prompt instructs LLM to ask for clarification in response

3. **Large functions**: Some NASTRAN routines exceed 1000 lines
   - Mitigation: Token truncation at 8,000 tokens before embedding, fixed-size fallback for oversized chunks

4. **Rate limits**: OpenAI rate limits during batch ingestion
   - Mitigation: Exponential backoff with retry, 0.5s delay between batches

5. **Encoding issues**: Legacy Fortran files may use non-UTF-8 encoding
   - Mitigation: chardet-based encoding detection with UTF-8 fallback

### Evaluation Metrics

- **Retrieval precision@5**: Target >70% relevant chunks in top-5 results
- **Query latency**: Target <3 seconds end-to-end
- **Coverage**: 100% of source files indexed
- **Ingestion throughput**: 10,000+ LOC in <5 minutes

### Performance Considerations

- Batch embedding (100 chunks per API call) to minimize HTTP overhead
- Pinecone serverless scales automatically — no capacity planning needed
- Frontend served as static files from FastAPI — single deployment unit
- Cost tracking enables monitoring and budget alerts

### Observability

- Structured logging to `logs/nastran95.log`
- Cost tracking persisted to `logs/costs.json`
- `/api/stats` endpoint exposes runtime metrics
- Query timing measured and returned in API responses
