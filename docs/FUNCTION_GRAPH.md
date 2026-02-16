# Function-Based Graph Visualization

## Overview
Added function-level graph visualization to complement the existing file-based dependency graphs. This allows developers to understand function call relationships and trace execution paths through the codebase.

## Features

### 1. Function Call Graph
- **Endpoint**: `GET /graph/functions`
- **Description**: Returns all functions and their call relationships
- **Visualization**: Interactive D3.js graph showing:
  - 🟠 Orange nodes = Functions
  - 🔵 Blue nodes = Files that call functions
  - Arrows show call direction

### 2. Function Call Chain
- **Endpoint**: `GET /graph/function/{function_name}`
- **Description**: Returns call chain for a specific function (up to 3 levels deep)
- **Use Case**: Trace who calls a specific function

### 3. Function List
- **Endpoint**: `GET /functions`
- **Description**: Lists all functions with file and line information
- **Use Case**: Browse available functions in the codebase

## Frontend Components

### FunctionGraph Component
Located: `frontend/src/components/FunctionGraph.js`

**Features**:
- Dropdown to select specific function or view all
- Color-coded nodes (functions vs files)
- Interactive drag-and-drop
- Zoom and pan support
- Tooltips showing file path and line numbers
- Auto-fit to viewport

## Backend Implementation

### FunctionGraphBuilder Class
Located: `backend/src/graph/function_graph.py`

**Methods**:
- `get_function_graph_data(limit)`: Get all function relationships
- `get_function_call_chain(function_name, depth)`: Get call chain for specific function

### Neo4j Queries
Uses existing graph structure:
- `Function` nodes (created during parsing)
- `CALLS` relationships (file → function)
- `CONTAINS` relationships (file → function)

## Usage

### Frontend
1. Navigate to "Function Graph" tab
2. View all functions or select specific function from dropdown
3. Interact with graph (drag, zoom, pan)
4. Hover over nodes for details

### API Examples

```bash
# Get all function relationships
curl http://localhost:8000/graph/functions

# Get call chain for specific function
curl http://localhost:8000/graph/function/calculate_metrics

# List all functions
curl http://localhost:8000/functions
```

## Comparison: File Graph vs Function Graph

| Feature | File Graph | Function Graph |
|---------|-----------|----------------|
| Granularity | File-level | Function-level |
| Nodes | Files | Functions + Files |
| Edges | File dependencies | Function calls |
| Use Case | Architecture overview | Execution flow |
| Color | Blue only | Orange (functions) + Blue (files) |

## Technical Details

### Graph Structure
```
File (Blue) --CALLS--> Function (Orange)
File --CONTAINS--> Function
```

### Data Format
```json
{
  "nodes": [
    {
      "id": "path/to/file.py::function_name",
      "label": "function_name",
      "file": "path/to/file.py",
      "line": 42,
      "type": "function"
    }
  ],
  "edges": [
    {
      "source": "caller_file.py::caller",
      "target": "path/to/file.py::function_name",
      "type": "calls"
    }
  ]
}
```

## Future Enhancements
- [ ] Function-to-function calls (not just file-to-function)
- [ ] Call depth visualization (color intensity)
- [ ] Filter by file or module
- [ ] Export call graph as image
- [ ] Integration with impact analysis
- [ ] Show function parameters and return types
