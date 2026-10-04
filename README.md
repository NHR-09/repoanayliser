# ARCHITECH — Architectural Recovery & Semantic Synthesis

ARCHITECH is a full-stack tool that analyzes software repositories (GitHub URLs or local paths), builds a knowledge graph of their structure, detects architectural patterns, measures coupling, computes blast radius, and generates LLM-powered explanations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Graph Database | Neo4j |
| In-memory Graph | NetworkX |
| AST Parsing | Tree-sitter (Python, JavaScript, TypeScript/TSX) |
| LLM | Groq (llama-3.3-70b-versatile) |
| Structural Indexing | Graphify CLI (`graphifyy`) |
| Frontend | React |
| HTTP Client | Axios |

---

## Project Structure

```
repoanayliser-main/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── setup.bat
│   ├── .env
│   └── src/
│       ├── config.py
│       ├── analysis_engine.py
│       ├── analysis/
│       │   └── confidence_analyzer.py
│       ├── api/
│       │   └── commit_routes.py
│       ├── graph/
│       │   ├── analyzers.py
│       │   ├── blast_radius.py
│       │   ├── dependency_mapper.py
│       │   ├── function_graph.py
│       │   ├── graph_db.py
│       │   └── version_tracker.py
│       ├── parser/
│       │   ├── repo_loader.py
│       │   └── static_parser.py
│       ├── reasoning/
│       │   └── llm_reasoner.py
│       └── retrieval/
│           ├── graphify_retriever.py
│           └── retrieval_engine.py
└── frontend/
    └── src/
        ├── App.js
        ├── index.js
        ├── App.css
        ├── components/
        │   ├── AnalyzeRepo.js
        │   ├── ArchitectureComparison.js
        │   ├── ArchitectureView.js
        │   ├── BlastRadius.js
        │   ├── ConfidenceReport.js
        │   ├── CouplingAnalysis.js
        │   ├── DependencyGraph.js
        │   ├── FileVersionHistory.js
        │   ├── FunctionAnalysis.js
        │   ├── FunctionGraph.js
        │   ├── Highlighter.js
        │   ├── ImpactAnalysis.js
        │   ├── PatternDetection.js
        │   ├── RepositoryManager.js
        │   └── SnapshotComparison.js
        ├── services/
        │   └── api.js
        └── utils/
            └── formatters.js
```

---

## Backend Files

### `backend/main.py`
The FastAPI application entry point. Defines all REST API routes and wires them to the `AnalysisEngine`. Handles background job execution for long-running analysis tasks (cloning + parsing can take minutes), stores job state in an in-memory `jobs` dict, and exposes endpoints for every feature: analyze, patterns, coupling, blast radius, impact, functions, snapshots, version history, and graph data. Also spawns a subprocess-based OS folder picker dialog via `/browse-folder`.

### `backend/src/config.py`
Loads environment variables from `.env` using Pydantic Settings. Provides a single `settings` object consumed across the backend for Neo4j credentials, Groq API key, and file size limits. Centralizing config here prevents scattered `os.getenv()` calls.

### `backend/src/analysis_engine.py`
The central orchestrator — the most important file in the backend. Coordinates the full analysis pipeline:
1. Clone or load the repo via `RepositoryLoader`
2. Parse files with `StaticParser`
3. Store nodes/edges in Neo4j via `GraphDB`
4. Build an in-memory NetworkX graph via `DependencyMapper`
5. Supplement edges with Graphify's AST-resolved imports
6. Detect patterns and coupling via `PatternDetector` / `CouplingAnalyzer`
7. Generate LLM architecture explanation via `LLMReasoner`
8. Cache everything in Neo4j Snapshot nodes to avoid re-running LLM on unchanged commits

Also manages an LRU in-memory cache (100 entries, thread-safe with `Lock`) for architecture and impact explanations, and handles snapshot comparison, blast radius delegation, and function analysis.

---

