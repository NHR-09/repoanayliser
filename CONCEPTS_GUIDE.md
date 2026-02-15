# ARCHITECH - Concepts & Terminology Guide

## 📚 Table of Contents
1. [Project Overview](#project-overview)
2. [Architectural Patterns](#architectural-patterns)
3. [Coupling Metrics](#coupling-metrics)
4. [Dependency Analysis](#dependency-analysis)
5. [Graph Theory Concepts](#graph-theory-concepts)
6. [Technical Terms](#technical-terms)

---

## 🎯 Project Overview

**ARCHITECH** is an automated architectural recovery system that analyzes source code repositories to:
- Extract architectural patterns
- Detect dependencies and coupling
- Predict change impact (blast radius)
- Generate evidence-based explanations

### How It Works
```
Source Code → Parse (AST) → Graph Storage → Pattern Detection → AI Reasoning → Insights
```

---

## 🏛️ Architectural Patterns

### 1. **Layered Architecture**
Organizes code into horizontal layers, each with specific responsibilities.

**Layers:**
- **Presentation Layer**: UI, views, controllers (user-facing)
- **Business Logic Layer**: Core application logic, services
- **Data Access Layer**: Database operations, repositories
- **Infrastructure Layer**: External services, utilities

**Example:**
```
/presentation
  - views.py
  - controllers.py
/business
  - services.py
  - validators.py
/data
  - models.py
  - repositories.py
```

**Detection:** Files grouped by directory names like `views/`, `services/`, `models/`

---

### 2. **MVC (Model-View-Controller)**
Separates application into three interconnected components.

**Components:**
- **Model**: Data structure and business logic (`User`, `Product`)
- **View**: UI presentation (`user_view.html`, `dashboard.jsx`)
- **Controller**: Handles requests, coordinates Model & View (`UserController`)

**Example:**
```python
# Model
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

# Controller
class UserController:
    def get_user(self, user_id):
        user = User.get_by_id(user_id)
        return render_view('user_view', user)

# View
# user_view.html
<h1>{{ user.name }}</h1>
```

**Detection:** Files named `*Controller`, `*Model`, `*View` or directories with these names

---

### 3. **Hexagonal Architecture (Ports & Adapters)**
Isolates core business logic from external dependencies.

**Structure:**
- **Core/Domain**: Business logic (independent)
- **Ports**: Interfaces for communication
- **Adapters**: Implementations (database, API, UI)

**Example:**
```
/core
  - domain_logic.py
/ports
  - user_repository_interface.py
/adapters
  - postgres_user_repository.py
  - rest_api_adapter.py
```

**Detection:** Directories named `core/`, `domain/`, `ports/`, `adapters/`

---

### 4. **Event-Driven Architecture**
Components communicate through events.

**Components:**
- **Event Producers**: Emit events (`OrderPlaced`)
- **Event Consumers**: React to events (`SendEmailHandler`)
- **Event Bus**: Routes events

**Example:**
```python
# Producer
event_bus.publish('OrderPlaced', order_data)

# Consumer
@event_bus.subscribe('OrderPlaced')
def send_confirmation_email(order_data):
    email.send(order_data['customer_email'])
```

**Detection:** Files with `event`, `handler`, `subscriber`, `publisher` in names

---

## 📊 Coupling Metrics

### **Fan-In**
Number of modules/files that **depend on** a given module.

**High Fan-In = Good** (reusable, stable component)

**Example:**
```
utils.py ← auth.py
         ← user_service.py
         ← order_service.py
```
`utils.py` has **fan-in = 3** (3 files depend on it)

**Interpretation:**
- High fan-in: Core utility, widely used
- Changes require careful testing (many dependents)

---

### **Fan-Out**
Number of modules/files that a given module **depends on**.

**High Fan-Out = Bad** (tightly coupled, fragile)

**Example:**
```
main.py → database.py
        → auth.py
        → logger.py
        → config.py
        → utils.py
```
`main.py` has **fan-out = 5** (depends on 5 files)

**Interpretation:**
- High fan-out: Complex, hard to maintain
- Changes in dependencies break this file

---

### **Coupling Score**
Combined metric: `coupling = fan-in + fan-out`

**Ideal:**
- **Low fan-out** (few dependencies)
- **Moderate fan-in** (reusable but not critical)

**Risk Levels:**
- `coupling < 5`: Low risk
- `5 ≤ coupling ≤ 10`: Medium risk
- `coupling > 10`: High risk (refactor candidate)

---

## 🔗 Dependency Analysis

### **Direct Dependencies**
Files directly imported by a module.

**Example:**
```python
# main.py
import database
from auth import login
```
Direct dependencies: `database`, `auth`

---

### **Transitive Dependencies**
Dependencies of dependencies (indirect).

**Example:**
```
main.py → auth.py → database.py → config.py
```
`main.py` transitively depends on `database.py` and `config.py`

---

### **Circular Dependencies**
Two or more modules depend on each other (cycle).

**Example:**
```
user.py → order.py → user.py  ❌ BAD
```

**Problems:**
- Import errors
- Hard to test
- Tight coupling

**Solution:** Introduce interface/abstraction to break cycle

---

### **Blast Radius**
Files affected when a target file changes.

**Calculation:**
1. Find all files that import the target (direct)
2. Find files that import those files (transitive)
3. Limit depth (e.g., 3 levels)

**Example:**
```
Change auth.py
  ↓
Affects: login.py, middleware.py
  ↓
Affects: routes.py, app.py
```
Blast radius = `[login.py, middleware.py, routes.py, app.py]`

**Risk Assessment:**
- `< 5 files`: Low risk
- `5-10 files`: Medium risk
- `> 10 files`: High risk (critical component)

---

## 🕸️ Graph Theory Concepts

### **Directed Graph (DiGraph)**
Nodes connected by directional edges.

**In ARCHITECH:**
- **Nodes**: Files, classes, functions
- **Edges**: Dependencies (imports, calls)

**Example:**
```
A → B → C
↓       ↑
D ------┘
```

---

### **Strongly Connected Components (SCC)**
Subgraph where every node can reach every other node.

**Example:**
```
A → B → C → A  (SCC: {A, B, C})
```

**Interpretation:** Tightly coupled modules (refactor candidate)

---

### **Shortest Path**
Minimum number of edges between two nodes.

**Use Case:** Calculate blast radius depth

---

## 🔧 Technical Terms

### **AST (Abstract Syntax Tree)**
Tree representation of source code structure.

**Example:**
```python
x = 5 + 3
```
AST:
```
Assignment
├── Variable: x
└── BinaryOp: +
    ├── Literal: 5
    └── Literal: 3
```

**Tool Used:** Tree-sitter

---

### **Static Analysis**
Analyzing code without executing it.

**ARCHITECH uses:**
- Parse files → Extract imports, classes, functions
- Build dependency graph
- Detect patterns

---

### **Semantic Search**
Search by meaning, not keywords.

**Example:**
- Query: "authentication logic"
- Finds: `login()`, `verify_token()`, `check_permissions()`

**Tool Used:** ChromaDB (vector embeddings)

---

### **Graph Database**
Database optimized for relationships.

**ARCHITECH uses Neo4j:**
```cypher
MATCH (f:File)-[:IMPORTS]->(m:Module)
WHERE f.path = 'main.py'
RETURN m.name
```

---

### **Vector Embeddings**
Numerical representation of text for similarity search.

**Example:**
```
"user authentication" → [0.2, 0.8, 0.1, ...]
"login system"        → [0.3, 0.7, 0.2, ...]  (similar)
```

---

## 📈 Metrics Summary

| Metric | Good Range | Interpretation |
|--------|-----------|----------------|
| **Fan-In** | 3-10 | Reusable component |
| **Fan-Out** | 0-5 | Low coupling |
| **Coupling** | < 10 | Maintainable |
| **Blast Radius** | < 5 files | Low impact |
| **Cyclomatic Complexity** | < 10 | Simple logic |

---

## 🎓 Key Takeaways

1. **Layered Architecture**: Horizontal separation (UI, logic, data)
2. **MVC**: Separation of concerns (Model, View, Controller)
3. **Fan-In**: How many depend on you (reusability)
4. **Fan-Out**: How many you depend on (coupling)
5. **Blast Radius**: Impact of changes (risk assessment)
6. **Circular Dependencies**: Mutual dependencies (anti-pattern)
7. **SCC**: Tightly coupled clusters (refactor targets)

---

## 🔍 How ARCHITECH Uses These Concepts

1. **Parse Code** → Extract classes, functions, imports
2. **Build Graph** → Create nodes (files) and edges (dependencies)
3. **Calculate Metrics** → Fan-in, fan-out, coupling
4. **Detect Patterns** → Layered, MVC, Hexagonal
5. **Analyze Impact** → Blast radius for change prediction
6. **Generate Insights** → AI-powered explanations with evidence

---

## 📖 Further Reading

- **Design Patterns**: Gang of Four (GoF) book
- **Clean Architecture**: Robert C. Martin
- **Graph Theory**: Introduction to Algorithms (CLRS)
- **Software Metrics**: Code Complete by Steve McConnell

---

**Built for PS-10: Architectural Recovery Challenge** 🚀
