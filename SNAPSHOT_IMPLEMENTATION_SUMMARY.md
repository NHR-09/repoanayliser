# Snapshot System Implementation - Complete Summary

## Problem Fixed
**Original Issue**: Files count = Versions count (64 files = 64 versions)
**Root Cause**: System was counting individual file versions instead of analysis snapshots

## Solution Implemented
Created a **snapshot-based version system** where each repository analysis is stored as a separate comparable instance.

---

## Backend Changes

### 1. `version_tracker.py`
**Changes:**
- Added `Snapshot` node creation in `create_repository()`
- Returns `(repo_id, exists, snapshot_id)` tuple
- Changed `list_repositories()` to count snapshots instead of commits
- Each analysis creates a new snapshot with unique ID

**New Graph Structure:**
```
Repository -[:HAS_SNAPSHOT]-> Snapshot
                              ├── snapshot_id
                              ├── created_at
                              ├── commit_hash
                              ├── total_files
                              ├── total_deps
                              ├── avg_coupling
                              ├── cycle_count
                              ├── patterns (JSON)
                              └── coupling (JSON)
```

### 2. `analysis_engine.py`
**Changes:**
- Stores `current_snapshot_id` during analysis
- Links analyzed files to snapshots via `ANALYZED_FILE` relationship
- Stores metrics in snapshot nodes instead of commits
- Stores architecture explanations in snapshots
- Updated `_store_architecture_cache()` to use snapshots

### 3. `main.py` (API)
**New Endpoints:**
- `GET /repository/{repo_id}/snapshots` - List all snapshots
- `GET /repository/{repo_id}/compare-snapshots/{s1}/{s2}` - Compare snapshots

**Response Format:**
```json
{
  "snapshot1": {
    "id": "abc12345",
    "date": "2025-02-16T18:30:00",
    "files": 64,
    "dependencies": 120,
    "avg_coupling": 2.4,
    "cycles": 3
  },
  "snapshot2": {
    "id": "def67890",
    "date": "2025-02-16T19:00:00",
    "files": 68,
    "dependencies": 135,
    "avg_coupling": 2.8,
    "cycles": 5
  },
  "delta": {
    "files": +4,
    "dependencies": +15,
    "coupling": +0.4,
    "cycles": +2
  }
}
```

---

## Frontend Changes

### 1. `services/api.js`
**Added:**
- `getSnapshots(repoId)` - Fetch snapshots
- `compareSnapshots(repoId, s1, s2)` - Compare snapshots

### 2. `components/SnapshotComparison.js` (NEW)
**Features:**
- Lists all analysis snapshots with metrics
- Numbered badges (#1, #2, #3...)
- Selection interface for choosing two snapshots
- Side-by-side comparison view
- Color-coded deltas (red=increase, green=decrease)

**UI Layout:**
```
┌─────────────────────────────────────────┐
│ #3  📸  2/16/2025, 7:30:00 PM          │
│ ┌─────────────────────────────────────┐ │
│ │ 📁 68  🔗 135  📊 2.8  🔄 5        │ │
│ └─────────────────────────────────────┘ │
│ [Select as 1] [Select as 2]             │
└─────────────────────────────────────────┘
```

### 3. `components/RepositoryManager.js`
**Updates:**
- Changed "Versions" → "Snapshots" throughout
- Added "📸 Snapshots" tab (first tab)
- Integrated `SnapshotComparison` component
- Updated stats: "Analysis Runs" instead of "Avg Versions/File"

---

## User Workflow

### Before (Broken)
1. Analyze repo → 64 files
2. See "Versions: 64" (confusing, equals file count)
3. No way to compare analyses

### After (Fixed)
1. **First Analysis**: Creates Snapshot #1
   - Files: 64, Deps: 120, Coupling: 2.4, Cycles: 3

2. **Second Analysis**: Creates Snapshot #2
   - Files: 68, Deps: 135, Coupling: 2.8, Cycles: 5

3. **Compare**: Select Snapshot #1 and #2
   - See deltas: +4 files, +15 deps, +0.4 coupling, +2 cycles
   - Identify architectural degradation

---

## Benefits

✅ **Fixed Bug**: Snapshots count now reflects actual analysis runs
✅ **Comparison**: Can compare any two analysis snapshots
✅ **Metrics Tracking**: Track coupling/complexity evolution
✅ **Architecture Evolution**: See how patterns change over time
✅ **No Data Loss**: All previous analyses preserved
✅ **Clear Semantics**: "Snapshot" is clearer than "Version" for analysis runs

---

## Technical Details

### Database Schema
```cypher
// Old (Confusing)
Repository -[:CONTAINS]-> File -[:HAS_VERSION]-> Version
// Count of versions = count of files (BUG)

// New (Clear)
Repository -[:HAS_SNAPSHOT]-> Snapshot -[:ANALYZED_FILE]-> File
// Count of snapshots = count of analysis runs (CORRECT)
```

### Snapshot Properties
- `snapshot_id`: Unique identifier (SHA-256 hash)
- `created_at`: Timestamp of analysis
- `commit_hash`: Git commit at analysis time
- `total_files`: Number of files analyzed
- `total_deps`: Number of dependencies
- `avg_coupling`: Average coupling metric
- `cycle_count`: Number of circular dependencies
- `patterns`: Detected patterns (JSON)
- `coupling`: Detailed coupling data (JSON)
- `arch_macro/meso/micro`: Architecture explanations

---

## Files Modified

### Backend
1. `backend/src/graph/version_tracker.py` - Snapshot creation & listing
2. `backend/src/analysis_engine.py` - Snapshot integration
3. `backend/main.py` - New API endpoints

### Frontend
1. `frontend/src/services/api.js` - API methods
2. `frontend/src/components/SnapshotComparison.js` - NEW component
3. `frontend/src/components/RepositoryManager.js` - Integration

### Documentation
1. `SNAPSHOT_SYSTEM.md` - System overview
2. `FRONTEND_SNAPSHOT_UPDATES.md` - Frontend changes
3. `README.md` - Updated features & endpoints

---

## Testing

### Manual Test
1. Start backend: `python main.py`
2. Start frontend: `npm start`
3. Analyze a repository
4. Go to "Repositories" tab
5. Click on repository
6. See "📸 Snapshots" tab
7. Analyze same repo again (modify code first)
8. See two snapshots
9. Select both and click "Compare"
10. View delta metrics

### Expected Result
- First analysis: Snapshot #1 created
- Second analysis: Snapshot #2 created
- Comparison shows differences in metrics
- "Snapshots" count increases with each analysis

---

## Migration Notes

**Existing Data**: Old repositories will show 0 snapshots until re-analyzed
**No Breaking Changes**: Existing version tracking still works
**Backward Compatible**: Old endpoints still functional

---

## Future Enhancements

- [ ] Snapshot deletion
- [ ] Snapshot export (JSON/PDF)
- [ ] Trend visualization (line charts)
- [ ] Automatic snapshot on git commit
- [ ] Snapshot tagging/naming
- [ ] Diff view between snapshots
