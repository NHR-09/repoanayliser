# ARCHITECH - Complete System Architecture

## 🏗️ Full Stack Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│                     http://localhost:3000                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTP/REST
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    REACT FRONTEND                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    App.js (Main)                     │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │         Tab Navigation System                  │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ AnalyzeRepo  │  │  Patterns    │  │  Coupling    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Impact     │  │Architecture  │  │    Graph     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Service (Axios)                     │  │
│  │  - analyzeRepo()    - getPatterns()                 │  │
│  │  - getCoupling()    - analyzeImpact()               │  │
│  │  - getArchitecture() - getBlastRadius()             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTP/REST API
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   FASTAPI BACKEND                           │
│                  http://localhost:8000                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   main.py (API)                      │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │  POST /analyze          GET /patterns          │ │  │
│  │  │  GET  /status/{id}      GET /coupling          │ │  │
│  │  │  POST /impact           GET /architecture      │ │  │
│  │  │  GET  /dependencies     GET /blast-radius      │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Analysis Engine                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐   │  │
│  │  │  Parser    │  │  Pattern   │  │  Coupling  │   │  │
│  │  │(Tree-sitter)│  │  Detector  │  │  Analyzer  │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘   │  │
│  │                                                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐   │  │
│  │  │ Dependency │  │  Retrieval │  │  Reasoning │   │  │
│  │  │   Mapper   │  │   System   │  │   Engine   │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
             │                        │
    ┌────────▼────────┐      ┌───────▼────────┐
    │   Neo4j Graph   │      │  ChromaDB      │
    │   Database      │      │  Vector Store  │
    │  localhost:7474 │      │  (Embeddings)  │
    │                 │      │                │
    │  • Files        │      │  • Code chunks │
    │  • Classes      │      │  • Semantic    │
    │  • Functions    │      │    search      │
    │  • Imports      │      │                │
    └─────────────────┘      └────────────────┘
```

## 🔄 Data Flow

### 1. Repository Analysis Flow
```
User Input (GitHub URL)
    ↓
Frontend: AnalyzeRepo Component
    ↓
API: POST /analyze
    ↓
Backend: Analysis Engine
    ↓
Clone Repository → Parse Files → Extract AST
    ↓
Store in Neo4j (Graph) + ChromaDB (Vectors)
    ↓
Return Job ID
    ↓
Frontend: Poll Status (every 2s)
    ↓
Backend: Check Job Status
    ↓
Frontend: Display Completion → Navigate to Patterns
```

### 2. Pattern Detection Flow
```
User: Click Patterns Tab
    ↓
Frontend: PatternDetection Component
    ↓
API: GET /patterns
    ↓
Backend: Pattern Detector
    ↓
Query Neo4j for Structure
    ↓
Analyze: Layered, MVC, Hexagonal
    ↓
Calculate Confidence Scores
    ↓
Return Pattern Data (JSON)
    ↓
Frontend: Display Patterns with Metrics
```

### 3. Coupling Analysis Flow
```
User: Click Coupling Tab
    ↓
Frontend: CouplingAnalysis Component
    ↓
API: GET /coupling
    ↓
Backend: Coupling Analyzer
    ↓
Build Dependency Graph (NetworkX)
    ↓
Calculate: Fan-in, Fan-out, Cycles
    ↓
Identify High Coupling Files
    ↓
Return Coupling Data (JSON)
    ↓
Frontend: Display Metrics + Warnings
```

### 4. Impact Analysis Flow
```
User: Enter File Path
    ↓
Frontend: ImpactAnalysis Component
    ↓
API: POST /impact
    ↓
Backend: Dependency Mapper
    ↓
Query Neo4j for Dependencies
    ↓
Calculate Blast Radius (BFS/DFS)
    ↓
Classify Risk Level
    ↓
Generate AI Explanation (LLM)
    ↓
Return Impact Data (JSON)
    ↓
Frontend: Display Affected Files + Risk
```

### 5. Architecture Explanation Flow
```
User: Click Architecture Tab
    ↓
Frontend: ArchitectureView Component
    ↓
API: GET /architecture
    ↓
Backend: Reasoning Engine
    ↓
Hybrid Retrieval (Vector + Graph)
    ↓
Query ChromaDB (Semantic) + Neo4j (Structural)
    ↓
LLM Reasoning (Macro/Meso/Micro)
    ↓
Generate Explanations with Evidence
    ↓