### `backend/src/parser/repo_loader.py`
Handles repository ingestion. `clone_repository()` runs `git clone --depth 1` into a local `workspace/` directory. `use_local_path()` validates a local directory without cloning. `scan_files()` recursively finds `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, and `.java` files while excluding `node_modules`, `venv`, `__pycache__`, `.git`, `dist`, and `build` directories.

### `backend/src/parser/static_parser.py`
Performs AST-based static analysis using Tree-sitter. For each file it extracts:
- **Classes** — class definition nodes with name and line number
- **Functions** — function/method definitions with name and line number
- **Imports** — `import` and `from ... import` statements (Python), plus imports and re-exports (JavaScript/TypeScript)
- **Function calls** — all call expressions in the file
- **Function-to-function calls** — which function body contains which calls (used to build the call graph)

Supports Python, JavaScript, TypeScript, and TSX. Java files are scanned for file presence but not deeply parsed (no Tree-sitter Java grammar registered).

---

### `backend/src/graph/graph_db.py`
The Neo4j data access layer. Manages all Cypher queries for creating and querying the knowledge graph. Key responsibilities:
- Creates `File`, `Class`, `Function`, `Module`, `Repository`, `Snapshot`, `Commit`, `Version`, and `User` nodes
- Creates `CONTAINS`, `IMPORTS`, `DEPENDS_ON`, `CALLS`, `CALLS_TRANSITIVE`, `HAS_VERSION`, `VERSION_AT`, `HAS_SNAPSHOT`, `HAS_COMMIT`, `AUTHORED_BY`, and `PREVIOUS_COMMIT` relationships
- Resolves file paths using multi-strategy matching (exact, suffix, normalized forward-slash) to handle cross-platform path differences
- Provides `get_graph_data()` for visualization, `get_all_files()`, `get_all_functions()`, `get_function_callers()`, and `get_affected_files()` for analysis queries

### `backend/src/graph/dependency_mapper.py`
Builds and queries a NetworkX `DiGraph` in memory. During `build_graph()`, it first maps all file stems and relative paths to absolute paths, then creates directed edges for each import that resolves to a known file. Unresolved imports are added as external dependency nodes. Provides `detect_cycles()`, `calculate_fan_in/out()`, and `get_blast_radius()` using NetworkX algorithms. This graph is the primary input to `PatternDetector` and `CouplingAnalyzer`.

### `backend/src/graph/analyzers.py`
Contains two classes:

**`PatternDetector`** — detects 8 architectural patterns from the NetworkX dependency graph (see [How Architectural Patterns Are Found](#how-architectural-patterns-are-found) below).

**`CouplingAnalyzer`** — measures coupling metrics:
- `_find_high_coupling()` — files where fan-in + fan-out exceeds a threshold (default 5)
- `_detect_cycles()` — uses `nx.simple_cycles()` to find circular dependencies
- `_calculate_metrics()` — computes total files, total dependencies, and average coupling ratio
- `compute_structural_risk()` — scores a single file on a 0–100 scale using: `fan_in × 8 + fan_out × 5 + 30 (if in cycle) + bonuses`, capped at 100, then maps to low/medium/high/critical

### `backend/src/graph/blast_radius.py`
Computes the impact of changing a file. Uses Neo4j Cypher path queries (not NetworkX) for accuracy:
- **Direct dependents** — files with a `DEPENDS_ON` edge pointing to the target (1 hop)
- **Indirect dependents** — files reachable via `DEPENDS_ON*2..3` paths (2–3 hops, intentionally limited for relevance)
- **Function impact** — functions defined in the file and their callers via `CALLS` relationships
- **Risk scoring** — different formulas per change type: delete (30 pts per direct import + 20 per function caller), move (8 pts per direct import), modify (5 pts per total affected file)

### `backend/src/graph/version_tracker.py`
SHA-256 based version tracking. Creates `Repository`, `Snapshot`, `Commit`, `Version`, and `User` nodes in Neo4j. Key behaviors:
- `create_repository()` — creates or reuses a repository node; creates a new Snapshot only if no snapshot exists for the current commit hash (prevents duplicates)
- `track_file_version()` — hashes each file and creates a `Version` node linked to the current `Commit`; skips if the same hash already exists at this commit
- `import_git_history()` — runs `git log` to backfill commit history and file versions for up to N commits
- `detect_file_tampering()` — compares the stored SHA-256 hash against the current file content

### `backend/src/graph/function_graph.py`
Builds function-level call graph data for visualization. Queries Neo4j for all `Function` nodes and their `CALLS` relationships (both file→function and function→function). Returns nodes and edges in a format consumable by the frontend graph renderer, with each node tagged as `type: 'function'` or `type: 'file'`.

---

### `backend/src/reasoning/llm_reasoner.py`
Wraps the Groq API (llama-3.3-70b-versatile). Provides:
- `explain_architecture_report()` — single consolidated LLM call that produces three sections (Overview, Modules, Key Files) from patterns, graph context, directory breakdown, code evidence, and optional Graphify structural context. Parses the `## Header` sections from the response.
- `explain_impact_with_graph()` — generates a 2–3 sentence blast radius summary citing actual function/class names from Graphify
- `explain_function()` — explains a function's purpose, usage, and impact from its code, callers, and context
- Uses `temperature=0.3` for deterministic, factual outputs; `max_tokens=1200–2000` depending on the call

