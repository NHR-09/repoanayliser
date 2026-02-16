# Function Graph Zero Edges - Root Cause & Fix

## Problem
Function graph had zero edges (CALLS relationships) even though:
- Functions were being parsed correctly
- Function calls were being extracted
- `create_function_call()` was being called

## Root Cause
**Property name mismatch between File nodes and CALLS relationship queries**

### The Issue:
1. **File nodes have inconsistent properties:**
   - Some have only `path` property (absolute paths)
   - Some have only `file_path` property (relative paths)  
   - Some have both properties

2. **`create_function_call()` was querying:**
   ```cypher
   MATCH (f:File {path: $from_file})
   ```
   This only matched File nodes with the `path` property.

3. **But Functions were linked to Files via `file_path`:**
   ```cypher
   MATCH (f:File)-[:CONTAINS]->(fn:Function)
   ```
   Where `f` might only have `file_path` property.

### Why This Happened:
- `graph_db.py` creates File nodes with `path` property (normalized/absolute)
- `version_tracker.py` creates File nodes with `file_path` property (as-is)
- This created duplicate/inconsistent File nodes in the database

## The Fix

### Changed `create_function_call()` in `graph_db.py`:

**Before:**
```python
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File {path: $from_file})
```

**After:**
```python
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
WHERE f.path = $from_file OR f.file_path = $from_file
```

This matches File nodes using EITHER property, ensuring CALLS relationships are created regardless of which property the File node has.

## Verification

After the fix:
- ✅ 16 CALLS relationships created (was 0)
- ✅ Function graph now has edges
- ✅ `/graph/functions` endpoint returns data

## Testing

To verify the fix works for new analyses:
1. Delete existing repository from database
2. Re-analyze the repository
3. Check `/graph/functions` endpoint
4. Should see CALLS relationships

## Future Improvements

1. **Standardize File node properties:**
   - Choose ONE property name (`path` or `file_path`)
   - Update all code to use it consistently
   - Add migration script to fix existing nodes

2. **Add validation:**
   - Ensure File nodes always have the required property
   - Log warnings when property is missing

3. **Better path handling:**
   - Decide on relative vs absolute paths
   - Normalize consistently across all modules
