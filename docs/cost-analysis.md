# AI Cost Analysis: LegacyLens for NASTRAN-95

## Development Costs (Actual)

### Ingestion (One-Time)

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| OpenAI text-embedding-3-small | 4,680,546 | $0.02 / 1M tokens | $0.094 |
| **Total Ingestion** | | | **$0.094** |

### Development Queries (Testing)

| Component | Est. Queries | Tokens/Query | Rate | Cost |
|-----------|-------------|-------------|------|------|
| Embedding (query) | ~50 | ~50 tokens | $0.02/1M | $0.00005 |
| Claude Sonnet input | ~50 | ~3,000 tokens | $3.00/1M | $0.45 |
| Claude Sonnet output | ~50 | ~500 tokens | $15.00/1M | $0.375 |
| **Total Dev Queries** | | | | **~$0.83** |

### Pinecone

| Item | Value | Cost |
|------|-------|------|
| Vectors stored | 4,040 | Free tier (100K limit) |
| Monthly queries (dev) | ~200 | Free tier |
| **Total Pinecone** | | **$0.00** |

### Total Development Cost

| Category | Cost |
|----------|------|
| Ingestion | $0.094 |
| Dev queries | ~$0.83 |
| Pinecone hosting | $0.00 |
| Railway hosting | Free tier |
| **Total** | **~$0.92** |

---

## Production Cost Projections

### Assumptions

- Average query: ~50 embedding tokens, ~3,000 LLM input tokens, ~500 LLM output tokens
- Queries per user per day: 5
- Re-ingestion: once per month (codebase doesn't change for NASTRAN-95, but for other legacy codebases)
- Pinecone free tier covers up to 100K vectors

### Per-Query Cost Breakdown

| Component | Tokens | Rate | Cost/Query |
|-----------|--------|------|-----------|
| Query embedding | 50 | $0.02/1M | $0.000001 |
| Claude input | 3,000 | $3.00/1M | $0.009 |
| Claude output | 500 | $15.00/1M | $0.0075 |
| Pinecone search | 1 query | Free tier | $0.00 |
| **Total per query** | | | **$0.0165** |

### Monthly Cost by User Scale

| Users | Queries/Month | Embedding | Claude Input | Claude Output | Pinecone | Total/Month |
|-------|--------------|-----------|-------------|--------------|----------|------------|
| 10 | 1,500 | $0.00 | $13.50 | $11.25 | $0 (free) | **$24.75** |
| 100 | 15,000 | $0.02 | $135.00 | $112.50 | $0 (free) | **$247.52** |
| 1,000 | 150,000 | $0.15 | $1,350 | $1,125 | $70* | **$2,545** |
| 10,000 | 1,500,000 | $1.50 | $13,500 | $11,250 | $70* | **$24,822** |

*\*Pinecone Standard plan at ~$70/month for >100K vectors or high query volume*

### Annual Cost Projections

| Users | Monthly | Annual | Annual + 20% Buffer |
|-------|---------|--------|---------------------|
| 10 | $24.75 | $297 | **$356** |
| 100 | $247.52 | $2,970 | **$3,564** |
| 1,000 | $2,545 | $30,540 | **$36,648** |
| 10,000 | $24,822 | $297,864 | **$357,437** |

---

## Cost Optimization Strategies

### Immediate (No Code Changes)

1. **Caching**: Cache frequent queries — many users ask similar questions about main entry points, key subroutines
   - Expected savings: 30-50% reduction in LLM calls
   - Implementation: Redis or in-memory LRU cache with 1-hour TTL

2. **Reduce top-k**: Decrease from 5 to 3 results for simple queries
   - Expected savings: 40% reduction in LLM input tokens
   - Trade-off: Slightly lower answer quality for complex queries

### Medium-Term

3. **Switch to Claude Haiku for simple queries**: Route straightforward lookups to Haiku ($0.25/$1.25 per 1M)
   - Expected savings: 85% reduction in LLM costs for ~60% of queries
   - Implementation: Query classifier to route simple vs. complex

4. **Embedding caching**: Cache query embeddings for repeated/similar queries
   - Expected savings: Minimal (embeddings are cheap), but reduces latency

### Long-Term

5. **Self-hosted embedding model**: Replace OpenAI with a local model (e.g., sentence-transformers)
   - Expected savings: 100% embedding cost elimination
   - Trade-off: Requires GPU hosting, maintenance

6. **Self-hosted LLM**: Use quantized open-source model (e.g., CodeLlama)
   - Expected savings: 90%+ LLM cost elimination
   - Trade-off: Lower quality, significant infrastructure requirements

---

## Cost per Feature

| Feature | LLM Calls | Avg Cost/Use |
|---------|----------|-------------|
| Query (search + answer) | 1 | $0.0165 |
| Search only | 0 | $0.000001 |
| Code Explain | 1 | $0.0165 |
| Dependency Map | 0 | $0.000001 |
| Pattern Detection | 0 | $0.000001 |
| Doc Generation | 1 | $0.0165 |
| Business Rules | 1 | $0.0165 |

Features without LLM calls (search, dependency map, pattern detection) are essentially free, costing only the embedding query ($0.000001).

---

## Budget Monitoring

The system tracks costs in real-time via `CostTracker` (`backend/utils/logger.py`):
- Persists to `logs/costs.json`
- Tracks: embedding tokens, LLM input/output tokens, query count, ingestion count
- Exposed via `/api/stats` endpoint
- Enables setting alerts before costs exceed budget thresholds