---

### `backend/src/retrieval/graphify_retriever.py`
Runs the `graphify` CLI on the repository to produce a `graphify-out/graph.json` knowledge graph, then provides query and lookup methods:
- `index_repo()` — invokes `graphify update <path>` as a subprocess; loads cached `graph.json` if it already exists
- `get_context_for_query()` — scores nodes by matching query tokens against node names, summaries, and file paths; boosts function/class/method nodes by 1.2×
- `get_path_context()` — returns all functions, classes, and imports belonging to a specific file (used to enrich blast radius LLM prompts)
- `get_dependency_edges()` — extracts file-to-file import edges from the graph to supplement the NetworkX dependency graph with Graphify's more accurate AST-resolved imports

### `backend/src/retrieval/retrieval_engine.py`
Combines Graphify structural search with Neo4j dependency context. `retrieve_evidence()` fetches top-K Graphify nodes for a query, then boosts nodes whose files appear in the Neo4j dependency/affected-files sets for a given context file. Returns a ranked evidence list (top 5) formatted for LLM prompts.

---

### `backend/src/analysis/confidence_analyzer.py`
Generates a confidence report for all architectural claims. For each detected pattern it produces:
- A human-readable claim statement
- A confidence score (0.0–1.0) taken directly from `PatternDetector`
- Reasoning text explaining what evidence supports the claim
- A failure scenario describing when the detection could be wrong (e.g., non-standard naming conventions)

Also analyzes coupling confidence (fixed at 0.92 for high-coupling files) and circular dependency confidence (1.0 when a cycle is confirmed by Neo4j traversal).

### `backend/src/api/commit_routes.py`
An `APIRouter` with commit-specific endpoints (`/repository/{repo_id}/commits`, `/commit/{hash}/files`, `/compare/{commit1}/{commit2}`). These routes are defined separately for modularity but the same functionality is also inlined in `main.py`. Depends on the shared `engine.graph_db` instance.

---

## Frontend Files

### `frontend/src/index.js`
React application entry point. Mounts `<App />` into the DOM.

### `frontend/src/App.js`
Root component. Manages global state: active tab, current repository ID/name, and refresh key. Renders the sticky header with the animated "ARCHITECH" scramble effect, the tab navigation bar, and the active tab's component. Passes `repoId` and callbacks down to child components.

### `frontend/src/App.css`
Global CSS variables and base styles (dark theme, color palette, typography, animations like `fade-in`).

