# Snapshot-Based Version System

## Overview
Each repository analysis is now stored as a separate **Snapshot** node, allowing comparison between different analysis runs.

## Architecture

```
Repository
    ├── HAS_SNAPSHOT → Snapshot #1 (Analysis Run 1)
    │   ├── ANALYZED_FILE → File nodes
    │   └── Properties: patterns, coupling, metrics
    ├── HAS_SNAPSHOT → Snapshot #2 (Analysis Run 2)
    │   ├── ANALYZED_FILE → File nodes
    │   └── Properties: patterns, coupling, metrics
    └── HAS_SNAPSHOT → Snapshot #3 (Analysis Run 3)
```

## Snapshot Properties
- `snapshot_id`: Unique identifier
- `created_at`: Timestamp of analysis
- `commit_hash`: Git commit at time of analysis
- `total_files`: Number of files analyzed
- `total_deps`: Number of dependencies
- `avg_coupling`: Average coupling metric
- `cycle_count`: Number of circular dependencies
- `patterns`: Detected architectural patterns (JSON)
- `coupling`: Detailed coupling data (JSON)
- `arch_macro/meso/micro`: Architecture explanations

## API Endpoints

### List Snapshots
```bash
GET /repository/{repo_id}/snapshots
```
Returns all analysis snapshots for a repository with metrics.

### Compare Snapshots
```bash
GET /repository/{repo_id}/compare-snapshots/{snapshot1}/{snapshot2}
```
Compares two snapshots showing:
- File count changes
- Dependency changes
- Coupling changes
- Cycle count changes

## Usage Flow

1. **First Analysis**: Creates Repository + Snapshot #1
2. **Second Analysis**: Reuses Repository + Creates Snapshot #2
3. **Comparison**: Compare Snapshot #1 vs Snapshot #2

## Benefits

✅ **Version History**: Track how architecture evolves over time
✅ **Comparison**: Compare any two analysis runs
✅ **Metrics Tracking**: See coupling/complexity trends
✅ **Pattern Evolution**: Track architectural pattern changes
✅ **No Data Loss**: Previous analyses are preserved

## Example Response

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

## Fixed Issues

✅ Files = Versions bug (now counts snapshots)
✅ Each analysis creates new comparable instance
✅ Historical tracking enabled
