# LegacyLens Demo Video Script

**Target length**: 3-5 minutes

---

## Opening (15 seconds)

> "Hi, I'm Rohan. I built LegacyLens — a RAG-powered system that makes NASA's NASTRAN-95 codebase queryable through natural language. NASTRAN-95 is a structural analysis program written in Fortran 77 with over 418,000 lines of code across 1,800+ files. Let me show you how it works."

---

## 1. Show the App (10 seconds)

- Open the deployed app in browser
- Show the clean dark UI with the three tabs: Query, Code Analysis, Stats
- Point out the search bar and sample query buttons

---

## 2. Natural Language Query (60 seconds)

**Click the sample query**: "Where is the main entry point of this program?"

> "I can ask natural language questions. Here I'm asking where the main entry point is. The system embeds my query, searches Pinecone for the most relevant code chunks, reranks them, and sends the top results to Claude for answer generation."

- **Show the AI answer** — it should reference NASTRN as the main program
- **Show the source cards** — point out the file path, line numbers, relevance score
- **Expand a source** — show the syntax-highlighted Fortran code with line numbers

> "Each source shows the actual code with syntax highlighting and line numbers. The relevance score tells me how confident the system is."

**Click "View File"** on one of the sources:

> "I can drill down to see the full file. The relevant section is highlighted in blue so I can see the context around it."

- Close the modal

---

## 3. Second Query (30 seconds)

**Type**: "What subroutines handle error checking?"

> "Let me search for error handling. The system finds ERRMKN, MACHCK, and other error-related subroutines. Notice how it pulls from different files across the codebase — this is the power of semantic search over simple text search."

- Show the results briefly

---

## 4. Third Query (30 seconds)

**Type**: "How does stiffness matrix assembly work?"

> "I can ask domain-specific questions too. Here I'm asking about stiffness matrix assembly — a core concept in structural analysis. The system finds relevant subroutines like DPSE4 and explains how they work together."

---

## 5. Code Analysis Tab (90 seconds)

**Switch to the Code Analysis tab**

> "Beyond search, LegacyLens has five code understanding features. Let me show them."

**Type entity name**: `NASTRN`

### Explain Code
- Click "Explain Code"
> "The Explain feature gives me a plain-English explanation of what this subroutine does, with references to the source."

### Map Dependencies
- Click "Map Dependencies"
> "Dependency mapping shows what this routine calls and what calls it. You can see the CALL targets and COMMON blocks it uses."

### Find Patterns
- Click "Find Patterns"
> "Pattern detection finds structurally similar code elsewhere in the codebase, with similarity percentages."

### Generate Docs
- Click "Generate Docs"
> "The documentation generator creates structured docs — overview, parameters, logic flow, dependencies — all auto-generated from the source code."

### Extract Rules
- Click "Extract Rules"
> "Finally, business rule extraction pulls out the IF conditions, validations, and calculations as structured rules."

---

## 6. Stats Tab (15 seconds)

**Switch to Stats tab**

> "The Stats tab shows real-time metrics — total vectors indexed, query count, and a full cost breakdown. You can see the total API cost is under a dollar for the entire project."

---

## 7. Architecture Overview (30 seconds)

> "Under the hood, the system uses a two-pipeline architecture. The ingestion pipeline scans the Fortran 77 source files, uses a syntax-aware chunker that understands column-based formatting and routine boundaries, embeds the chunks with OpenAI, and stores them in Pinecone. The retrieval pipeline embeds the query, searches Pinecone, reranks with keyword boosting, and generates answers with Claude Sonnet."

---

## 8. Closing (15 seconds)

> "LegacyLens makes legacy codebases accessible to developers who may not know Fortran 77. It's deployed on Railway, tested with 64 unit tests, and the full source is on GitHub. Thanks for watching!"

---

## Suggested Queries for Demo

These produce good, demonstrable results:

| Query | Why It's Good |
|-------|--------------|
| "Where is the main entry point of this program?" | Clean answer pointing to NASTRN |
| "What subroutines handle error checking?" | Shows ERRMKN, MACHCK — multiple relevant results |
| "How does stiffness matrix assembly work?" | Domain-specific, shows structural analysis knowledge |
| "Find all error handling patterns" | Broader search, shows breadth of retrieval |
| "What are the dependencies of the NASTRN module?" | Shows dependency awareness |
| "Explain the GINO I/O system" | Tests NASTRAN-specific knowledge from system prompt |

## Suggested Entity Names for Code Analysis

| Entity | Why |
|--------|-----|
| `NASTRN` | Main program — good for all 5 features |
| `SDR2A` | Well-known subroutine with clear dependencies |
| `ERRMKN` | Error checking — clear business logic |
| `DPSE4` | Matrix operations — good for patterns |

## Tips

- Use the deployed Railway URL, not localhost
- Have the queries ready to paste so you don't waste time typing
- Pause briefly on each result so viewers can see the output
- If a query takes a few seconds, narrate what's happening ("The system is searching across 4,000 code chunks...")