### `frontend/src/services/api.js`
Centralized Axios API client. Every backend endpoint has a corresponding function here. Components import from this file rather than constructing URLs directly, making the base URL (`http://localhost:8000`) a single point of change.

### `frontend/src/utils/formatters.js`
Utility functions for display formatting: `formatFilePath()` trims long absolute paths to the last N segments, `getFileName()` extracts just the filename, and `formatEvidenceText()` shortens file paths embedded in LLM-generated text.

---

### Frontend Components

| Component | Purpose |
|---|---|
| `AnalyzeRepo.js` | Input form for GitHub URL or local path; triggers analysis job and polls `/status/{jobId}` until complete |
| `RepositoryManager.js` | Lists all analyzed repositories; allows loading, deleting, and switching between repos |
| `PatternDetection.js` | Displays detected architectural patterns with confidence bars and layer breakdowns |
| `CouplingAnalysis.js` | Shows high-coupling files (fan-in/fan-out), circular dependency cycles, and coupling metrics |
| `BlastRadius.js` | File selector + change type picker; displays direct/indirect dependents and risk score for a simulated change |
| `ImpactAnalysis.js` | Similar to BlastRadius but focused on the LLM-generated impact explanation |
| `ConfidenceReport.js` | Renders the confidence report: each architectural claim with its score, reasoning, and failure scenario |
| `FunctionAnalysis.js` | Lists all functions; clicking one fetches callers, code, and an LLM explanation |
| `ArchitectureView.js` | Displays the three-section LLM architecture report (Overview, Modules, Key Files) with structural stats |
| `ArchitectureComparison.js` | Side-by-side comparison of architecture summaries between two commits |
| `DependencyGraph.js` | Interactive force-directed graph of file-to-file dependencies using a graph visualization library |
| `FunctionGraph.js` | Interactive graph of function call relationships |
| `SnapshotComparison.js` | Lists snapshots for a repo; compares two selected snapshots showing file changes, coupling deltas, and pattern changes |
| `FileVersionHistory.js` | Shows the version history of a specific file across commits |
| `Highlighter.js` | Syntax highlighting utility component used within other views |

---

## How Architectural Patterns Are Found

Pattern detection happens in `PatternDetector` (`backend/src/graph/analyzers.py`) after the dependency graph is fully built. It uses a **multi-signal heuristic approach** — no ML model, no hardcoded rules per project. Each pattern is detected independently.

### Signal Sources (per file/node)

For every node in the NetworkX graph, the detector extracts four types of signals:

1. **Filename stem** — e.g., `controller`, `service`, `repository`, `model`
2. **Parent directory name** — e.g., `controllers/`, `adapters/`, `domain/`
3. **Class and function names** — extracted from the parsed AST and stored as node attributes in the graph
4. **Import statements** — framework imports like `fastapi`, `sqlalchemy`, `celery` are mapped to known layer/role sets

### Node Classification

Before pattern detection, each node is classified into a role using `_classify_node()`:

- **Presentation** — matches keywords like `controller`, `route`, `view`, `api` in filename/directory/symbols, or imports from `flask`, `fastapi`, `django.views`, etc.
- **Data** — matches `repository`, `dao`, `model`, `db`, `schema`, or imports from `sqlalchemy`, `pymongo`, `sqlite3`, etc.
- **Business** — matches `service`, `engine`, `processor`, `pipeline`, or imports from `sklearn`, `torch`, `groq`, etc.

### Pattern Detection Logic

**Layered Architecture**
Counts how many of the three layers (presentation, business, data) have at least one file. Checks for actual inter-layer dependency edges (e.g., presentation → business, business → data). Confidence: 0.85 if all 3 layers exist with valid edges, down to 0.5 for 2 layers without edges.

**MVC**
Separately identifies controllers (route/endpoint keywords + framework imports), models (model/schema/db keywords + ORM imports), and views (view/template/component keywords + render functions). Checks for controller→model dependency edges. Confidence: 0.9 with all three components and edges, 0.5 with only controllers and models.

