# Database Schema Documentation

## Neo4j Graph Database Schema

### Node Types

#### 1. File
Represents source code files.

**Properties:**
- `path` (string): Absolute file path
- `language` (string): Programming language (python, javascript, java)

**Example:**
```cypher
(:File {path: "/src/service.py", language: "python"})
```

#### 2. Class
Represents class definitions.

**Properties:**
- `name` (string): Class name
- `file` (string): File path containing the class
- `line` (int): Line number

**Example:**
```cypher
(:Class {name: "UserService", file: "/src/service.py", line: 10})
```

#### 3. Function
Represents function/method definitions.

**Properties:**
- `name` (string): Function name
- `file` (string): File path containing the function
- `line` (int): Line number

**Example:**
```cypher
(:Function {name: "get_user", file: "/src/service.py", line: 25})
```

#### 4. Module
Represents imported modules.

**Properties:**
- `name` (string): Module name

**Example:**
```cypher
(:Module {name: "flask"})
```

### Relationship Types

#### 1. CONTAINS
File contains class or function.

```cypher
(:File)-[:CONTAINS]->(:Class)
(:File)-[:CONTAINS]->(:Function)
```

#### 2. IMPORTS
File imports a module.

```cypher
(:File)-[:IMPORTS]->(:Module)
```

#### 3. CALLS
Function calls another function (future enhancement).

```cypher
(:Function)-[:CALLS]->(:Function)
```

#### 4. INHERITS
Class inherits from another class (future enhancement).

```cypher
(:Class)-[:INHERITS]->(:Class)
```

### Key Queries

#### Find all dependencies of a file:
```cypher
MATCH (f:File {path: $path})-[:IMPORTS]->(m:Module)
RETURN m.name
```

#### Find files affected by a change:
```cypher
MATCH (target:File {path: $path})
MATCH (f:File)-[:IMPORTS*1..3]->(target)
RETURN DISTINCT f.path
```

#### Find high fan-in files:
```cypher
MATCH (f:File)
WITH f, size((f)<-[:IMPORTS]-()) as fan_in
WHERE fan_in > 5
RETURN f.path, fan_in
ORDER BY fan_in DESC
```

## ChromaDB Vector Database Schema

### Collection: code_embeddings

**Document Structure:**
```json
{
  "id": "file_path:type:name",
  "document": "code snippet or description",
  "metadata": {
    "file_path": "/src/service.py",
    "type": "class|function",
    "name": "UserService"
  }
}
```

**Example Entries:**

```json
{
  "id": "/src/service.py:class:UserService",
  "document": "class UserService at line 10",
  "metadata": {
    "file_path": "/src/service.py",
    "type": "class",
    "name": "UserService"
  }
}
```

```json
{
  "id": "/src/service.py:func:get_user",
  "document": "function get_user at line 25",
  "metadata": {
    "file_path": "/src/service.py",
    "type": "function",
    "name": "get_user"
  }
}
```

### Retrieval Strategy

**Hybrid Retrieval:**
1. Semantic search via ChromaDB (cosine similarity)
2. Structural context via Neo4j (graph traversal)
3. Merge results with boosted scores for structural matches

**Query Flow:**
```
User Query
    ↓
ChromaDB.search(query, n=10)
    ↓
Neo4j.get_dependencies(context_file)
    ↓
Merge & Rank (structural matches get +0.5 score)
    ↓
Return top 5 evidence chunks
```
