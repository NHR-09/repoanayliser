# ARCHITECH — 5-Person Team Division with AI Concepts

This document divides the ARCHITECH project into 5 functional roles, each with core responsibilities and an AI/ML concept to explain and own.

---

## 📋 Team Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ARCHITECH PROJECT TEAM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Person 1: Code Parser & AST Engineer                              │
│  ├─ AI Concept: Abstract Syntax Tree (AST) Parsing                │
│  └─ Files: parser/static_parser.py, parser/repo_loader.py        │
│                                                                     │
│  Person 2: Graph Database & Knowledge Engineer                     │
│  ├─ AI Concept: Knowledge Graph Construction & Representation     │
│  └─ Files: graph/graph_db.py, Neo4j Schema Design                │
│                                                                     │
│  Person 3: Graph Algorithms & Dependency Analyst                   │
│  ├─ AI Concept: Graph Algorithms (SCC, Cycles, Coupling)          │
│  └─ Files: graph/dependency_mapper.py, analyzers.py, blast_...    │
│                                                                     │
│  Person 4: LLM & RAG Engineer                                      │
│  ├─ AI Concept: LLM Reasoning & Retrieval-Augmented Generation    │
│  └─ Files: reasoning/llm_reasoner.py, retrieval/*.py              │
│                                                                     │
│  Person 5: Frontend & Pattern Detection Engineer                   │
│  ├─ AI Concept: Heuristic Pattern Classification & Confidence     │
│  └─ Files: frontend/src/*, analysis/confidence_analyzer.py        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 👤 Person 1: Code Parser & AST Engineer

**AI Concept to Explain:** `Abstract Syntax Tree (AST) Parsing with Tree-sitter`

### Responsibilities

| Task | Priority | Details |
|---|---|---|
| Parse repositories | HIGH | Clone GitHub repos or load local paths using `RepositoryLoader` |
| Extract code symbols | HIGH | Extract classes, functions, imports, and function calls from source files using Tree-sitter AST |
| Build symbol index | MEDIUM | Create a searchable map of all functions, classes, and their file locations |
| Handle multi-language | MEDIUM | Support Python and JavaScript (can extend to Java, Go, etc.) |
| Cache parsed data | LOW | Store extracted symbols in Neo4j for fast retrieval |

### Core Files

| File | Role |
|---|---|
| `backend/src/parser/static_parser.py` | **Main file** — AST extraction logic using Tree-sitter |
| `backend/src/parser/repo_loader.py` | Repository loading, cloning, and file enumeration |
| `backend/src/analysis_engine.py` | Orchestration — calls `StaticParser` in the pipeline |

### Key Methods to Implement/Explain

```python
# StaticParser class
._extract_classes()          # Find class definitions
._extract_functions()        # Find function/method definitions
._extract_imports()          # Extract import statements
._extract_function_calls()   # Find all function calls
._extract_function_to_function_calls()  # Map who calls whom
```

### Example AST Extraction Flow

```
Source File (Python)
    ↓
tree-sitter parser
    ↓
Concrete Syntax Tree (CST)
    ↓
Walk tree for nodes:
  - class_definition → Class(name, file_path)
  - function_definition → Function(name, file_path)
  - import_statement → Import(module_name, file_path)
  - call expressions → FunctionCall(caller, callee, line)
    ↓
Extracted Symbols Dict → Sent to GraphDB
```

### What to Explain in AI Concept Presentation

1. **What is AST?** — Syntactic structure of code, not just text matching
2. **Why Tree-sitter?** — Incremental, tolerant to errors, accurate multi-language support
3. **How does extraction work?** — Tree traversal, node type matching, symbol resolution
4. **Edge cases:** — Method chains (`model.query().filter()`), nested imports, lambda functions
5. **Performance:** — Time complexity of AST parsing vs. regex-based parsing

---

## 👤 Person 2: Graph Database & Knowledge Engineer

**AI Concept to Explain:** `Knowledge Graph Construction & Representation`

### Responsibilities

| Task | Priority | Details |
|---|---|---|
| Design Neo4j schema | HIGH | Nodes (File, Function, Class, Module, Repository) and relationships |
| Create graph nodes | HIGH | MERGE nodes for files, functions, classes, repositories |
| Create graph edges | HIGH | Add DEPENDS_ON, IMPORTS, CONTAINS, CALLS, HAS_VERSION relationships |
| Query the graph | MEDIUM | Write Cypher queries for dependencies, cycles, paths |
| Manage snapshots | MEDIUM | Store analysis snapshots for version tracking and comparisons |
| Handle versioning | MEDIUM | Store commit hashes, timestamps, and file versions |

### Core Files

| File | Role |
|---|---|
| `backend/src/graph/graph_db.py` | **Main file** — Neo4j connection, CRUD operations, Cypher queries |
| `backend/src/graph/version_tracker.py` | Version history and commit tracking |
| `backend/src/config.py` | Neo4j credentials and connection URI |

### Neo4j Schema to Implement

```cypher
-- Node Types
(:Repository {repo_id, name, url, path})
(:File {file_path, language, lines_of_code, path_normalized})
(:Function {name, file_path, line_start, line_end, signature})
(:Class {name, file_path, line_start, line_end})
(:Module {name, type})  -- "external" or "internal"
(:Snapshot {snapshot_id, created_at, commit_hash, total_files, avg_coupling})
(:Commit {commit_hash, message, timestamp})
(:User {email, name})

-- Relationships
(:Repository)-[:CONTAINS]->(:File)
(:Repository)-[:CONTAINS]->(:Function)
(:Repository)-[:CONTAINS]->(:Class)
(:File)-[:CONTAINS]->(:Function)
(:File)-[:CONTAINS]->(:Class)
(:File)-[:DEPENDS_ON]->(:File)
(:File)-[:IMPORTS]->(:Module)
(:Function)-[:CALLS]->(:Function)
(:Function)-[:CALLS_TRANSITIVE]->(:Function)
(:Repository)-[:HAS_SNAPSHOT]->(:Snapshot)
(:Snapshot)-[:ANALYZED_FILE]->(:File)
(:Repository)-[:HAS_COMMIT]->(:Commit)
(:Commit)-[:AUTHORED_BY]->(:User)
```

### Key Cypher Queries to Explain

```cypher
-- Find all files that depend on a specific file
MATCH (f:File {file_path: $target})<-[:DEPENDS_ON]-(dependent:File)
RETURN dependent.file_path

-- Detect circular dependencies
MATCH (f1:File)-[:DEPENDS_ON*1..5]->(f2:File) WHERE f1 = f2
RETURN f1.file_path, [relationships in (f1)-[:DEPENDS_ON*1..5]->(f2) | type(relationships)] as cycle

-- Find all functions called by a specific function
MATCH (fn:Function {name: $func_name})-[:CALLS*1..3]->(called:Function)
RETURN DISTINCT called.name, called.file_path

-- Get files with highest coupling
MATCH (f:File)
WITH f, size((f)<-[:DEPENDS_ON]-(:File)) as inDegree, size((f)-[:DEPENDS_ON]->(:File)) as outDegree
RETURN f.file_path, inDegree, outDegree, (inDegree + outDegree) as totalCoupling
ORDER BY totalCoupling DESC
LIMIT 10
```

### What to Explain in AI Concept Presentation

1. **What is a Knowledge Graph?** — Nodes + Edges with semantic meaning
2. **Graph Representation Models:** — Property graphs vs. RDF vs. Hypergraphs
3. **Why Neo4j?** — ACID transactions, pattern matching with Cypher, scalability
4. **Schema design trade-offs:** — Normalization vs. denormalization, edge direction
5. **Query optimization:** — Index usage, cardinality estimation, explain plans
6. **Real-world example:** — How the ARCHITECH graph represents code relationships

---

## 👤 Person 3: Graph Algorithms & Dependency Analyst

**AI Concept to Explain:** `Graph Algorithms: Cycle Detection, Coupling Analysis, and Shortest Path`

### Responsibilities

| Task | Priority | Details |
|---|---|---|
| Build dependency graph | HIGH | Create NetworkX DiGraph from parsed imports |
| Detect cycles | HIGH | Find circular dependencies using Tarjan's algorithm |
| Compute coupling metrics | HIGH | Calculate Fan-In, Fan-Out, Instability for each file |
| Find SCCs | MEDIUM | Detect Strongly Connected Components (mutually dependent clusters) |
| Compute blast radius | HIGH | Simulate change impact using BFS/DFS transitive closure |
| Visualize graphs | MEDIUM | Generate graph data for frontend visualization |

### Core Files

| File | Role |
|---|---|
| `backend/src/graph/dependency_mapper.py` | **Main file** — DiGraph construction, cycle detection, BFS |
| `backend/src/graph/analyzers.py` | Coupling analysis, metrics computation |
| `backend/src/graph/blast_radius.py` | Change impact simulation, transitive closure |
| `backend/src/graph/function_graph.py` | Function-level call graphs |

### Algorithms to Implement/Explain

| Algorithm | Purpose | NetworkX Method | Complexity |
|---|---|---|---|
| **Johnson's Algorithm** | Find all elementary cycles | `nx.simple_cycles()` | O((n+e)(c+1)) |
| **Tarjan's SCC** | Find strongly connected components | `nx.strongly_connected_components()` | O(n+e) |
| **BFS/DFS** | Find reachable nodes (blast radius) | `nx.has_path()`, `nx.shortest_path_length()` | O(n+e) |
| **Topological Sort** | Order files by dependencies | `nx.topological_sort()` | O(n+e) |
| **Page Rank** | Centrality/importance scoring | `nx.pagerank()` | Iterative |

### Example: Cycle Detection Flow

```python
# Two-pass construction
graph = nx.DiGraph()

# Pass 1: Add all files as nodes
for file in parsed_files:
    graph.add_node(file.path)

# Pass 2: Add edges from imports
for file in parsed_files:
    for imported_module in file.imports:
        target_file = resolve_import(imported_module)  # Fuzzy matching
        if target_file:
            graph.add_edge(file.path, target_file)

# Detect cycles
cycles = list(nx.simple_cycles(graph))
# Output: [[file1, file2, file1], [file3, file4, file5, file3], ...]
```

### Coupling Metrics Formula

```
Fan-In(f)      = number of files importing f
Fan-Out(f)     = number of files that f imports
Instability(f) = Fan-Out(f) / (Fan-In(f) + Fan-Out(f))
                 ↑ Range: [0, 1]
                 ↑ 0 = stable (many dependents, few dependencies)
                 ↑ 1 = unstable (few dependents, many dependencies)
```

### Blast Radius Computation

```python
def get_blast_radius(target_file, change_type="modify", depth=3):
    """
    Transitive closure of dependents if target_file changes.
    
    Types:
    - "modify": All files that directly/indirectly depend on target_file
    - "delete": Same as modify (file goes away)
    - "move": Same as modify (imports may break)
    """
    affected = set()
    for level in range(1, depth + 1):
        # Find nodes reachable from target_file in reverse (who depends on it?)
        reachable = nx.ancestors(graph, target_file)  # All nodes that can reach target
        affected.update(reachable)
    return affected
```

### What to Explain in AI Concept Presentation

1. **Directed Graphs in Code Analysis** — Modeling imports as edges
2. **Cycle Detection Algorithms:**
   - Johnson's algorithm: Finding all elementary cycles
   - Tarjan's algorithm: Finding SCCs
   - Use cases: Circular dependency detection
3. **Coupling Metrics** — Fan-In/Fan-Out, Instability, cohesion measures
4. **Transitive Closure & Reachability** — Understanding cascading impacts
5. **Performance Considerations** — Scaling to large codebases (1000+ files)
6. **Visualization** — Graph layouts (force-directed, hierarchical) for frontend

---

## 👤 Person 4: LLM & RAG Engineer

**AI Concept to Explain:** `Large Language Model (LLM) Reasoning & Retrieval-Augmented Generation (RAG)`

### Responsibilities

| Task | Priority | Details |
|---|---|---|
| Generate architecture explanations | HIGH | Use LLM to describe overall codebase structure |
| Explain blast radius impact | HIGH | Describe cascading effects of changes |
| Analyze function behavior | MEDIUM | Generate docstring-style explanations for functions |
| Retrieve relevant code context | HIGH | Use Graphify + Neo4j to augment LLM prompts |
| Implement prompt engineering | HIGH | Design prompts for accuracy, prevent hallucination |
| Cache LLM responses | MEDIUM | Store in Neo4j Snapshots to avoid redundant API calls |

### Core Files

| File | Role |
|---|---|
| `backend/src/reasoning/llm_reasoner.py` | **Main file** — LLM prompting, response parsing |
| `backend/src/retrieval/retrieval_engine.py` | Hybrid retrieval (Neo4j + Graphify) |
| `backend/src/retrieval/graphify_retriever.py` | Token-based relevance scoring from Graphify |

### LLM Prompting Techniques

#### 1. **Structured Output Forcing**
```python
prompt = """
Analyze the codebase and provide a report.

## Overview
[Describe the purpose and high-level architecture]

## Modules
[List major modules and their responsibilities]

## Key Files
[Identify the most important files and why]
"""
# Parse response by splitting on "## Overview", "## Modules", "## Key Files"
```

#### 2. **Evidence Grounding**
```python
prompt = f"""
Given the following code structure:
{evidence}  # Actual function names, file paths, imports from graph

Explain how these components interact to achieve the system's goals.
Cite specific function and class names when possible.
"""
```

#### 3. **Token Budget Control**
```python
response = client.messages.create(
    model="llama-3.3-70b-versatile",
    max_tokens=1200,  # Prevent verbose outputs
    temperature=0.3,  # Low temperature for factual analysis
    messages=[...],
)
```

#### 4. **Retrieval-Augmented Generation Flow**
```
User Query
    ↓
GraphifyRetriever.get_context_for_query()
    ├─ Score all Graphify nodes by token similarity
    ├─ Get top-K nodes
    └─ Boost nodes whose files appear in Neo4j dependency graph
    ↓
Evidence Assembly
    ├─ Merge Graphify structural context
    ├─ Add Neo4j dependency context
    └─ Create consolidated evidence string
    ↓
LLMReasoner.explain_*()
    ├─ Build prompt with evidence
    ├─ Call Groq API
    ├─ Parse response into structured sections
    └─ Cache in Neo4j Snapshot
```

### Key Methods to Implement

| Method | Purpose |
|---|---|
| `explain_architecture_report()` | Generate full architecture overview |
| `explain_impact_with_graph()` | Explain blast radius changes |
| `explain_function()` | Analyze single function purpose and impact |
| `explain_meso_level()` | Module-level architecture description |
| `explain_micro_level()` | File-level details |
| `_call_llm_with_limit()` | API call with token budgeting |

### Prompt Examples

#### Architecture Report Prompt
```
You are a code architecture analyzer. Given the following codebase structure:

FILES:
{file_list}

DEPENDENCIES:
{dependency_edges}

FUNCTIONS & CLASSES:
{symbol_list}

Create a detailed architecture report with these sections:

## Overview
Explain what this codebase does and its primary purpose.

## Modules
List the major functional modules and their responsibilities.

## Key Files
Identify the most critical files and explain why they're important.
```

#### Blast Radius Prompt
```
If a developer modifies {target_file}, which files are affected?

DIRECT DEPENDENTS (files that import {target_file}):
{direct_dependents}

INDIRECT DEPENDENTS (files that import the above, 2 hops away):
{indirect_dependents}

Explain the cascading impact and what could break.
```

### What to Explain in AI Concept Presentation

1. **What is an LLM?** — Transformer architecture, token prediction, few-shot learning
2. **Prompt Engineering Techniques:**
   - Chain-of-thought prompting
   - In-context examples (few-shot learning)
   - Instruction clarity and role-playing
3. **RAG (Retrieval-Augmented Generation):**
   - Why augment? — Reduce hallucination, ground answers in facts
   - Retrieval strategies: Dense vs. sparse, token-based vs. semantic
4. **Hallucination Prevention:**
   - Evidence grounding (cite actual symbols from code)
   - Temperature tuning (lower = more factual)
   - Token budgets (concise, focused outputs)
5. **Caching Strategy** — When to cache LLM responses to save API costs
6. **Evaluation** — How to measure quality of generated explanations

---

## 👤 Person 5: Frontend & Pattern Detection Engineer

**AI Concept to Explain:** `Heuristic Pattern Classification & Confidence Analysis`

### Responsibilities

| Task | Priority | Details |
|---|---|---|
| Build React UI | HIGH | All components for visualization and user interaction |
| Detect architectural patterns | HIGH | Classify code into 8 pattern categories (MVC, Microservices, etc.) |
| Compute confidence scores | HIGH | Calculate certainty of pattern detections |
| Validate pattern evidence | MEDIUM | Check signal thresholds for each pattern |
| Visualize graphs | HIGH | Render dependency graph, function call graph with D3.js or similar |
| Version comparison UI | MEDIUM | Show diff between snapshots and commits |

### Core Files

| File | Role |
|---|---|
| `frontend/src/components/PatternDetection.js` | Display detected patterns and confidence |
| `frontend/src/components/ArchitectureView.js` | Show architecture explanations |
| `frontend/src/components/DependencyGraph.js` | Interactive graph visualization |
| `frontend/src/components/BlastRadius.js` | Change impact visualization |
| `backend/src/analysis/confidence_analyzer.py` | Confidence scoring logic |
| `backend/src/graph/analyzers.py` | `PatternDetector` class |

### 8 Architectural Patterns to Detect

| # | Pattern | Detection Signals | Confidence Tiers |
|---|---|---|---|
| 1 | **Layered (N-tier)** | `controller/`, `service/`, `repository/` dirs + framework imports | 0.50 (1 layer) → 0.90 (3+ verified) |
| 2 | **MVC** | `*_controller.py`, `*_model.py`, `*_view.py` files + render/route functions | 0.50 (naming only) → 0.90 (all 3 + edges) |
| 3 | **Hexagonal (Ports & Adapters)** | `port/`, `adapter/`, `domain/` dirs + interface/abstract classes | 0.50 (dirs exist) → 0.90 (verified isolation) |
| 4 | **Event-Driven** | `*_event.py`, `*_subscriber.py` files + publish/subscribe functions | 0.50 (naming) → 0.90 (events + publishers + subscribers) |
| 5 | **Pipe-Filter** | `pipeline/`, `filters/` dirs + process/transform/pipe functions | 0.50 (naming) → 0.90 (pipelines + filters verified) |
| 6 | **Client-Server** | Flask/FastAPI imports (server); requests/axios (client) | 0.50 (1 type) → 0.90 (both + edges) |
| 7 | **Microkernel** | `core/kernel.py`, `plugins/` dir + register/dispatch functions | 0.50 (core exists) → 0.90 (core + 2+ plugins) |
| 8 | **Microservices** | Multiple `service_*.py` files or FastAPI apps + API gateway | 0.50 (1-2 services) → 0.90 (3+ services + gateway) |

### Pattern Detection Algorithm (Example: MVC)

```python
def detect_mvc(graph_db, files, functions):
    """
    Multi-signal heuristic classification for MVC pattern.
    Returns: (detected: bool, confidence: float, evidence: dict)
    """
    
    # Signal 1: File naming patterns
    controllers = [f for f in files if '_controller' in f.lower()]
    models = [f for f in files if '_model' in f.lower()]
    views = [f for f in files if '_view' in f.lower()]
    has_mvc_naming = len(controllers) > 0 and len(models) > 0
    
    # Signal 2: Framework imports
    has_web_framework = any(
        'flask' in f.imports or 'django' in f.imports or 'fastapi' in f.imports
        for f in files
    )
    
    # Signal 3: Function patterns
    render_funcs = [fn for fn in functions if 'render' in fn.name.lower()]
    route_funcs = [fn for fn in functions if 'route' in fn.name.lower()]
    has_mvc_functions = len(render_funcs) > 0 and len(route_funcs) > 0
    
    # Signal 4: Verified edges (Controller→Model dependency)
    controller_model_links = 0
    for controller in controllers:
        for model in models:
            if depends_on(graph_db, controller, model):
                controller_model_links += 1
    
    # Confidence tiering
    has_mvc = has_mvc_naming or (has_web_framework and has_mvc_functions)
    
    if has_mvc and len(views) >= 2 and controller_model_links > 0:
        confidence = 0.90  # Strong
    elif has_mvc and controller_model_links > 0:
        confidence = 0.75  # Good
    elif has_mvc and len(views) >= 1:
        confidence = 0.65  # Moderate
    elif has_mvc:
        confidence = 0.50  # Weak
    else:
        confidence = 0.0
    
    return {
        'detected': confidence >= 0.50,
        'confidence': confidence,
        'evidence': {
            'controllers': len(controllers),
            'models': len(models),
            'views': len(views),
            'controller_model_links': controller_model_links,
        }
    }
```

### Confidence Analysis Metrics

```python
class ConfidenceAnalyzer:
    def compute_report(self):
        """Generate confidence scores for all architectural claims."""
        return {
            'pattern_detection_confidence': {
                'MVC': 0.85,
                'Layered': 0.70,
                ...
            },
            'coverage': {
                'files_analyzed': 45,
                'functions_analyzed': 230,
                'coverage_percentage': 98.5
            },
            'limitations': [
                "Could not resolve 2 external imports",
                "5 files use dynamic imports (not captured)",
                "LLM temperature=0.3 may under-report complex patterns"
            ],
            'recommendations': [
                "Add more test coverage for edge-case imports",
                "Verify pattern detections manually for microservices"
            ]
        }
```

### Frontend Components Structure

| Component | Purpose |
|---|---|
| `AnalyzeRepo.js` | Input form for GitHub URL / local path |
| `ArchitectureView.js` | Display architecture explanation |
| `PatternDetection.js` | Show detected patterns with confidence bars |
| `DependencyGraph.js` | Interactive visualization of file dependencies |
| `FunctionGraph.js` | Call graph visualization |
| `BlastRadius.js` | Change impact visualization |
| `CouplingAnalysis.js` | Show Fan-In/Fan-Out metrics |
| `ConfidenceReport.js` | Limitations and recommendations |
| `SnapshotComparison.js` | Diff two analysis snapshots |

### What to Explain in AI Concept Presentation

1. **Heuristic vs. Statistical Classification:**
   - Why not ML (overfitting, training data scarcity)?
   - Why heuristics work for code patterns (domain-specific rules)
2. **Multi-Signal Decision Making:**
   - Combining signals (filename + imports + functions + graph edges)
   - Why ensemble heuristics are powerful
3. **Confidence Scoring Framework:**
   - Tier-based confidence (weak → moderate → good → strong)
   - Evidence thresholds for each tier
4. **Architectural Pattern Theory:**
   - The 8 patterns: their history, trade-offs, use cases
   - When MVC is appropriate vs. microservices vs. hexagonal
5. **Limitations & Uncertainty:**
   - What patterns can't be detected from static analysis
   - Dynamic imports, runtime polymorphism, configuration-driven behavior
6. **Validation Strategy** — How to validate pattern detections (manual inspection, automated tests)

---

## 🔄 Communication & Integration Points

### Person 1 → Person 2
- **Artifact:** Extracted symbol dictionary (functions, classes, imports)
- **Handoff:** `StaticParser` output → `GraphDB.add_file()`

### Person 2 → Person 3
- **Artifact:** Neo4j dependency graph (nodes & edges)
- **Handoff:** Cypher queries → NetworkX DiGraph construction

### Person 3 → Person 4
- **Artifact:** Graph metrics (cycles, coupling, blast radius) + structured data
- **Handoff:** Metrics & evidence → LLMReasoner prompts

### Person 4 → Person 5
- **Artifact:** LLM explanations + evidence-grounded facts
- **Handoff:** Explanations → Frontend visualization

### Person 5 → Persons 1-4
- **Artifact:** User queries, selected files for analysis
- **Handoff:** UI interactions → Backend API calls → Pipeline restart

---

## 🎓 AI Concept Presentation Guide

Each person should prepare a **10-15 minute presentation** on their AI concept:

### Presentation Structure
1. **Introduction** (2 min) — What is the concept? Why is it used?
2. **How It Works** (5 min) — Core algorithm, formulas, step-by-step example
3. **In ARCHITECH** (3 min) — How it's used in this codebase
4. **Demo** (3 min) — Show a live or recorded example
5. **Q&A** (2 min) — Questions from team

### Suggested Topics for Deep Dives

| Person | Potential Deep Dives |
|---|---|
| Person 1 (AST) | Tree-sitter internals, multi-language parsing, error recovery |
| Person 2 (Graphs) | Neo4j performance tuning, graph index strategies, Cypher optimization |
| Person 3 (Algorithms) | Cycle detection algorithms, complexity analysis, scalability limits |
| Person 4 (LLM) | Transformer architecture, attention mechanisms, fine-tuning strategies |
| Person 5 (Patterns) | Design pattern theory, architectural decision records (ADRs), pattern languages |

---

## 📊 Sprint Planning Guide

### Sprint 1: Foundation (Person 1 & 2)
- [ ] Person 1: Complete AST extraction for Python files
- [ ] Person 2: Design and populate Neo4j schema with extracted data
- **Deliverable:** Repository → File → Function node structure in Neo4j

### Sprint 2: Analysis (Person 3)
- [ ] Build NetworkX dependency graph
- [ ] Implement cycle detection
- [ ] Compute coupling metrics
- **Deliverable:** Cycle report, coupling analysis scores

### Sprint 3: Intelligence (Person 4)
- [ ] Implement RAG retrieval pipeline
- [ ] Set up LLM prompting
- [ ] Generate architecture reports
- **Deliverable:** LLM explanations cached in Neo4j

### Sprint 4: UI (Person 5)
- [ ] Pattern detection implementation
- [ ] React components for visualization
- [ ] Confidence scoring display
- **Deliverable:** Full frontend with interactive graphs

### Sprint 5: Integration & Polish
- [ ] All components integrated and tested
- [ ] Performance optimization
- [ ] AI concept presentations

---

## 💡 Tips for Team Collaboration

1. **Daily Standups** — 15 min each morning covering blockers and progress
2. **Code Reviews** — Each person reviews PRs from adjacent roles
3. **Shared Documentation** — Update README and this file as you progress
4. **Testing** — Unit tests for each module, integration tests across boundaries
5. **Demo Sessions** — Weekly demos of working features to team
6. **Knowledge Sharing** — Cross-train on each other's components

---

## 📚 References

- [AI Concepts Document](./AI_CONCEPTS_AND_ALGORITHMS.md) — Detailed algorithm explanations
- [README](./README.md) — Project overview and tech stack
- [Neo4j Documentation](https://neo4j.com/docs/)
- [NetworkX Documentation](https://networkx.org/)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Groq API Docs](https://console.groq.com/docs)
- [React Documentation](https://react.dev/)