Return Architecture Data (JSON)
    ↓
Frontend: Display Multi-level Explanations
```

### 6. Graph Visualization Flow
```
User: Click Graph Tab
    ↓
Frontend: DependencyGraph Component
    ↓
API: GET /debug/files
    ↓
Backend: Graph Database
    ↓
Query Neo4j for All Files
    ↓
Return File List (JSON)
    ↓
Frontend: D3.js Force Simulation
    ↓
Render Interactive Graph
    ↓
User: Drag Nodes, Explore
```

## 🎯 Component Communication

```
┌─────────────────────────────────────────────────────┐
│                    App.js                           │
│  ┌───────────────────────────────────────────────┐ │
│  │  State: activeTab, refreshKey                 │ │
│  │  Methods: handleAnalysisComplete()            │ │
│  └───────────────────────────────────────────────┘ │
│                       │                             │
│         ┌─────────────┼─────────────┐              │
│         ▼             ▼             ▼              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Component1│  │Component2│  │Component3│        │
│  │          │  │          │  │          │        │
│  │ Props:   │  │ Props:   │  │ Props:   │        │
│  │ - key    │  │ - key    │  │ - onDone │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │               │
│       └─────────────┼─────────────┘               │
│                     ▼                             │
│              ┌──────────────┐                     │
│              │  api.js      │                     │
│              │  (Axios)     │                     │
│              └──────┬───────┘                     │
└─────────────────────┼─────────────────────────────┘
                      │
                      ▼
              Backend API (FastAPI)
```

## 🗄️ Database Schema

### Neo4j Graph Database
```
(File)-[:CONTAINS]->(Class)
(File)-[:CONTAINS]->(Function)
(File)-[:IMPORTS]->(File)
(Class)-[:CONTAINS]->(Method)
(Function)-[:CALLS]->(Function)
```

### ChromaDB Vector Store
```
Collection: code_chunks
Documents: Code snippets
Embeddings: Semantic vectors
Metadata: File path, type, language
```

## 🔐 Security & CORS

```
Frontend (localhost:3000)
    ↓
CORS Headers
    ↓
Backend (localhost:8000)
    allow_origins: ["*"]
    allow_methods: ["*"]
    allow_headers: ["*"]
```

## 📊 Technology Stack Summary

### Frontend Layer
- React 18.2.0 (UI Framework)
- Axios 1.6.0 (HTTP Client)
- D3.js 7.8.5 (Visualization)
- React Scripts 5.0.1 (Build Tools)

### Backend Layer
- FastAPI (REST API)
- Python 3.9+ (Runtime)
- Tree-sitter (Parser)
- NetworkX (Graph Analysis)
- OpenAI/Anthropic (LLM)

### Data Layer
- Neo4j 5.x (Graph Database)
- ChromaDB (Vector Database)

### Infrastructure
- Node.js 16+ (Frontend Runtime)
- Docker (Neo4j Container)
- Git (Version Control)

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Production Setup                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Frontend (Static Files)                        │
│  ├── Nginx / Apache                             │
│  └── Serve build/ folder                        │
│                                                 │
│  Backend (API Server)                           │
│  ├── Uvicorn / Gunicorn                         │
│  └── Python FastAPI App                         │
│                                                 │
│  Databases                                      │
│  ├── Neo4j (Docker Container)                   │
│  └── ChromaDB (Persistent Volume)               │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 📈 Performance Characteristics

| Component | Load Time | Response Time |
|-----------|-----------|---------------|
| Frontend Initial Load | ~2s | - |
| Tab Switch | <100ms | - |
| API Call | - | 100-500ms |
| Pattern Detection | - | 1-3s |
| Coupling Analysis | - | 1-2s |
| Impact Analysis | - | 500ms-1s |
| Graph Rendering | 500ms-2s | - |
| Repository Analysis | - | 30s-5min |

## 🎯 System Capabilities

✅ Analyze repositories up to 1000 files
✅ Detect 3 architectural patterns
✅ Calculate coupling metrics
✅ Predict change impact
✅ Generate multi-level explanations
✅ Visualize dependencies
✅ Real-time status updates
✅ Evidence-based reasoning

---

**Architecture Type**: Microservices + SPA
**Communication**: REST API
**State Management**: React Hooks
**Data Storage**: Graph + Vector
**Visualization**: D3.js Force-Directed
**Deployment**: Docker + Static Hosting