**Hexagonal (Ports & Adapters)**
Looks for `port`, `interface`, `abstract` in filenames/classes for ports; `adapter`, `impl`, `connector` for adapters; `domain`, `core`, `entities` directories for domain. Checks domain isolation: domain nodes should have fewer than 30% of their outgoing edges pointing outside the domain+ports boundary. Confidence: 0.8 if isolated, 0.5 otherwise.

**Event-Driven**
Identifies event nodes (`event`, `message`, `signal` keywords or messaging library imports like `celery`, `kafka`, `rabbitmq`), publishers (`publish`, `emit`, `dispatch` functions), and subscribers (`subscribe`, `listen`, `consume` functions). Confidence: 0.75 with events + publishers + 2+ subscribers.

**Pipe-Filter**
Detects pipeline/stage nodes (`pipeline`, `stage`, `workflow` keywords or `luigi`, `airflow`, `prefect` imports) and filter/transform nodes (`filter`, `transform`, `mapper`, `reducer`). Checks for chaining edges between pipes and filters. Confidence: 0.8 with chaining and 2+ filters.

**Client-Server**
Identifies server nodes (server-side framework imports: `flask`, `fastapi`, `uvicorn`) and client nodes (HTTP client imports: `requests`, `axios`, `httpx`). Checks for client→server edges. Confidence: 0.8 with edges and 2+ servers.

**Microkernel**
Looks for core/kernel/registry/loader nodes and plugin/extension/middleware nodes. Checks for core↔plugin edges. Requires at least 2 plugins. Confidence: 0.8 with 3+ plugins and edges.

**Microservices**
Identifies service nodes (`service`, `svc` keywords or service discovery imports like `consul`, `grpc`) and gateway nodes. Requires at least 3 independent service nodes. Checks for inter-service edges. Confidence: 0.8 with gateway + inter-service communication.

### Confidence Scores

Each pattern returns a `confidence` value between 0.0 and 1.0. Higher confidence requires more corroborating signals (e.g., all three layers present AND inter-layer edges exist). The `ConfidenceAnalyzer` surfaces these scores to the user along with the reasoning and known failure modes (e.g., "fails if layers are not separated by directory structure or naming conventions").

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Neo4j Desktop (running locally on `bolt://localhost:7687`)
- Git installed and on PATH
- Groq API key

### Backend

```bash
cd backend
pip install -r requirements.txt
# Create .env with:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your_password
# GROQ_API_KEY=your_groq_key
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
```

The app runs at `http://localhost:3000` and connects to the API at `http://localhost:8000`.

---

## Analysis Pipeline (End-to-End)

```
User submits URL/path
        ↓
RepositoryLoader  →  clone or validate local path
        ↓
StaticParser      →  AST parse each .py/.js/.jsx/.ts/.tsx file
                     extract classes, functions, imports, calls
        ↓
GraphDB           →  store File/Class/Function/Module nodes in Neo4j
VersionTracker    →  track SHA-256 file versions per commit
        ↓
DependencyMapper  →  build NetworkX DiGraph from imports
GraphifyRetriever →  run graphify CLI, merge AST-resolved edges
        ↓
GraphDB           →  persist DEPENDS_ON edges to Neo4j
                     create transitive CALLS_TRANSITIVE relationships
        ↓
PatternDetector   →  detect 8 architectural patterns from NetworkX graph
CouplingAnalyzer  →  compute fan-in/out, cycles, risk scores
        ↓
RetrievalEngine   →  fetch top-K Graphify nodes as LLM evidence
LLMReasoner       →  single Groq call → Overview / Modules / Key Files
        ↓
AnalysisEngine    →  cache everything in Neo4j Snapshot node
        ↓
Frontend          →  display patterns, coupling, graphs, LLM report
```
