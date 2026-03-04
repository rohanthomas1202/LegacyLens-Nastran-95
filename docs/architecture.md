# RAG Architecture Document: LegacyLens for NASTRAN-95

## System Overview

LegacyLens is a Retrieval-Augmented Generation (RAG) system that makes the NASA NASTRAN-95 Fortran 77 structural analysis codebase queryable through natural language. The system ingests source code, creates semantic embeddings, and uses vector search combined with LLM generation to answer questions with specific file/line references.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│   ┌──────────┐  ┌──────────────┐  ┌──────────┐                │
│   │  Query    │  │ Code Analysis│  │  Stats   │                │
│   │  Tab      │  │    Tab       │  │  Tab     │                │
│   └────┬─────┘  └──────┬───────┘  └────┬─────┘                │
└────────┼────────────────┼───────────────┼──────────────────────┘
         │                │               │
         ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Ingestion Pipeline                       │   │
│  │  File Discovery → Preprocessor → Chunker → Embedder      │   │
│  └──────────────────────────────────────┬───────────────────┘   │
│                                          │                       │
│  ┌──────────────────────────────────────┐│                       │
│  │             Retrieval Pipeline        ││                       │
│  │  Embed Query → Search → Rerank →     ││                       │
│  │  Generate Answer                      ││                       │
│  └──────────────────┬───────────────────┘│                       │
│                      │                    │                       │
│  ┌──────────────────┐│                    │                       │
│  │  Feature Modules  ││                    │                       │
│  │  • Code Explainer ││                    │                       │
│  │  • Dependency Map ││                    │                       │
│  │  • Pattern Detect ││                    │                       │
│  │  • Doc Generator  ││                    │                       │
│  │  • Business Logic ││                    │                       │
│  └──────────────────┘│                    │                       │
└──────────────────────┼────────────────────┼──────────────────────┘
                       │                    │
              ┌────────▼────────┐  ┌───────▼────────┐
              │   Pinecone      │  │   OpenAI API   │
              │   Vector DB     │  │  (Embeddings)  │
              │   (Search)      │  │                │
              └─────────────────┘  └────────────────┘
                                          │
                                   ┌──────▼────────┐
                                   │  Anthropic API │
                                   │  (Claude LLM)  │
                                   │  (Generation)  │
                                   └────────────────┘
```

## Vector Database Selection

### Choice: Pinecone (Serverless)

**Why Pinecone over alternatives:**

| Criteria | Pinecone | ChromaDB | Weaviate | pgvector |
|----------|----------|----------|----------|----------|
| Managed hosting | Yes (serverless) | No | Cloud option | No |
| Free tier | 100K vectors | N/A (local) | Limited | N/A |
| Metadata filtering | Native | Basic | GraphQL | SQL WHERE |
| Scale handling | Auto | Manual | Manual | Manual |
| Setup complexity | Minimal | Low | Medium | Medium |

**Key factors:**
1. **Zero infrastructure**: Serverless on AWS us-east-1 — no provisioning, no capacity planning
2. **Free tier sufficiency**: 100K vectors covers NASTRAN-95's ~4,000 chunks with room to spare
3. **Metadata filtering**: Native support for filtering by language, file path, chunk type
4. **Cosine similarity**: Built-in distance metric optimized for embedding comparison

**Configuration:**
- Index: `nastran95`
- Dimensions: 1,536
- Metric: Cosine similarity
- Cloud: AWS us-east-1 (serverless)
- Spec: Serverless (auto-scaling)

## Embedding Strategy

### Choice: OpenAI text-embedding-3-small

**Model comparison:**

| Model | Dimensions | Cost/1M tokens | MTEB Score |
|-------|-----------|----------------|------------|
| text-embedding-3-small | 1,536 | $0.02 | 62.3% |
| text-embedding-3-large | 3,072 | $0.13 | 64.6% |
| text-embedding-ada-002 | 1,536 | $0.10 | 61.0% |

**Rationale**: At $0.02/1M tokens, text-embedding-3-small costs 6.5x less than the large model with only a 2.3% quality difference. For code search where exact keyword matches supplement semantic similarity, this trade-off is worthwhile.

**Implementation details:**
- **Metadata header prepended**: `[FORTRAN SUBROUTINE 'SDR2A' in bd/sdr2a.f:1-45]` — provides structured context to the embedding model
- **Batch size**: 100 chunks per API call to balance throughput and rate limits
- **Token limit**: Chunks truncated to 8,000 tokens (model max is 8,191) with iterative line removal
- **Rate limit handling**: Exponential backoff (2^attempt + 1 seconds) with 0.5s delay between batches

### Actual Ingestion Metrics

| Metric | Value |
|--------|-------|
| Files processed | 1,846 |
| Lines of code | 418,349 |
| Chunks created | 4,040 |
| Total embedding tokens | 4,680,546 |
| Embedding cost | ~$0.094 |
| Ingestion time | ~4 minutes |

## Chunking Approach

### Fortran 77 Syntax-Aware Chunking

The chunker leverages Fortran 77's fixed-form format for reliable boundary detection:

```
Columns 1-5:  Statement label (line number)
Column 6:     Continuation character (non-blank, non-zero)
Columns 7-72: Source code
Columns 73-80: Sequence numbers (stripped during preprocessing)
Column 1:     C or * marks comment line
```

**Boundary detection rules:**
1. Scan columns 7+ for keywords: `SUBROUTINE`, `FUNCTION`, `PROGRAM`, `BLOCK DATA`, `ENTRY`
2. Track bare `END` statements as routine terminators
3. Group continuation lines (non-blank/non-zero in column 6) with their parent statement
4. Skip comment lines (C/\*/! in column 1) for boundary detection but include in chunk content
5. Extract dependencies: `CALL` targets, `COMMON` block names, `INCLUDE` file references

**Chunk data model:**
```python
@dataclass
class Chunk:
    content: str           # Full source code of the chunk
    file_path: str         # Relative path to source file
    start_line: int        # First line number (1-based)
    end_line: int          # Last line number
    chunk_type: str        # subroutine|function|program|block-data|entry|fixed-size
    name: str              # Routine name (e.g., "SDR2A")
    language: str          # fortran|c
    dependencies: list     # ["CALL:TARGET", "COMMON:BLOCK", "INCLUDE:FILE"]
