# Analysis Caching System

## Overview
ARCHITECH now caches analysis results to avoid redundant LLM calls and enable instant switching between repositories.

## Features

### 1. **Architecture Explanation Caching**
- LLM-generated explanations (macro/meso/micro) stored in Commit nodes
- Automatically retrieved on subsequent requests
- Saves tokens and reduces latency

### 2. **Pattern & Coupling Caching**
- Pattern detection results stored per commit
- Coupling metrics cached in commit nodes
- Architecture comparison uses cached data when available

### 3. **Repository Switching**
- Load any previously analyzed repository instantly
- Rebuilds dependency graph from Neo4j data
- No re-parsing or re-analysis needed

## Usage

### Backend API

**Load Repository:**
```bash
POST /repository/{repo_id}/load
```

**Get Cached Architecture:**
```bash
GET /architecture?repo_id={repo_id}
```

**Get Patterns (with auto-load):**
```bash
GET /patterns?repo_id={repo_id}
```

### Frontend

**Select Repository:**
- Click any repository in Repository Manager
- Analysis automatically loads in background
- All tabs (Architecture, Patterns, Coupling) use loaded data

## Cache Storage

### Neo4j Commit Node Properties:
```cypher
(:Commit {
  commit_hash: "abc123...",
  patterns: "{...}",           // JSON string
  coupling: "{...}",           // JSON string
  arch_macro: "...",           // LLM explanation
  arch_meso: "...",            // Module analysis
  arch_micro: "...",           // File details
  cached_at: datetime()
})
```

## Benefits

1. **Token Savings**: LLM called once per commit, not per request
2. **Performance**: Instant architecture retrieval (no LLM latency)
3. **Multi-Repo**: Switch between repositories without re-analysis
4. **Comparison Speed**: Cached coupling/patterns speed up comparisons

## Cache Invalidation

- Cache tied to commit hash
- New commit = new analysis + new cache
- Old commits retain their cached analysis

## Example Workflow

```python
# First analysis (generates cache)
POST /analyze {"repo_url": "..."}
# → Stores patterns, coupling, architecture in commit node

# Later access (uses cache)
GET /architecture?repo_id=abc123
# → Returns cached explanation instantly

# Switch repository
POST /repository/xyz789/load
GET /patterns?repo_id=xyz789
# → Loads from Neo4j, no re-parsing
```

## Implementation Details

### AnalysisEngine Methods:
- `load_repository_analysis(repo_id)` - Load existing analysis
- `_store_architecture_cache()` - Save LLM results
- `_get_cached_architecture()` - Retrieve cached results
- `_generate_and_cache_architecture()` - Generate + cache

### Cache Check Flow:
1. Check if repo_id matches current
2. If not, load repository from Neo4j
3. Check commit node for cached data
4. Return cached or generate new

## Performance Impact

| Operation | Without Cache | With Cache |
|-----------|---------------|------------|
| Architecture explanation | ~5-10s (LLM) | ~50ms (DB) |
| Pattern detection | ~100ms | ~50ms (cached) |
| Repository switch | ~30s (re-parse) | ~200ms (load) |
| Comparison | ~2s | ~500ms (cached metrics) |

## Future Enhancements

- [ ] Cache expiration policy
- [ ] Partial cache updates
- [ ] Cache warming on startup
- [ ] Redis for faster cache access
