# Snapshot Comparison System

## Overview

The snapshot comparison system allows you to track and compare architectural evolution across different analysis runs. Each snapshot caches:
- **Architecture patterns** (Layered, MVC, Hexagonal)
- **Coupling metrics** (avg coupling, high coupling files, cycles)
- **Dependencies** (file-level import relationships)
- **Architecture explanations** (macro/meso/micro level descriptions)

## Key Features

### 1. Cached Data Per Snapshot
Every snapshot stores:
```json
{
  "snapshot_id": "uuid",
  "created_at": "timestamp",
  "total_files": 50,
  "total_deps": 120,
  "avg_coupling": 2.4,
  "cycle_count": 3,
  "patterns": {...},
  "coupling": {...},
  "arch_macro": "System follows layered architecture...",
  "arch_meso": "Module breakdown...",
  "arch_micro": "File-level details..."
}
```

### 2. Comparison Capabilities

#### Architecture Changes
- Pattern detection changes (newly detected, no longer detected)
- Pattern confidence changes
- Architectural style evolution

#### Coupling Changes
- Average coupling delta
- New/resolved circular dependencies
- High coupling file count changes

#### Dependency Changes
- Files added/removed
- Dependency count delta
- Import relationship changes

### 3. Risk Assessment
Automatically identifies:
- High file growth (>10 files added)
- Significant coupling increase (>1.0 delta)
- New circular dependencies
- Increased highly coupled files

Risk levels: `low`, `medium`, `high`

## API Usage

### List Snapshots
```bash
GET /repository/{repo_id}/snapshots
```

Response:
```json
{
  "repo_id": "abc123",
  "total": 5,
  "snapshots": [
    {
      "snapshot_id": "snap1",
      "created_at": "2024-01-15T10:30:00",
      "total_files": 50,
      "total_deps": 120,
      "avg_coupling": 2.4,
      "cycle_count": 3
    }
  ]
}
```

### Compare Snapshots
```bash
GET /repository/{repo_id}/compare-snapshots/{snapshot1}/{snapshot2}
```

Response:
```json
{
  "snapshot1": {
    "id": "snap1",
    "date": "2024-01-15T10:30:00",
    "files": 50,
    "dependencies": 120,
    "avg_coupling": 2.4,
    "cycles": 3,
    "patterns": {
      "layered": {"detected": true, "confidence": 0.8}
    },
    "architecture": "System follows layered architecture..."
  },
  "snapshot2": {
    "id": "snap2",
    "date": "2024-01-16T14:20:00",
    "files": 55,
    "dependencies": 135,
    "avg_coupling": 2.8,
    "cycles": 5,
    "patterns": {
      "layered": {"detected": true, "confidence": 0.85},
      "mvc": {"detected": true, "confidence": 0.7}
    },
    "architecture": "System follows layered architecture with MVC..."
  },
  "changes": {
    "files_added": ["new_file.py"],
    "files_removed": [],
    "file_delta": 5,
    "dependency_delta": 15,
    "coupling_delta": 0.4,
    "cycle_delta": 2,
    "pattern_changes": {
      "mvc": "newly_detected"
    },
    "high_coupling_before": 8,
    "high_coupling_after": 12
  },
  "risk_assessment": {
    "risk_level": "medium",
    "risk_areas": [
      "Coupling increased by 0.4",
      "2 new circular dependencies",
      "4 more highly coupled files"
    ]
  },
  "summary": "Added 5 files; Coupling increased significantly (+0.4); 2 new circular dependencies; 1 architectural pattern changes"
}
```

## Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
repo_id = "your-repo-id"

# Get snapshots
snapshots = requests.get(f"{BASE_URL}/repository/{repo_id}/snapshots").json()

# Compare first two
s1 = snapshots['snapshots'][0]['snapshot_id']
s2 = snapshots['snapshots'][1]['snapshot_id']

comparison = requests.get(
    f"{BASE_URL}/repository/{repo_id}/compare-snapshots/{s1}/{s2}"
).json()

print(f"Risk Level: {comparison['risk_assessment']['risk_level']}")
print(f"Summary: {comparison['summary']}")
```

## Use Cases

### 1. Track Refactoring Impact
Compare snapshots before/after refactoring to verify:
- Coupling decreased
- Circular dependencies resolved
- Architecture patterns improved

### 2. Monitor Technical Debt
Track over time:
- Coupling trends
- Dependency growth
- Pattern erosion

### 3. Code Review Insights
Compare feature branch snapshot vs main:
- New dependencies introduced
- Coupling impact
- Architectural consistency

### 4. Onboarding Documentation
Show new developers:
- How architecture evolved
- Major refactoring milestones
- Current vs historical patterns

## Implementation Details

### Caching Strategy
- **When**: Data cached during `analyze_repository()`
- **Where**: Stored in Neo4j `Snapshot` nodes
- **What**: Patterns, coupling, dependencies, architecture text
- **Why**: Fast comparisons without re-analysis

### Storage Schema
```cypher
(:Repository)-[:HAS_SNAPSHOT]->(:Snapshot {
  snapshot_id: string,
  created_at: datetime,
  total_files: int,
  total_deps: int,
  avg_coupling: float,
  cycle_count: int,
  patterns: json_string,
  coupling: json_string,
  arch_macro: text,
  arch_meso: text,
  arch_micro: text
})-[:ANALYZED_FILE]->(:File)
```

### Performance
- Comparison: O(1) - reads cached data
- No re-parsing or re-analysis needed
- Handles 100+ snapshots efficiently

## Testing

Run the test script:
```bash
cd backend
python test_snapshot_comparison.py
```

Expected output:
- Lists all snapshots
- Compares first two
- Shows detailed changes
- Displays risk assessment

## Future Enhancements

- [ ] Visual timeline of architecture evolution
- [ ] Automated regression detection
- [ ] Snapshot tagging (releases, milestones)
- [ ] Export comparison reports (PDF/JSON)
- [ ] Diff view for architecture text
- [ ] Trend analysis across multiple snapshots
