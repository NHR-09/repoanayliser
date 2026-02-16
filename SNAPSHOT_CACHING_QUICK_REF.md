# Snapshot Caching - Quick Reference

## What Changed?

### Before
```
Analyze repo → Parse files → Run analysis → Call LLM → Return results
(Every time, even for unchanged repos)
```

### After
```
Analyze repo → Check commit hash → Cache hit? → Return cached results
                                  ↓ Cache miss
                                  Parse files → Run analysis → Call LLM → Cache → Return
```

## Key Benefits

✅ **No redundant LLM calls** - Save API costs  
✅ **Instant results** - 1-2 seconds vs 30-60 seconds  
✅ **Automatic detection** - No manual configuration needed  
✅ **Preserves history** - All snapshots kept for comparison  

## How to Use

### 1. First Analysis (Creates Cache)
```bash
POST /analyze
{
  "repo_url": "https://github.com/user/repo"
}

# Takes 30-60 seconds
# Creates snapshot with cached data
```

### 2. Subsequent Analysis (Uses Cache)
```bash
POST /analyze
{
  "repo_url": "https://github.com/user/repo"
}

# Takes 1-2 seconds
# Returns: {"cached": true}
```

### 3. After New Commit (Creates New Cache)
```bash
# Make changes and commit
git commit -m "new changes"

POST /analyze
{
  "repo_url": "https://github.com/user/repo"
}

# Takes 30-60 seconds
# Creates new snapshot for new commit
```

## Log Messages

### Cache Hit
```
✅ No changes detected - using cached analysis
📦 Repository ID: abc123
📸 Cached Snapshot ID: xyz789
💾 Commit: a1b2c3d4
```

### Cache Miss
```
🚀 Starting repository analysis
📦 Repository ID: abc123
📸 New Snapshot ID: new123
📝 Parsing 50 files...
```

## API Endpoints

### Check Snapshots
```bash
GET /repository/{repo_id}/snapshots
```

### Compare Snapshots
```bash
GET /repository/{repo_id}/compare-snapshots/{s1}/{s2}
```

### Delete Snapshot
```bash
DELETE /repository/{repo_id}/snapshot/{snapshot_id}
```

## When Cache is Used

✅ Same repository URL  
✅ Same Git commit hash  
✅ Snapshot has cached data  

## When Cache is NOT Used

❌ Different commit hash  
❌ New repository  
❌ Snapshot deleted  
❌ First analysis  

## Cached Data

- Pattern detection results
- Coupling analysis
- Architecture explanations (macro/meso/micro)
- Dependency metrics
- File counts

## Not Cached

- Raw file contents
- AST parsing results
- Vector embeddings (regenerated if needed)

## Cost Savings Example

### 10 Analyses of Same Repo

**Without Caching:**
- Time: 10 × 45s = 450 seconds (7.5 minutes)
- LLM calls: 10 × 4 = 40 calls
- Cost: 10 × $0.10 = $1.00

**With Caching:**
- Time: 45s + (9 × 2s) = 63 seconds (1 minute)
- LLM calls: 4 calls
- Cost: $0.10

**Savings: 86% time, 90% cost**

## Troubleshooting

### Cache Not Working?
1. Check commit hash: `git rev-parse HEAD`
2. Verify snapshot exists: `GET /repository/{repo_id}/snapshots`
3. Check logs for "✅ No changes detected"

### Force Fresh Analysis?
1. Make a new commit: `git commit --allow-empty -m "force"`
2. Or delete snapshot: `DELETE /repository/{repo_id}/snapshot/{id}`

### Multiple Snapshots?
- Normal behavior - one per commit
- Use compare endpoint to see differences
- Delete old snapshots if needed

## Implementation Files

- `backend/src/analysis_engine.py` - Main caching logic
- `backend/src/graph/version_tracker.py` - Commit tracking
- `backend/main.py` - API endpoints
- `SNAPSHOT_CACHING.md` - Full documentation

---

**TL;DR**: System now caches analysis results per commit. Same commit = instant cached results. New commit = fresh analysis + new cache.
