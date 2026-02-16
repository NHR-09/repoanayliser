# Repository Version Tracking System

## Overview

SHA-256 based version tracking system integrated with Neo4j graph database for managing multiple repository analyses with complete version history and integrity verification.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Version Tracking System                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐      ┌──────────────┐            │
│  │ SHA-256      │      │ Neo4j Graph  │            │
│  │ Hash Engine  │─────▶│ Database     │            │
│  └──────────────┘      └──────────────┘            │
│         │                      │                    │
│         │                      │                    │
│  ┌──────▼──────────────────────▼──────┐            │
│  │   Version Change Detection          │            │
│  │   (Content-based, not save-based)   │            │
│  └─────────────────────────────────────┘            │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Graph Data Model

### Nodes

1. **Repository**
   - `repo_id` (unique): SHA-256 hash of repo URL
   - `name`: Repository name
   - `url`: Git URL
   - `path`: Local path
   - `last_analyzed`: Timestamp

2. **File**
   - `file_path` (unique): Absolute file path
   - `language`: Programming language

3. **Version**
   - `hash` (unique): SHA-256 content hash
   - `timestamp`: Creation time
   - `message`: Commit/change message

4. **User**
   - `user_id` (unique): Email or identifier
   - `email`: User email

### Relationships

```
Repository ─[CONTAINS]→ File
File ─[HAS_VERSION]→ Version
Version ─[CREATED_BY]→ User
Version ─[PREVIOUS_VERSION]→ Version (linked list)
```

## Key Features

### 1. Content-Based Versioning
- New version created ONLY when SHA-256 hash changes
- File saves without content changes = no new version
- Prevents false history pollution

### 2. Multi-Repository Support
- Each repository tracked separately
- Unique `repo_id` per repository
- Isolated workflows per repository

### 3. Version History Chain
- Complete lineage tracking via `PREVIOUS_VERSION` relationships
- Time-ordered version history
- Diff capability between versions

### 4. Integrity Verification
- Tamper detection via hash comparison
- Stored hash vs. current file hash
- Security feature for data integrity

### 5. Developer Tracking
- Attribution per version
- Contribution analysis
- Activity metrics

## API Endpoints

### Repository Management

#### List All Repositories
```bash
GET /repositories
```

Response:
```json
{
  "total": 3,
  "repositories": [
    {
      "repo_id": "a1b2c3d4e5f6",
      "name": "flask",
      "url": "https://github.com/pallets/flask",
      "path": "/workspace/flask",
      "last_analyzed": "2024-01-15T10:30:00",
      "file_count": 150,
      "version_count": 450
    }
  ]
}
```

#### Get Repository Versions
```bash
GET /repository/{repo_id}/versions
```

Response:
```json
{
  "repo_id": "a1b2c3d4e5f6",
  "versions": [
    {
      "file": "/workspace/flask/app.py",
      "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "timestamp": "2024-01-15T10:30:00",
      "message": "Auto-tracked",
      "author": "system"
    }
  ]
}
```

### File History

#### Get File Version History
```bash
GET /repository/{repo_id}/file-history?file_path=/path/to/file.py
```

Response:
```json
{
  "file": "/workspace/flask/app.py",
  "history": [
    {
      "hash": "abc123...",
      "timestamp": "2024-01-15T10:30:00",
      "message": "Auto-tracked",
      "author": "user@example.com",
      "previous_hash": "def456..."
    }
  ]
}
```

### Integrity Checking

#### Check File Tampering
```bash
POST /repository/{repo_id}/check-integrity?file_path=/path/to/file.py
```

Response (Intact):
```json
{
  "status": "intact",
  "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

Response (Tampered):
```json
{
  "status": "tampered",
  "stored_hash": "abc123...",
  "current_hash": "def456...",
  "message": "File modified outside system"
}
```

### Developer Analytics

#### Get Contributors
```bash
GET /repository/{repo_id}/contributors
```

Response:
```json
{
  "repo_id": "a1b2c3d4e5f6",
  "contributors": [
    {
      "developer": "user@example.com",
      "files_modified": 25,
      "total_versions": 87
    }
  ]
}
```

## Usage Examples

### Analyze New Repository
```python
# POST /analyze
{
  "repo_url": "https://github.com/pallets/flask"
}

