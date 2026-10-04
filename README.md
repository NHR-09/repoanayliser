# ARCHITECH 📐

### *Autonomous Architectural Recovery, Dependency Intelligence & Semantic Codebase Synthesis*

[![Neo4j](https://img.shields.io/badge/Graph_Database-Neo4j_5.x-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![FastAPI](https://img.shields.io/badge/API_Framework-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tree-sitter](https://img.shields.io/badge/AST_Parsing-Tree--sitter-1e293b?style=for-the-badge)](https://tree-sitter.github.io/tree-sitter/)
[![NetworkX](https://img.shields.io/badge/Graph_Algorithms-NetworkX-38bdf8?style=for-the-badge)](https://networkx.org/)
[![Groq](https://img.shields.io/badge/LLM_Reasoning-Groq_Llama_3.3_70B-f97316?style=for-the-badge)](https://groq.com/)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_D3.js-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)

---

## 📌 Problem Statement

> Modern software systems contain thousands of evolving source files, making architecture difficult to understand and maintain. Over time, dependencies grow, module boundaries blur, and architectural intent becomes undocumented.
>
> Developers lack effective tools to visualize system architecture, identify subsystems and dependencies, detect circular coupling, and predict the impact of code changes.
>
> This results in **slow onboarding, risky refactoring, rising technical debt, and architectural erosion**.
>
> The need is for a system that automatically analyzes a codebase, visualizes its architecture and dependencies, and highlights structural risks to improve codebase comprehension and enable safer, more efficient development.

---

## 💡 System Overview

**ARCHITECH** is an automated architectural intelligence engine that extracts, visualizes, reasons about, and tracks software architecture across time.

By unifying **Abstract Syntax Tree (AST) parsing via Tree-sitter**, **dual-layer graph databases (Neo4j & NetworkX)**, **heuristic pattern detection algorithms**, and **LLM-driven semantic synthesis (Groq Llama-3.3-70B)**, ARCHITECH transforms flat repositories into queryable, multi-dimensional knowledge graphs.

```
                           ┌─────────────────────────────────────────┐
                           │   Repository Input (GitHub / Local)     │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │ Static AST Extraction (Tree-sitter)     │
                           │ Classes, Functions, Imports, OOP Calls  │
                           └────────────────────┬────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
┌─────────────────────────────────┐                           ┌─────────────────────────────────┐
│ In-Memory DiGraph (NetworkX)    │                           │ Graph Database (Neo4j)          │
│ • Johnson's Cycle Detection     │                           │ • Persistent Node/Edge Topology │
│ • Multi-Signal Pattern Analysis │                           │ • Transitive Call Calculation   │
│ • Fan-In / Fan-Out Metrics      │                           │ • Cryptographic Snapshot Lineage│
└────────────────┬────────────────┘                           └────────────────┬────────────────┘
                 │                                                             │
                 └──────────────────────────────┬──────────────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │ Structural Context & Retrieval Engine   │
                           │ Graphify AST Indexing + README Context  │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │ Semantic LLM Synthesis (Groq Llama 3.3) │
                           │ Macro, Meso & Micro Architecture Review │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │ Interactive UI (React + D3.js Force)    │
                           │ Dynamic Blast Radius, Coupling, Graphs  │
                           └─────────────────────────────────────────┘
```

---

## 🔬 Core Architectural Subsystems & Working Details

### 1. Static AST Ingestion & OOP-Aware Parsing (`StaticParser`)
* **Grammar Parsing Engines:** Utilizes native Tree-sitter parsers (`tree-sitter-python`, `tree-sitter-javascript`) to generate concrete syntax trees (CST/AST).
* **Two-Pass Ingestion Protocol:**
  * **Pass 1 (Node Extraction & Structural Typing):** Extracts `class_definition`, `function_definition`, `import_statement`, and inspects `__init__` constructor assignments (`self.X = ClassName()`) to infer object-oriented dependency injection. File nodes are assigned content SHA-256 hashes.
  * **Pass 2 (Cross-File Call Graph & OOP Resolution):** Recursively traverses function bodies to extract caller-callee bindings (`f2f`). Resolves indirect method dispatch (`self.target_service.execute()`) by matching receiver types against known class method definitions across the codebase.

---

### 2. Dual-Layer Graph Architecture (`GraphDB` & `DependencyMapper`)
ARCHITECH pairs an in-memory graph engine with a persistent graph database for distinct computational advantages:

| Subsystem | Technology | Primary Responsibilities |
|---|---|---|
| **Persistent Knowledge Graph** | **Neo4j** (Cypher) | Storage of all entities (`Repository`, `Snapshot`, `Commit`, `Version`, `File`, `Class`, `Function`, `Module`), multi-hop path traversals (`[:DEPENDS_ON*2..3]`), transitive call chain generation (`[:CALLS_TRANSITIVE]`), and cross-commit snapshot querying. |
| **Algorithmic Graph Engine** | **NetworkX** (`DiGraph`) | High-speed in-memory structural algorithms: Johnson's cycle detection (`nx.simple_cycles`), strongly connected components (`nx.strongly_connected_components`), instant in/out-degree calculations, and heuristic classification. |

#### Neo4j Graph Schema Taxonomy
* **Nodes:** `(:Repository)`, `(:Snapshot)`, `(:Commit)`, `(:User)`, `(:File)`, `(:Class)`, `(:Function)`, `(:Module)`, `(:Version)`
* **Relationships:**
  * `(:Repository)-[:CONTAINS]->(:File)`
  * `(:Repository)-[:HAS_SNAPSHOT]->(:Snapshot)`
  * `(:Repository)-[:HAS_COMMIT]->(:Commit)-[:AUTHORED_BY]->(:User)`
  * `(:File)-[:CONTAINS]->(:Class|:Function)`
  * `(:File)-[:IMPORTS]->(:Module)`
  * `(:File)-[:DEPENDS_ON]->(:File)`
  * `(:File|:Function)-[:CALLS]->(:Function)`
  * `(:Function)-[:CALLS_TRANSITIVE]->(:Function)`
  * `(:File)-[:HAS_VERSION]->(:Version)-[:VERSION_AT]->(:Commit)`
  * `(:Version)-[:PREVIOUS_VERSION]->(:Version)`
  * `(:Commit)-[:PREVIOUS_COMMIT]->(:Commit)`

---

### 3. Multi-Signal Architectural Pattern Detection (`PatternDetector`)
Pattern detection uses a multi-signal heuristic classifier evaluating file paths, directory conventions, class/function AST names, and framework import signatures:

```
                                  Classification Signals
   ┌───────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
   │    Filename Stem      │   Directory Name     │  AST Class/Func Name │    Framework Imports │
   └───────────┬───────────┴──────────┬───────────┴──────────┬───────────┴──────────┬───────────┘
               │                      │                      │                      │
               └──────────────────────┼──────────────────────┼──────────────────────┘
                                      ▼
                        Node Role Classification Engine
                     (Presentation | Business | Data Layer)
                                      │
                                      ▼
                        Pattern Heuristic Rules & Scoring
```

1. **Layered (N-tier):** Verifies physical or directory separation across Presentation (`routes`, `api`, `controllers`), Business (`services`, `core`, `engine`), and Data (`models`, `repositories`, `db`). Computes inter-layer dependency validation ($P \rightarrow B$, $B \rightarrow D$).
2. **Model-View-Controller (MVC):** Verifies controller routing definitions, model schemas/entities, and view template components. Validates controller-to-model dependency links ($C \rightarrow M$).
3. **Hexagonal (Ports & Adapters):** Identifies boundary interfaces/ports, infrastructure adapters, and domain core modules. Checks domain isolation: verifies domain nodes have $< 30\%$ external coupling.
4. **Event-Driven:** Detects event definitions, publishers (`emit`, `dispatch`), subscribers (`listen`, `consume`), and broker integrations (`celery`, `kafka`, `rabbitmq`, `pika`).
5. **Pipe & Filter:** Detects data processing pipelines, transformation stages, and filter chains. Checks for sequential execution edges.
6. **Client-Server:** Identifies server APIs (`fastapi`, `flask`, `express`) versus client HTTP consumers (`axios`, `fetch`, `requests`, `httpx`).
7. **Microkernel (Plugin):** Identifies core orchestrator modules versus dynamic extension/plugin registry mechanisms.
8. **Microservices:** Identifies independent service directories, API gateways, service discovery (`consul`, `grpc`), and inter-service communication paths.

---

### 4. Coupling Metrics & Structural Risk Scoring (`CouplingAnalyzer`)

#### Metrics Computed
* **Afferent Coupling / Fan-In ($C_a$):** Number of external files that depend on this file. High Fan-In indicates high responsibility / core abstraction.
* **Efferent Coupling / Fan-Out ($C_e$):** Number of external files this file depends on. High Fan-Out indicates high instability / fragility.
* **Instability Index ($I$):** $I = \frac{C_e}{C_a + C_e}$ ($I=0$ represents maximum stability, $I=1$ represents maximum instability).
* **Circular Coupling Cycles:** Exact circular dependency chains detected using depth-first circuit enumeration.

#### Structural Risk Formula
Every file receives an objective risk score $R \in [0, 100]$:

$$R = \min\left(100, (C_a \times 8) + (C_e \times 5) + (\text{CycleBonus}) + (\text{HighFanBonus})\right)$$

Where:
* $\text{CycleBonus} = 30$ if the file participates in any circular dependency cycle.
* $\text{HighFanBonus} = 10 \text{ if } C_a > 5 \text{ } + 10 \text{ if } C_e > 5$.
* Categorization: **Critical** ($R \ge 80$), **High** ($R \ge 60$), **Medium** ($R \ge 30$), **Low** ($R < 30$).

---

### 5. Change Impact & Blast Radius Simulation (`BlastRadiusAnalyzer`)
Simulates the systemic impact of making changes to any file in the codebase before a single line of code is edited:

```
 [ Target File ] ──(1-hop)──► [ Direct Dependents ] ──(2-3 hops)──► [ Indirect Dependents ]
        │
        └───[:CONTAINS]──► [ Functions ] ◄──[:CALLS]── [ External Callers ]
```

* **Direct Blast Radius (1-Hop):** Exact files with direct `[:DEPENDS_ON]` edges pointing to the target.
* **Indirect Blast Radius (2–3 Hops):** Cascading files affected via transitive dependencies, bounded to 3 hops to maintain architectural relevance.
* **Function-Level Breaking Surface:** Functions defined within the target file and their runtime callers across the entire repository.
* **Simulation Modes:**
  * `DELETE`: Evaluates total catastrophic breakages (30 pts per direct dependent + 20 pts per function caller).
  * `MOVE`: Evaluates import reference breaks across existing callers (8 pts per dependent).
  * `MODIFY`: Evaluates logic regression and test surface risk (5 pts per total affected dependent).

---

### 6. Cryptographic Snapshot Lineage & Integrity (`VersionTracker`)
* **SHA-256 Content Fingerprinting:** Hashes all source code content, establishing an immutable cryptographic audit trail.
* **Git Lineage Backfilling:** Imports historical commits to construct previous version lineages (`(:Version)-[:PREVIOUS_VERSION]->(:Version)`).
* **Snapshot Versioning:** Stores complete architectural metric snapshots per Git commit hash.
* **Architectural Delta Engine (`compare_snapshots`):** Compares any two historical snapshots to compute:
  * File diffs (added, removed, modified)
  * Net coupling metric changes ($\Delta \text{avg\_coupling}$)
  * Net circular dependency deltas ($\Delta \text{cycles}$)
  * Architectural pattern shifts (e.g. newly emerging MVC or degraded Hexagonal isolation)

---

### 7. Hybrid Semantic Synthesis (`LLMReasoner` + `RetrievalEngine`)
To produce genuine architectural insights rather than generic code descriptions, ARCHITECH compiles graph topology into an enriched architectural context prompt:

1. **Project Framing:** Extracted intent and domain from `README.md`.
2. **Topological Metrics:** High fan-out files, hub orchestrators, cycle paths, and risk scores.
3. **Graphify Knowledge Extraction:** Class/function signatures, AST-indexed dependency edges, and code snippets from hub nodes.
4. **Structured Inference:** Groq Llama-3.3-70B synthesizes a three-tier architectural report:
   * **Macro Level (Overview):** System domain, architectural style, fit, and subsystem breakdown.
   * **Meso Level (Modules):** Subsystem boundaries, inter-module data flow, and separation of concerns.
   * **Micro Level (Key Files):** Architecturally critical files, single points of failure, God objects, and refactoring recommendations.

---

## 🗂️ Repository Architecture & File Matrix

```
repoanayliser-main/
├── backend/
│   ├── main.py                     # FastAPI REST API controller & background task manager
│   ├── requirements.txt            # Backend dependencies
│   ├── src/
│   │   ├── config.py               # Pydantic environment configuration
│   │   ├── analysis_engine.py      # Core orchestrator: coordinates parsing, graph, analysis & caching
│   │   ├── analysis/
│   │   │   └── confidence_analyzer.py  # Evaluates confidence and failure modes of architectural claims
│   │   ├── graph/
│   │   │   ├── analyzers.py        # PatternDetector (8 patterns) & CouplingAnalyzer (metrics & risk)
│   │   │   ├── blast_radius.py     # Change impact simulation (Delete, Move, Modify)
│   │   │   ├── dependency_mapper.py# In-memory NetworkX DiGraph builder & cycle detector
│   │   │   ├── function_graph.py   # Function-level call graph builder for visualization
│   │   │   ├── graph_db.py         # Neo4j Cypher DAL for nodes, relationships & multi-hop queries
│   │   │   └── version_tracker.py  # SHA-256 versioning, Git history ingestion & tamper detection
│   │   ├── parser/
│   │   │   ├── repo_loader.py      # Git cloning, local folder path validation & file filtering
│   │   │   └── static_parser.py    # Tree-sitter AST parser (Python, JS) with OOP method extraction
│   │   ├── reasoning/
│   │   │   └── llm_reasoner.py     # Groq API integration (Llama-3.3-70B) for architectural synthesis
│   │   └── retrieval/
│   │       ├── graphify_retriever.py # Graphify CLI interface for AST knowledge extraction
│   │       └── retrieval_engine.py # Hybrid Graphify + Neo4j evidence retrieval engine
└── frontend/
    └── src/
        ├── App.js                  # Master application component & tab controller
        ├── components/
        │   ├── AnalyzeRepo.js       # Repository input form (GitHub / Local Folder) with async polling
        │   ├── ArchitectureView.js  # Macro/Meso/Micro architecture report viewer with dynamic layer stack
        │   ├── BlastRadius.js       # Interactive blast radius simulator with D3 force graph
        │   ├── CouplingAnalysis.js  # Coupling metrics dashboard, KPIs & circular dependency list
        │   ├── DependencyGraph.js   # Force-directed D3.js file-to-file dependency graph
        │   ├── FunctionAnalysis.js  # Function-level inspection, callers & LLM explanation
        │   ├── FunctionGraph.js     # Force-directed D3.js function call chain visualization
        │   ├── ImpactAnalysis.js    # AI-assisted change impact analysis report
        │   ├── PatternDetection.js  # Detected architectural patterns, confidence gauges & breakdowns
        │   ├── RepositoryManager.js # Analyzed repository catalog, version tracking & snapshot controls
        │   └── SnapshotComparison.js# Cross-commit architectural diff & risk assessment comparison
        └── services/
            └── api.js              # Centralized Axios REST client
```

---

## 📡 Complete REST API Reference

| Method | Route | Description |
|---|---|---|
| `POST` | `/analyze` | Initiates background analysis of a remote GitHub repository. |
| `POST` | `/analyze/local` | Initiates background analysis of a local directory on the host machine. |
| `GET` | `/status/{job_id}` | Polls the current processing state (`processing`, `completed`, `failed`). |
| `GET` | `/browse-folder` | Opens a native OS folder picker dialog to select local repositories. |
| `GET` | `/architecture?repo_id={id}` | Returns the synthesized 3-tier architectural report and structural stats. |
| `GET` | `/patterns?repo_id={id}` | Returns detected architectural patterns, layer breakdowns, and confidence scores. |
| `GET` | `/coupling?repo_id={id}` | Returns high-coupling files, Fan-In/Fan-Out metrics, and dependency cycles. |
| `GET` | `/confidence-report?repo_id={id}` | Returns confidence ratings, reasoning, and failure scenarios for architectural claims. |
| `GET` | `/blast-radius/{file_path}?change_type={t}&repo_id={id}` | Returns direct/indirect dependents, affected functions, and simulated risk score. |
| `POST` | `/impact` | Returns AI semantic impact analysis for a specific file and change type. |
| `GET` | `/graph/data?repo_id={id}` | Returns node and edge collections for file dependency graph visualization. |
| `GET` | `/graph/functions?repo_id={id}` | Returns node and edge collections for function call graph visualization. |
| `GET` | `/graph/function/{name}?repo_id={id}` | Returns the call chain for a specific target function. |
| `GET` | `/functions?repo_id={id}` | Lists all indexed functions with their source files and line locations. |
| `GET` | `/function/{name}` | Returns callers, implementation code, and AI explanation for a function. |
| `GET` | `/repositories` | Lists all analyzed repositories with snapshot and file counts. |
| `POST` | `/repository/{repo_id}/load` | Loads a repository's cached analysis state into memory. |
| `DELETE` | `/repository/{repo_id}` | Deletes a repository and all associated graph nodes and snapshots. |
| `GET` | `/repository/{repo_id}/snapshots` | Lists all historical analysis snapshots for a repository. |
| `GET` | `/repository/{repo_id}/compare-snapshots/{s1}/{s2}` | Performs full architectural, coupling, and dependency diff between two snapshots. |
| `GET` | `/repository/{repo_id}/commits` | Returns the commit history lineage for a repository. |
| `GET` | `/repository/{repo_id}/file-history?file_path={p}` | Returns the cryptographic SHA-256 version lineage for a file. |
| `POST` | `/repository/{repo_id}/check-integrity?file_path={p}` | Compares current file content hash against stored hash to detect out-of-band tampering. |

---

## 🖥️ User Interface Capabilities

1. **Analyze:** Dual-mode repository ingestion (Remote GitHub clone with shallow depth or native Local Folder selection).
2. **Repository Manager:** Multi-repo workspace catalog with Git commit histories, contributor metrics, and integrity validation.
3. **Pattern Detection:** Real-time visual cards for all 8 architectural styles with confidence bars, layer compositions, and component breakdowns.
4. **Coupling Analysis:** System-wide average coupling score gauge, instability indices, circular dependency cycle listings, and per-module Fan-In/Fan-Out rankings.
5. **Blast Radius & Impact Analysis:** Interactive change simulation (Modify/Delete/Move) with D3 force graph visualizer, risk severity score, and AI impact analysis.
6. **Architecture View:** AI-synthesized system architecture breakdown with interactive layer stack visualizer, top directory distributions, and source citations.
7. **File & Function Graphs:** Interactive, zoomable D3.js force-directed graphs with node search, neighbor highlighting, and call chain isolation.
8. **Snapshot Comparison:** Automated cross-commit architectural diffing highlighting file growth, coupling shifts, and regression risks.

---

## 🔒 Security & Performance Considerations

* **Local Code Privacy:** Analysis is executed locally against host repositories. Only aggregated structural context and metadata summaries are transmitted to the LLM reasoning engine.
* **Deterministic Caching:** SHA-256 commit hashing and Snapshot caching prevent redundant AST parsing and eliminate unnecessary LLM invocations on unchanged commits.
* **Thread-Safe LRU In-Memory Cache:** Python `threading.Lock` and `collections.OrderedDict` guard the high-speed cache against multi-threaded request races.
* **Process Isolation:** The folder dialog launcher executes via isolated subprocesses to prevent GUI thread conflicts with the asynchronous FastAPI/Uvicorn event loop.
