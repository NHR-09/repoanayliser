# ARCHITECH Project Structure

```
ARCHITECH/
│
├── backend/                          # Main backend server
│   ├── src/                          # Source code
│   │   ├── api/                      # API routes (future)
│   │   ├── graph/                    # Graph database & analysis
│   │   │   ├── graph_db.py          # Neo4j operations
│   │   │   ├── dependency_mapper.py # NetworkX graph builder
│   │   │   └── analyzers.py         # Pattern & coupling detection
│   │   ├── parser/                   # Code parsing
│   │   │   ├── repo_loader.py       # Git clone & file scanning
│   │   │   └── static_parser.py     # Tree-sitter AST extraction
│   │   ├── retrieval/                # Evidence retrieval
│   │   │   ├── vector_store.py      # ChromaDB operations
│   │   │   └── retrieval_engine.py  # Hybrid retrieval logic
│   │   ├── reasoning/                # LLM integration
│   │   │   └── llm_reasoner.py      # OpenAI/Anthropic wrapper
│   │   ├── analysis_engine.py        # Main orchestrator
│   │   └── config.py                 # Configuration
│   │
│   ├── main.py                       # FastAPI server entry point
│   ├── init_system.py                # Database initialization
│   ├── test_system.py                # System test script
│   ├── requirements.txt              # Python dependencies
│   ├── .env.example                  # Environment template
│   └── workspace/                    # Cloned repositories (created at runtime)
│
├── docs/                             # Documentation
│   ├── API.md                        # API endpoint documentation
│   ├── DATABASE_SCHEMA.md            # Neo4j & ChromaDB schemas
│   ├── SETUP.md                      # Installation guide
│   └── IMPLEMENTATION_STATUS.md      # Feature completion status
│
├── frontend/                         # Frontend (future implementation)
│   └── (React + D3.js visualization)
│
└── README.md                         # Main project documentation
```

## Component Responsibilities

### Core Engine (`analysis_engine.py`)
- Orchestrates entire analysis pipeline
- Coordinates all subsystems
- Manages analysis workflow

### Repository Loader (`parser/repo_loader.py`)
- Clones Git repositories
- Scans for source files
- Filters excluded directories
- Detects programming languages

### Static Parser (`parser/static_parser.py`)
- Tree-sitter integration
- AST extraction
- Class/function detection
- Import statement parsing

### Graph Database (`graph/graph_db.py`)
- Neo4j CRUD operations
- Node creation (File, Class, Function, Module)
- Relationship creation (IMPORTS, CONTAINS)
- Dependency queries
- Affected files traversal

### Dependency Mapper (`graph/dependency_mapper.py`)
- NetworkX graph construction
- Circular dependency detection
- Fan-in/fan-out calculation
- Blast radius computation
- Strongly connected components

### Analyzers (`graph/analyzers.py`)
- **PatternDetector**: Identifies architectural patterns
  - Layered architecture
  - MVC pattern
  - Hexagonal architecture
  - Confidence scoring
- **CouplingAnalyzer**: Measures code coupling
  - High coupling identification
  - Cycle detection
  - Coupling metrics

### Vector Store (`retrieval/vector_store.py`)
- ChromaDB operations
- Code embedding storage
- Semantic similarity search
- Metadata management

### Retrieval Engine (`retrieval/retrieval_engine.py`)
- Hybrid retrieval strategy
- Combines semantic + structural context
- Score boosting for graph matches
- Evidence ranking

### LLM Reasoner (`reasoning/llm_reasoner.py`)
- OpenAI/Anthropic integration
- Evidence-bound prompting
- Architecture explanation generation
- Impact analysis reasoning
- Citation enforcement

### API Server (`main.py`)
- FastAPI application
- 8 REST endpoints
- Background job processing
- CORS configuration

## Data Flow

```
1. Repository URL
   ↓
2. repo_loader.clone_repository()
   ↓
3. repo_loader.scan_files()
   ↓
4. static_parser.parse_file() [for each file]
   ↓
5. graph_db.create_*_node() + vector_store.add_batch()
   ↓
6. dependency_mapper.build_graph()
   ↓
7. PatternDetector.detect_patterns()
   ↓
8. CouplingAnalyzer.analyze()
   ↓
9. User Query
   ↓
10. retrieval_engine.retrieve_evidence()
    ↓
11. llm_reasoner.explain_*()
    ↓
12. JSON Response
```

## Database Schemas

### Neo4j Nodes
- `File`: {path, language}
- `Class`: {name, file, line}
- `Function`: {name, file, line}
- `Module`: {name}

### Neo4j Relationships
- `(File)-[:CONTAINS]->(Class|Function)`
- `(File)-[:IMPORTS]->(Module)`

### ChromaDB Documents
- ID: `file_path:type:name`
- Document: Code snippet
- Metadata: {file_path, type, name}

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| POST /analyze | Start analysis job |
| GET /status/{id} | Check job status |
| GET /architecture | Get AI explanation |
| GET /patterns | Get detected patterns |
| GET /coupling | Get coupling metrics |
| POST /impact | Analyze change impact |
| GET /dependencies/{path} | Get file deps |
| GET /blast-radius/{path} | Get affected files |

## Configuration

### Environment Variables (.env)
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CHROMA_PERSIST_DIR=./chroma_db
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Runtime Directories

Created automatically:
- `workspace/` - Cloned repositories
- `chroma_db/` - Vector database storage

## Key Design Decisions

1. **Monolithic Backend**: Single process for shared memory access
2. **Dual Databases**: Neo4j for structure, ChromaDB for semantics
3. **Hybrid Retrieval**: Combines vector similarity + graph traversal
4. **Evidence Binding**: LLM only sees retrieved code chunks
5. **Async Jobs**: Background processing prevents timeouts
6. **Tree-sitter**: Language-agnostic parsing
7. **NetworkX**: In-memory graph for fast analysis

## Testing

```bash
# Initialize databases
python init_system.py

# Start server
python main.py

# Run tests
python test_system.py
```

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- FastAPI (API framework)
- Tree-sitter (parsing)
- Neo4j driver (graph DB)
- ChromaDB (vector DB)
- NetworkX (graph analysis)
- OpenAI/Anthropic (LLM)
