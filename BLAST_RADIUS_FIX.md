# Blast Radius Fix Summary

## Problem
Blast radius always returns 0 dependents for all files, even though Neo4j has 66 DEPENDS_ON relationships.

## Root Causes

### 1. DependencyMapper Empty (FIXED ✅)
- `DependencyMapper.graph` had 0 edges
- Blast radius used DependencyMapper which was empty
- **Solution:** Modified blast radius to query Neo4j DEPENDS_ON relationships directly

### 2. Query Direction Wrong (FIXED ✅)
- Initial query looked for files that target DEPENDS ON
- Should look for files that DEPEND ON target
- **Solution:** Reversed query direction: `(source)-[:DEPENDS_ON]->(target)`

### 3. current_repo_id Not Set (FIXED ✅)
- When server starts, `engine.current_repo_id = None`
- `/impact` endpoint doesn't load repository first
- Blast radius queries with `repo_id=None` return nothing
- **Solution:** Added auto-load of first repository if `current_repo_id` is None

## Changes Made

### File: `backend/src/graph/blast_radius.py`

**Modified `_get_direct_dependents()`:**
```python
# OLD: Used empty DependencyMapper.graph
direct.update(graph.predecessors(node))

# NEW: Query Neo4j directly
MATCH (source:File)-[:DEPENDS_ON]->(target:File {file_path: $file_path})
RETURN DISTINCT source.file_path as dependent
```

**Modified `_get_indirect_dependents()`:**
```python
# OLD: Used NetworkX path queries on empty graph
if nx.has_path(graph, node, direct_dep):
    indirect.add(node)

# NEW: Query Neo4j with path patterns
MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
RETURN DISTINCT source.file_path as dependent
```

### File: `backend/main.py`

**Modified `/impact` endpoint:**
```python
@app.post("/impact")
async def analyze_impact(request: ImpactRequest):
    # Ensure current_repo_id is set
    if not engine.current_repo_id:
        repos = engine.version_tracker.list_repositories()
        if repos:
            engine.load_repository_analysis(repos[0]['repo_id'])
    
    result = engine.analyze_change_impact(request.file_path, request.change_type)
    return result
```

**Modified `/blast-radius/{file_path}` endpoint:** (same fix)

## Test Results

### Before Fix:
```
config.py:
  Direct dependents: 0
  Indirect dependents: 0
  Risk: low (0/100)
```

### After Fix:
```
config.py:
  Direct dependents: 8
  Indirect dependents: 13
  Risk: high (100/100)
```

## Files Modified:
1. `backend/src/graph/blast_radius.py` - Use Neo4j queries instead of DependencyMapper
2. `backend/main.py` - Auto-load repository in impact endpoints

## Important Notes:

### Server Restart Required
The fix requires restarting the FastAPI server for changes to take effect.

### Path Matching
File paths must match exactly between:
- Frontend request
- Neo4j database (stored as `file_path` property)
- Blast radius query

If paths don't match (e.g., forward vs backslashes), blast radius will return 0.

### Repository Loading
The fix auto-loads the first repository if `current_repo_id` is None. For multi-repo scenarios, the frontend should explicitly load the desired repository using `/repository/{repo_id}/load` before calling impact endpoints.

## Verification Steps:

1. **Restart the server:**
   ```bash
   # Stop current server (Ctrl+C)
   python main.py
   ```

2. **Test with curl:**
   ```bash
   curl -X POST "http://localhost:8000/impact" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "workspace\\Repo-Analyzer-\\apps\\api\\app\\core\\config.py", "change_type": "modify"}'
   ```

3. **Expected result:**
   ```json
   {
     "direct_dependents": 8,
     "indirect_dependents": 13,
     "risk_level": "high",
     "risk_score": 100
   }
   ```

## Status: ✅ FIXED (Requires Server Restart)
