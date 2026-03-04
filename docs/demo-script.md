# CODEX-95 Demo Video Script

**Target length**: 3-5 minutes

---

## Opening (15 seconds)

> "Hi, I'm Rohan. I built CODEX-95 — an AI-powered code intelligence tool for NASA's NASTRAN-95 codebase. NASTRAN-95 is a structural analysis program written in Fortran 77 with over 418,000 lines of code across 1,800+ files. Let me show you what it can do."

---

## 1. Show the App (10 seconds)

- Open the deployed app in browser
- Show the cyberpunk-themed UI with four tabs: Query, Analysis, Graph, Dashboard
- Point out the cursor glow effect, glass navigation, and the live status indicator

---

## 2. Natural Language Query (60 seconds)

**Click the sample query**: "Where is the main entry point of this program?"

> "I can ask natural language questions and get streaming AI-generated answers. The system embeds my query, searches Pinecone for the most relevant code chunks, reranks them, and streams the answer from Claude in real-time."

- **Show the streaming answer** — tokens appear as they're generated
- **Show the source cards** — point out the file path, line numbers, relevance score
- **Expand a source** — show the syntax-highlighted Fortran code with line numbers

> "Each source shows the actual code with syntax highlighting and line numbers. The relevance score tells me how confident the system is."

**Click "View File"** on one of the sources:

> "I can drill down to see the full file. The relevant section is highlighted so I can see the context around it."

- Close the modal

---

## 3. Second Query (30 seconds)

**Type**: "How does stiffness matrix assembly work?"

> "I can ask domain-specific questions too. Here I'm asking about stiffness matrix assembly — a core concept in structural analysis. The system finds relevant subroutines and explains how they work together, citing specific file and line references."

---

## 4. Code Analysis Tab (90 seconds)

**Switch to the Analysis tab**

> "Beyond search, CODEX-95 has a suite of code understanding features. Let me show them."

**Type entity name using autocomplete**: `NASTRN`

> "The autocomplete searches across all indexed routines in the graph. Let me start with the main program."

### Explain Code
- Click "Explain Code"
> "The Explain feature gives me a plain-English explanation of what this subroutine does, with references to the source."

### Map Dependencies
- Click "Map Dependencies"
> "Dependency mapping shows what this routine calls and what calls it — the CALL targets and COMMON blocks."

### Modernize Code
- Select "Python" from the language dropdown, click "Modernize Code"
> "This is the code modernization feature. It translates the Fortran 77 code to a modern language — here I picked Python. The side-by-side view shows the original on the left and the translation on the right, with migration notes explaining the idiom mappings, type conversions, and control flow changes."

- Show the modal briefly, point out the pane headers and migration notes
- Close the modal

### Generate Docs
- Click "Generate Docs"
> "The documentation generator creates structured docs — overview, parameters, logic flow, dependencies — all auto-generated from the source code."

### Dead Code Detection
- Click "Detect Dead Code"
> "Dead code detection analyzes the call graph to find routines with zero incoming calls — potentially unreachable code."

---

## 5. Graph Tab (45 seconds)

**Switch to the Graph tab**

> "The interactive dependency graph visualizes the call relationships in the codebase. Each node is a subroutine or function, and edges show call dependencies."

- Show the 2D graph, click on a node to recenter
- Toggle to 3D mode

> "I can switch to a 3D view that auto-rotates, giving a spatial perspective of the code architecture. Ctrl+scroll to zoom, right-click to pan."

### Code Flow Tracer
- Enter `NASTRN` as source, `MESAGE` as target
- Click "Trace Path"

> "The code flow tracer finds the shortest call path between any two routines. Here it shows how execution flows from the main program NASTRN to the message handler MESAGE."

---

## 6. Dashboard Tab (15 seconds)

**Switch to Dashboard tab**

> "The Dashboard shows real-time metrics — total vectors indexed, query count, cost breakdown, and a live activity sparkline. The total API cost for the entire project is under a dollar."

---

## 7. Architecture Overview (30 seconds)

> "Under the hood, CODEX-95 uses a two-pipeline architecture. The ingestion pipeline scans the Fortran 77 source files with a syntax-aware chunker that understands column-based formatting and routine boundaries, embeds the chunks with OpenAI, and stores them in Pinecone. The retrieval pipeline embeds the query, searches Pinecone, reranks with keyword boosting, and generates streaming answers with Claude Sonnet. On top of this, there's a static call graph built from the chunk dependency metadata that powers the graph visualization, flow tracing, and dead code detection."

---

## 8. Closing (15 seconds)

> "CODEX-95 makes legacy codebases accessible to developers who may not know Fortran 77. It's deployed on Railway, and the full source is on GitHub. Thanks for watching!"

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
| `NASTRN` | Main program — good for all features including modernize |
| `SDR2A` | Well-known subroutine with clear dependencies |
| `ERRMKN` | Error checking — clear business logic |
| `DPSE4` | Matrix operations — good for patterns |

## Suggested Flow Tracer Paths

| Source → Target | Why |
|----------------|-----|
| `NASTRN` → `MESAGE` | Main program to message handler |
| `NASTRN` → `BTSTRP` | Main program to bootstrap |
| `NASTRN` → `DBMINT` | Main program to database init |

## Tips

- Use the deployed Railway URL, not localhost
- Have the queries ready to paste so you don't waste time typing
- Pause briefly on each result so viewers can see the output
- If a query takes a few seconds, narrate what's happening ("The system is searching across 4,000 code chunks and streaming the answer in real-time...")
- For the modernize feature, Python produces the most readable output
- Show the 3D graph briefly — it's visually impressive but don't spend too long
