# Version Tracking Quick Reference

## Core Concept
**Content-based versioning**: New version created ONLY when SHA-256 hash changes, not on file save.

## Key Components

### 1. VersionTracker Class
Location: `backend/src/graph/version_tracker.py`

Main methods:
- `compute_file_hash(filepath)` - SHA-256 hashing
- `create_repository(repo_url, repo_path)` - Initialize repo tracking
- `track_file_version(repo_id, file_path)` - Version a file
- `get_file_history(repo_id, file_path)` - Get version chain
- `detect_file_tampering(repo_id, file_path)` - Integrity check

### 2. Graph Schema

```
(Repository)-[:CONTAINS]->(File)-[:HAS_VERSION]->(Version)-[:CREATED_BY]->(User)
                                                     |
                                                     v
                                            [:PREVIOUS_VERSION]
                                                     |
                                                     v
                                                 (Version)
```

### 3. API Endpoints

```bash
# List all repositories
GET /repositories

# Get repository versions
GET /repository/{repo_id}/versions

# Get file history
GET /repository/{repo_id}/file-history?file_path=/path/to/file

# Check integrity
POST /repository/{repo_id}/check-integrity?file_path=/path/to/file

# Get contributors
GET /repository/{repo_id}/contributors
```

## Usage Flow

### Analyze Repository
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

System automatically:
1. Creates Repository node with unique ID
2. Computes SHA-256 for each file
3. Creates Version nodes
4. Links everything in Neo4j graph

### Check Repositories
```bash
curl http://localhost:8000/repositories
```

Returns:
- All analyzed repositories
- File counts
- Version counts
- Last analysis time

### View File History
```bash
curl "http://localhost:8000/repository/abc123/file-history?file_path=/workspace/repo/app.py"
```

Returns:
- Complete version chain
- Timestamps
- Authors
- Hash values

### Verify Integrity
```bash
curl -X POST "http://localhost:8000/repository/abc123/check-integrity?file_path=/workspace/repo/app.py"
```

Returns:
- `intact` - File unchanged
- `tampered` - File modified outside system

## Cypher Queries

### Get all versions of a file
```cypher
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File {file_path: $file_path})
MATCH (f)-[:HAS_VERSION]->(v:Version)
RETURN v ORDER BY v.timestamp DESC
```

### Find most changed files
```cypher
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
MATCH (f)-[:HAS_VERSION]->(v:Version)
WITH f, COUNT(v) as changes
RETURN f.file_path, changes
ORDER BY changes DESC
LIMIT 10
```

### Track developer activity
```cypher
MATCH (u:User)<-[:CREATED_BY]-(v:Version)
RETURN u.email, COUNT(v) as total_changes
ORDER BY total_changes DESC
```

## Testing

Run test suite:
```bash
cd backend
python test_version_tracking.py
```

Tests:
1. ✅ Repository creation
2. ✅ Multi-repository support
3. ✅ Version history tracking
4. ✅ File integrity verification
5. ✅ Developer contributions
6. ✅ Isolated workflows

## Benefits

✅ **Separate Workflows**: Each repository tracked independently  
✅ **Version History**: Complete lineage with SHA-256 hashes  
✅ **Integrity**: Tamper detection via hash comparison  
✅ **Attribution**: Track who changed what  
✅ **Efficiency**: Only changed files get new versions  
✅ **Security**: Cryptographic hashing ensures data integrity  

## Integration with ARCHITECH

The version tracker integrates seamlessly:
- Runs during repository analysis
- Stores metadata in same Neo4j database
- Uses same graph for dependency + version tracking
- Provides additional API endpoints
- No impact on existing functionality

## Example Workflow

```python
# 1. Analyze repository
POST /analyze {"repo_url": "https://github.com/user/repo"}

# 2. System creates:
#    - Repository node (ID: abc123)
#    - File nodes for each file
#    - Version nodes with SHA-256 hashes
#    - Links everything together

# 3. Check what was analyzed
GET /repositories
# Returns: repo_id, file_count, version_count

# 4. View specific file history
GET /repository/abc123/file-history?file_path=/workspace/repo/app.py
# Returns: All versions with timestamps and hashes

# 5. Re-analyze same repository (after changes)
POST /analyze {"repo_url": "https://github.com/user/repo"}
# System:
#   - Computes new hashes
#   - Compares with stored hashes
#   - Creates versions ONLY for changed files
#   - Links new versions to previous versions

# 6. Verify file wasn't tampered with
POST /repository/abc123/check-integrity?file_path=/workspace/repo/app.py
# Returns: "intact" or "tampered" with hash details
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│              ARCHITECH System                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │  Analysis    │         │  Version        │  │
│  │  Engine      │◄───────►│  Tracker        │  │
│  └──────┬───────┘         └────────┬────────┘  │
│         │                           │           │
│         │      ┌───────────────────┘           │
│         │      │                                │
│         ▼      ▼                                │
│  ┌─────────────────────┐                       │
│  │   Neo4j Graph DB    │                       │
│  │                     │                       │
│  │  • Files            │                       │
│  │  • Dependencies     │                       │
│  │  • Versions         │                       │
│  │  • History          │                       │
│  └─────────────────────┘                       │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Summary

This system provides **Git-like version control** integrated with **architectural analysis** in a **graph database**, enabling:

- Multi-repository management
- Content-based versioning (SHA-256)
- Complete version history
- Tamper detection
- Developer analytics
- Dependency + version tracking in one place

Perfect for understanding how code architecture evolves over time! 🚀
