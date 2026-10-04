# 🧠 ARCHITECH — AI Concepts, Algorithms & Techniques Reference

![ARCHITECH Flowchart Diagram](file:///c:/Users/user/Desktop/PPROJECTS/repoanayliser-main/architech_flowchart.png)

> A comprehensive guide to every AI, ML, and Computer Science concept used in the ARCHITECH codebase, where it lives, and how it works.

---

## Table of Contents

1. [Abstract Syntax Tree (AST) Parsing](#1-abstract-syntax-tree-ast-parsing)
2. [Knowledge Graph Construction](#2-knowledge-graph-construction)
3. [Graph Algorithms](#3-graph-algorithms)
4. [Large Language Model (LLM) Reasoning](#4-large-language-model-llm-reasoning)
5. [Retrieval-Augmented Generation (RAG)](#5-retrieval-augmented-generation-rag)
6. [Heuristic Pattern Classification](#6-heuristic-pattern-classification)
7. [Token-Based Relevance Scoring](#7-token-based-relevance-scoring)
8. [Structural Risk Scoring](#8-structural-risk-scoring)
9. [Confidence Analysis & Claim Verification](#9-confidence-analysis--claim-verification)
10. [Content-Addressable Hashing](#10-content-addressable-hashing)
11. [Two-Pass Graph Construction](#11-two-pass-graph-construction)

---

## 1. Abstract Syntax Tree (AST) Parsing

| Property | Detail |
|---|---|
| **Concept** | Parsing source code into a tree representation of its syntactic structure |
| **Library** | `tree-sitter` (with `tree-sitter-python`, `tree-sitter-javascript`) |
| **File** | `backend/src/parser/static_parser.py` |
| **Class** | `StaticParser` |

### How It Works

Tree-sitter is an **incremental parser generator** that builds a concrete syntax tree (CST) for source code. Unlike regex-based parsers, it understands language grammar, so it can reliably extract:

```
Source Code → tree-sitter → AST → Extract symbols
```

### What Gets Extracted

| Extraction | Method | AST Node Type |
|---|---|---|
| **Classes** | `_extract_classes()` | `class_definition` |
| **Functions** | `_extract_functions()` | `function_definition`, `function_declaration` |
| **Imports** | `_extract_imports()` | `import_statement`, `import_from_statement` |
| **Function Calls** | `_extract_function_calls()` | `call` (Python), `call_expression` (JS) |
| **Caller→Callee Mapping** | `_extract_function_to_function_calls()` | Nested call nodes within function bodies |

### Key Design Decision

Method calls like `model.query_all()` are extracted by walking the AST `attribute` node and taking the **last** identifier (`.split('.')[-1]`), which gives us `query_all` — enabling cross-file function linking.

---

## 2. Knowledge Graph Construction

| Property | Detail |
|---|---|
| **Concept** | Storing code relationships as a labeled property graph |
| **Database** | Neo4j (graph database with Cypher query language) |
| **File** | `backend/src/graph/graph_db.py` |
| **Class** | `GraphDB` |

### Graph Schema

```
(:Repository)-[:CONTAINS]->(:File)-[:CONTAINS]->(:Function)
(:Repository)-[:CONTAINS]->(:File)-[:CONTAINS]->(:Class)
(:File)-[:DEPENDS_ON]->(:File)
(:File)-[:IMPORTS]->(:Module)
(:File)-[:CALLS]->(:Function)
(:Function)-[:CALLS]->(:Function)
(:Function)-[:CALLS_TRANSITIVE]->(:Function)
(:Repository)-[:HAS_SNAPSHOT]->(:Snapshot)-[:ANALYZED_FILE]->(:File)
```

### Key Algorithms Used

| Algorithm | Purpose | Cypher Pattern |
|---|---|---|
| **MERGE (Upsert)** | Idempotent node/edge creation | `MERGE (f:File {path: $p})` |
| **Path Traversal** | Finding transitive dependencies | `MATCH (a)-[:CALLS*2..5]->(c)` |
| **Cycle Detection** | Finding circular dependencies | `MATCH (f1)-[:DEPENDS_ON*1..5]->(f2) WHERE f1 = f2` |
| **Flexible Matching** | Cross-platform path resolution | `WHERE f.path ENDS WITH $suffix` |

---

## 3. Graph Algorithms

| Property | Detail |
|---|---|
| **Library** | NetworkX (`nx.DiGraph`) |
| **Files** | `backend/src/graph/dependency_mapper.py`, `backend/src/graph/analyzers.py`, `backend/src/graph/blast_radius.py` |

### 3.1 Directed Dependency Graph (DiGraph)

**File:** `dependency_mapper.py` → `DependencyMapper`

Builds a directed graph where:
- **Nodes** = source files (with all parsed metadata as attributes)
- **Edges** = import relationships (`type='imports'` or `type='external'`)

Uses a **two-pass algorithm**:
1. **Pass 1:** Add all files as nodes + build a module-name → file-path map
2. **Pass 2:** Resolve imports to edges using fuzzy module matching

### 3.2 Cycle Detection

**Method:** `DependencyMapper.detect_cycles()` → `nx.simple_cycles()`

Uses NetworkX's implementation of **Johnson's algorithm** for finding all elementary circuits in a directed graph. Time complexity: O((n + e)(c + 1)) where c = number of cycles.

### 3.3 Fan-In / Fan-Out Coupling Analysis

**File:** `analyzers.py` → `CouplingAnalyzer`

| Metric | Definition | Method |
|---|---|---|
| **Fan-In** | Number of files that import this file (afferent coupling) | `graph.in_degree(node)` |
| **Fan-Out** | Number of files this file imports (efferent coupling) | `graph.out_degree(node)` |
| **Instability** | `fan_out / (fan_in + fan_out)` — how susceptible to change | Custom formula |

High coupling detection threshold: `fan_in + fan_out > 10`

### 3.4 Strongly Connected Components (SCC)

**Method:** `DependencyMapper.get_strongly_connected_components()` → `nx.strongly_connected_components()`

Uses **Tarjan's algorithm** to find groups of files that are mutually dependent (all reachable from each other). Each SCC with >1 node indicates a circular dependency cluster.

### 3.5 Shortest Path / Blast Radius BFS

**File:** `dependency_mapper.py` → `get_blast_radius()` and `blast_radius.py` → `BlastRadiusAnalyzer`

Uses `nx.has_path()` and `nx.shortest_path_length()` to compute the **transitive closure** of all files affected when a file changes. Limited to depth 3 for performance.

```
Target File ←[DEPENDS_ON]← Direct Dependents ←[DEPENDS_ON*2..3]← Indirect Dependents
```

---

## 4. Large Language Model (LLM) Reasoning

| Property | Detail |
|---|---|
| **Concept** | Using an LLM to generate natural-language explanations from structured data |
| **Provider** | Groq Cloud API |
| **Model** | `llama-3.3-70b-versatile` |
| **File** | `backend/src/reasoning/llm_reasoner.py` |
| **Class** | `LLMReasoner` |

### LLM Use Cases

| Use Case | Method | What It Does |
|---|---|---|
| **Architecture Report** | `explain_architecture_report()` | Single consolidated call generating Overview, Modules, and Key Files sections |
| **Blast Radius Impact** | `explain_impact_with_graph()` | Explains cascading effects of modifying/deleting a file |
| **Function Analysis** | `explain_function()` | Explains purpose, usage, and impact of a single function |
| **Meso-Level Analysis** | `explain_meso_level()` | Module-level architecture description |
| **Micro-Level Analysis** | `explain_micro_level()` | File-level architecture details |

### Prompt Engineering Techniques

1. **Structured Output Forcing**: Prompts include exact section headers (`## Overview`, `## Modules`, `## Key Files`) and the response is parsed by splitting on those headers.

2. **Evidence Grounding**: Every prompt includes concrete code evidence (file names, function names, class names) to prevent hallucination. The LLM is instructed to "cite actual function names" from evidence.

3. **Token Budget Control**: `_call_llm_with_limit()` caps `max_tokens=1200` for the architecture report to prevent verbose, unfocused outputs.

4. **Temperature Tuning**: `temperature=0.3` — low temperature for factual, deterministic analysis rather than creative generation.

5. **Graphify Enrichment**: When available, the LLM prompt is augmented with actual function and class names from Graphify's knowledge graph, allowing citations of real symbols.

---

## 5. Retrieval-Augmented Generation (RAG)

| Property | Detail |
|---|---|
| **Concept** | Augmenting LLM prompts with retrieved structural context |
| **Files** | `backend/src/retrieval/retrieval_engine.py`, `backend/src/retrieval/graphify_retriever.py` |
| **Classes** | `RetrievalEngine`, `GraphifyRetriever` |

### Architecture

```
User Query → GraphifyRetriever (token scoring) → Top-K nodes
                                                      ↓
Neo4j (dependency context)  ──→  Boost scores  ──→  Merged evidence
                                                      ↓
                                              LLMReasoner (prompt)
```

### How Graphify Works

1. **Indexing:** Runs `graphify update <repo_path>` CLI to produce `graph.json` containing functions, classes, imports, and their relationships.

2. **Token-Based Retrieval:** `get_context_for_query()` scores each graph node by matching query tokens against node names, summaries, file paths, and types (see Section 7).

3. **Path Context:** `get_path_context()` retrieves all symbols (functions, classes) belonging to a specific file — used for blast-radius explanations.

4. **Dependency Edge Extraction:** `get_dependency_edges()` extracts file-to-file dependency edges from Graphify's knowledge graph to supplement NetworkX's import resolution.

### Hybrid Retrieval Strategy

The `RetrievalEngine` combines two sources:

| Source | What It Provides | Strength |
|---|---|---|
| **Graphify** | Structural context (functions, classes, signatures) | Rich symbol-level data |
| **Neo4j** | Dependency topology (who imports whom) | Accurate graph traversals |

Evidence nodes whose files appear in the Neo4j dependency context get a **+0.5 score boost**, fusing structural relevance with topological proximity.

---

## 6. Heuristic Pattern Classification

| Property | Detail |
|---|---|
| **Concept** | Multi-signal heuristic classification of architectural patterns |
| **File** | `backend/src/graph/analyzers.py` |
| **Class** | `PatternDetector` |

### Detection Strategy

Each pattern detector uses **4 classification signals** per graph node:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Filename    │   │  Directory   │   │ Class/Func   │   │  Framework   │
│  Keywords    │   │  Keywords    │   │  Names       │   │  Imports     │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └──────────────────┴──────────────────┴──────────────────┘
                                    │
                              Classification
```

### 8 Patterns Detected

| # | Pattern | Key Signals | Confidence Logic |
|---|---|---|---|
| 1 | **Layered (N-tier)** | `controller/`, `service/`, `repository/` dirs; framework imports | ≥2 layers detected + validated inter-layer edges |
| 2 | **MVC** | `*_controller.py`, `*_model.py`, `*_view.py`; render/route functions | Controller→Model edge verification |
| 3 | **Hexagonal** | `port/`, `adapter/`, `domain/` dirs; interface/abstract classes | Domain isolation check (external deps < 30%) |
| 4 | **Event-Driven** | `*_event.py`, `*_subscriber.py`; publish/emit/subscribe functions | Events ≥ 1 AND (publishers ≥ 1 OR subscribers ≥ 1) |
| 5 | **Pipe-Filter** | `pipeline/`, `filters/` dirs; process/transform/pipe functions | Pipes ≥ 1 AND Filters ≥ 1 |
| 6 | **Client-Server** | Flask/FastAPI imports (server); requests/axios (client) | Servers ≥ 1 AND Clients ≥ 1 |
| 7 | **Microkernel** | `core/kernel.py`, `plugins/` dir; register/dispatch functions | Core ≥ 1 AND Plugins ≥ 2 |
| 8 | **Microservices** | `services/` dir; gateway files; multiple independent FastAPI apps | Services ≥ 3 |

### Confidence Scoring

Each pattern uses a **tiered confidence system** based on multiple evidence thresholds:

```python
# Example: MVC confidence tiers
if has_mvc and views >= 2 and controller_model_links > 0:
    confidence = 0.90  # Strong: All 3 components + verified edges
elif has_mvc and controller_model_links > 0:
    confidence = 0.75  # Good: C+M with verified dependency
elif has_mvc and views >= 1:
    confidence = 0.65  # Moderate: All present but unverified
elif has_mvc:
    confidence = 0.50  # Weak: Minimal signal
```

---

## 7. Token-Based Relevance Scoring

| Property | Detail |
|---|---|
| **Concept** | Scoring knowledge graph nodes by query token overlap |
| **File** | `backend/src/retrieval/graphify_retriever.py` |
| **Method** | `GraphifyRetriever._score_node()` |

### Scoring Weights

```python
for token in query_tokens:
    if token in name:      score += 3.0   # Name match (strongest)
    if token in summary:   score += 1.5   # Docstring match
    if token in file_path: score += 1.0   # File path match
    if token == node_type: score += 0.5   # Type match (weakest)

# Type boost: functions/classes are more relevant than imports
if node_type in ("function", "method", "class"):
    score *= 1.2
```

This is a **TF-based (term frequency) ranking** without IDF, optimized for small-corpus code search where every token is meaningful.

---

## 8. Structural Risk Scoring

| Property | Detail |
|---|---|
| **Concept** | Quantifying the risk of changing a file based on graph topology |
| **File** | `backend/src/graph/blast_radius.py` |
| **Class** | `BlastRadiusAnalyzer` |

### Risk Model

```
Risk Score = (Direct Dependents × 30) + (Function Callers × 20) + (Function Count × 10)
```

| Risk Level | Score Range | Meaning |
|---|---|---|
| **Critical** | ≥ 100 | Core infrastructure; change breaks everything |
| **High** | 60–99 | Widely depended upon |
| **Medium** | 30–59 | Moderate blast radius |
| **Low** | < 30 | Isolated module; safe to change |

### Change Type Multipliers

| Change Type | Weight Model |
|---|---|
| **Delete** | 30 pts per direct import + 20 pts per function caller + 10 pts per function |
| **Move** | 8 pts per direct import (all import paths break) |
| **Modify** | 5 pts per total affected file (direct + indirect) |

### Structural Risk (CouplingAnalyzer)

**File:** `analyzers.py` → `CouplingAnalyzer.compute_structural_risk()`

```python
score = (fan_in × 8) + (fan_out × 5) + (30 if in_cycle else 0)
```

Adds a flat **30-point penalty** if the file is part of a circular dependency (detected via SCC).

---

## 9. Confidence Analysis & Claim Verification

| Property | Detail |
|---|---|
| **Concept** | Meta-analysis of system's own claims with failure mode documentation |
| **File** | `backend/src/analysis/confidence_analyzer.py` |
| **Class** | `ConfidenceAnalyzer` |

### What It Does

For every architectural claim the system makes, it generates:

| Field | Description |
|---|---|
| `claim` | Human-readable statement (e.g., "System follows MVC pattern") |
| `confidence` | 0.0 – 1.0 score |
| `reasoning` | Why this confidence level was assigned |
| `failure_scenario` | When/why this analysis might be wrong |
| `evidence` | Files supporting the claim |

### Failure Scenarios Documented

- **Layered:** "Cannot detect logical layering without physical separation"
- **MVC:** "May fail if controllers use non-standard naming"
- **Hexagonal:** "Cannot verify actual dependency inversion"
- **Event-Driven:** "May miss message queue patterns without explicit naming"
- **Circular Dependencies:** "Cannot detect runtime circular dependencies or dynamic imports"

This is a form of **epistemic uncertainty quantification** — the system is self-aware about its limitations.

---

## 10. Content-Addressable Hashing

| Property | Detail |
|---|---|
| **Concept** | Using SHA-256 hashes as deterministic identifiers |
| **File** | `backend/src/graph/version_tracker.py` |
| **Class** | `VersionTracker` |

### Two Uses of Hashing

| Use | Input | Output | Purpose |
|---|---|---|---|
| **Repository ID** | Repository URL or absolute path | `SHA256[:16]` | Stable, deterministic repo identifier |
| **File Versioning** | File content bytes | `SHA256` | Detect if a file changed between analyses |

### Version Tracking Algorithm

```
For each file:
  1. Compute SHA-256 of current file content
  2. Query Neo4j for the last stored hash
  3. If hash differs → create new version node → status: "new_version"
  4. If hash matches → skip re-analysis → status: "unchanged"
```

This implements a **content-addressable storage** pattern — the file's identity is its content, not its path or timestamp.

---

## 11. Two-Pass Graph Construction

| Property | Detail |
|---|---|
| **Concept** | Separating node creation from edge creation to handle cross-file references |
| **File** | `backend/src/analysis_engine.py` |
| **Methods** | `_store_in_graph()` (Pass 1), `_store_edges_in_graph()` (Pass 2) |

### Problem Solved

When processing files sequentially, File A may call a function in File B. If we create the CALLS edge while processing File A, File B's Function node **doesn't exist yet**.

### Two-Pass Solution

```
Pass 1 (per-file loop):
  ├── Create File node
  ├── Create Class nodes
  ├── Create Function nodes
  └── Create Import relationships

Pass 2 (after ALL files processed):
  ├── Create File→Function CALLS edges
  └── Create Function→Function CALLS edges
```

This ensures all callee Function nodes exist before any CALLS edges are created.

---

## Summary Table

| # | Concept | Type | File(s) |
|---|---|---|---|
| 1 | AST Parsing (tree-sitter) | Compiler Theory | `static_parser.py` |
| 2 | Knowledge Graph (Neo4j) | Graph Database | `graph_db.py` |
| 3 | Cycle Detection (Johnson's) | Graph Algorithm | `dependency_mapper.py` |
| 4 | SCC (Tarjan's) | Graph Algorithm | `dependency_mapper.py` |
| 5 | BFS Blast Radius | Graph Traversal | `blast_radius.py` |
| 6 | Fan-In/Fan-Out Coupling | Software Metrics | `analyzers.py` |
| 7 | LLM Reasoning (Llama 3.3) | Generative AI | `llm_reasoner.py` |
| 8 | RAG Pipeline | Information Retrieval + AI | `retrieval_engine.py`, `graphify_retriever.py` |
| 9 | Heuristic Pattern Detection | Rule-Based Classification | `analyzers.py` |
| 10 | Token-Based Relevance Scoring | Information Retrieval | `graphify_retriever.py` |
| 11 | Structural Risk Scoring | Quantitative Risk Analysis | `blast_radius.py`, `analyzers.py` |
| 12 | Confidence/Claim Analysis | Epistemic Uncertainty | `confidence_analyzer.py` |
| 13 | SHA-256 Content Hashing | Content-Addressable Storage | `version_tracker.py` |
| 14 | Two-Pass Graph Construction | Topological Ordering | `analysis_engine.py` |

---

*Generated for the ARCHITECH Repository Analysis Pipeline*