# System automatically:
# 1. Creates Repository node
# 2. Computes SHA-256 for each file
# 3. Creates initial Version nodes
# 4. Links everything in graph
```

### Re-analyze Same Repository
```python
# POST /analyze (same URL)
# System:
# 1. Uses existing repo_id
# 2. Compares new hashes with stored hashes
# 3. Creates versions ONLY for changed files
# 4. Links new versions to previous versions
```

### Query Version History
```cypher
// Get file evolution
MATCH path=(v:Version)-[:PREVIOUS_VERSION*]->(old)
WHERE v.hash = 'abc123...'
RETURN path

// Find who changed what
MATCH (u:User)-[:CREATED_BY]-(v:Version)-[:HAS_VERSION]-(f:File)
WHERE f.file_path CONTAINS 'auth.py'
RETURN u.email, v.timestamp, v.hash
```

## Cypher Query Examples

### 1. File Change Timeline
```cypher
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File {file_path: $file_path})
MATCH (f)-[:HAS_VERSION]->(v:Version)
OPTIONAL MATCH (v)-[:CREATED_BY]->(u:User)
RETURN v.timestamp, v.hash, u.email
ORDER BY v.timestamp DESC
```

### 2. Most Active Files
```cypher
MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
MATCH (f)-[:HAS_VERSION]->(v:Version)
WITH f, COUNT(v) as version_count
RETURN f.file_path, version_count
ORDER BY version_count DESC
LIMIT 10
```

### 3. Developer Impact
```cypher
MATCH (u:User {user_id: $email})<-[:CREATED_BY]-(v:Version)
MATCH (v)<-[:HAS_VERSION]-(f:File)
RETURN COUNT(DISTINCT f) as files_touched,
       COUNT(v) as total_changes
```

### 4. Detect Concurrent Changes
```cypher
MATCH (f:File)-[:HAS_VERSION]->(v1:Version)
MATCH (f)-[:HAS_VERSION]->(v2:Version)
WHERE v1.timestamp = v2.timestamp AND v1 <> v2
RETURN f.file_path, v1.hash, v2.hash
```

## System Workflow

### Initial Analysis
```
1. User submits repo_url
2. System clones repository
3. For each file:
   a. Compute SHA-256 hash
   b. Create File node
   c. Create Version node with hash
   d. Link: Repository→File→Version→User
4. Store in Neo4j
```

### Re-analysis (Version Update)
```
1. User re-submits same repo_url
2. System finds existing repo_id
3. For each file:
   a. Compute current SHA-256
   b. Query last stored hash
   c. IF hash_changed:
      - Create new Version node
      - Link to previous version
      - Update timestamp
   d. ELSE:
      - Skip (no new version)
4. Return change summary
```

### Integrity Check
```
1. User requests integrity check
2. System:
   a. Retrieves stored hash from Neo4j
   b. Computes current file hash
   c. Compares hashes
3. IF different:
   - Flag as "tampered"
   - Return both hashes
4. ELSE:
   - Return "intact"
```

## Benefits Over Traditional Systems

| Feature | File System | Git | ARCHITECH Version Tracker |
|---------|-------------|-----|---------------------------|
| Content-based versioning | ❌ | ✅ | ✅ |
| Dependency tracking | ❌ | ❌ | ✅ |
| Architecture analysis | ❌ | ❌ | ✅ |
| Multi-repo management | ❌ | ⚠️ | ✅ |
| Tamper detection | ❌ | ✅ | ✅ |
| Graph queries | ❌ | ❌ | ✅ |
| Impact analysis | ❌ | ❌ | ✅ |

## Security Features

### 1. Cryptographic Integrity
- SHA-256 ensures tamper detection
- Any byte change = different hash
- Immutable version history

### 2. Audit Trail
- Every version linked to user
- Timestamp tracking
- Complete change history

### 3. Isolated Workflows
- Each repository separate
- No cross-contamination
- Independent version chains

## Performance Considerations

### Hash Computation
- Chunked reading (8KB blocks)
- Efficient for large files
- Cached in Neo4j

### Graph Queries
- Indexed on unique constraints
- Optimized traversals
- Limited depth queries

### Storage
- Only metadata stored (not file content)
- Hashes are 64 characters
- Minimal overhead

## Future Enhancements

- [ ] Diff generation between versions
- [ ] Branch/merge support
- [ ] Automated conflict detection
- [ ] Version rollback capability
- [ ] Export version history to Git
- [ ] Real-time change monitoring
- [ ] WebSocket notifications

## Conclusion

This system combines:
- **Version Control** (like Git)
- **Graph Database** (relationships)
- **Architecture Analysis** (code structure)
- **Integrity Verification** (security)

Result: Comprehensive repository management with architectural insights and tamper-proof version tracking.