```

**Fallback**: Files without detectable routine boundaries use fixed-size chunking (40 lines with 10-line overlap).

### Why not AST-based parsing?

No production-quality Fortran 77 parser exists for Python. The fixed-form format makes regex-based parsing reliable — column positions are deterministic, not context-dependent. Our approach correctly identifies 100% of SUBROUTINE/FUNCTION boundaries in NASTRAN-95.

## Retrieval Pipeline

### Flow

```
1. User query → OpenAI embedding (same model as ingestion)
2. Embedded query → Pinecone top-k search (default k=5)
3. Raw results → Keyword reranking
4. Reranked results → Claude Sonnet generation
5. Generated answer + sources → User
```

### Reranking Strategy

Lightweight keyword-based reranking instead of a cross-encoder model:

| Boost Type | Amount | Condition |
|-----------|--------|-----------|
| Name match | +0.10 | Query keyword appears in chunk name |
| Content match | +0.02 | Query keyword appears in content (max 5 matches = +0.10) |
| Score cap | 1.00 | Maximum final score |

**Why not a cross-encoder?** Cross-encoders (e.g., ms-marco-MiniLM) add latency and complexity. For code search, exact name matching is the highest-value signal — users often know the routine name they're looking for. The keyword boost addresses the most common failure mode (exact match ranked below semantic match) at zero additional cost.

### Search Parameters

- **Top-k**: 5 (configurable per request)
- **Filters**: Optional language and file_path filtering via Pinecone metadata
- **Similarity metric**: Cosine similarity (range 0-1)

## LLM Generation

### Choice: Claude Sonnet (claude-sonnet-4-20250514)

**System prompt includes NASTRAN-specific context:**
- COMMON blocks for shared data between subroutines
- DMAP (Direct Matrix Abstraction Program) executive control
- GINO (General Input/Output) system for matrix I/O
- Open Core memory management architecture
- Fortran 77 fixed-form conventions

**Generation constraints:**
- Max output tokens: 2,000
- Required: File:line citations for every code reference
- Temperature: Default (balanced creativity/accuracy)

## Failure Modes and Mitigations

| Failure Mode | Impact | Mitigation |
|-------------|--------|------------|
| No relevant results | User gets unhelpful answer | Return empty results with suggestion to rephrase |
| Rate limit during ingestion | Ingestion stalls | Exponential backoff with retry (up to 5 attempts) |
| Token limit exceeded | Embedding fails | Iterative truncation removing 20% of lines until under 8,000 tokens |
| Encoding errors | File unreadable | chardet detection with UTF-8 fallback |
| Large routines (>1000 lines) | Poor embedding quality | Token truncation preserves first 8,000 tokens (function signature + early logic) |
| Ambiguous queries | Low-quality answer | System prompt instructs Claude to note ambiguity |
| Pinecone unavailable | Search fails | Error returned to user with appropriate HTTP status |

## Performance Results

| Metric | Target | Actual |
|--------|--------|--------|
| Query latency (search only) | <1s | ~500ms |
| Query latency (with LLM) | <3s | ~2-3s |
| Ingestion throughput | 10K LOC / 5 min | 418K LOC / 4 min |
| Codebase coverage | 100% files | 100% (1,846 files) |
| Test pass rate | 100% | 100% (64/64) |

## Code Understanding Features

Five features beyond basic search:

1. **Code Explainer**: Retrieves entity chunks, sends to Claude for plain-English explanation
2. **Dependency Mapper**: Extracts CALL/COMMON/INCLUDE from chunk metadata, finds reverse callers
3. **Pattern Detector**: Uses entity's code as embedding query to find structurally similar code
4. **Documentation Generator**: Claude generates structured docs (Overview, Parameters, Logic Flow, Dependencies)
5. **Business Logic Extractor**: Claude extracts IF conditions, validations, calculations as structured rules
