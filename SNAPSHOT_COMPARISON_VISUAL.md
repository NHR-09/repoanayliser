# Snapshot Comparison System - Visual Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECH ANALYSIS ENGINE                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    analyze_repository()
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   Parse Files        Detect Patterns      Analyze Coupling
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
              _store_architecture_cache()
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NEO4J SNAPSHOT NODE                         │
├─────────────────────────────────────────────────────────────────┤
│  snapshot_id: "abc123..."                                       │
│  created_at: 2024-01-15T10:30:00                               │
│  total_files: 50                                                │
│  total_deps: 120                                                │
│  avg_coupling: 2.4                                              │
│  cycle_count: 3                                                 │
│  patterns: {"layered": {...}, "mvc": {...}}        ← CACHED     │
│  coupling: {"high_coupling": [...], "cycles": [...]} ← CACHED   │
│  arch_macro: "System follows layered..."           ← CACHED     │
│  arch_meso: "Module breakdown..."                  ← CACHED     │
│  arch_micro: "File-level details..."               ← CACHED     │
└─────────────────────────────────────────────────────────────────┘
```

## Comparison Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  GET /repository/{repo_id}/compare-snapshots/{s1}/{s2}           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  compare_snapshots(repo_id, s1, s2)
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  Query Snapshot 1      Query Snapshot 2      Query Files
  (cached data)         (cached data)         (analyzed)
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                    Calculate Deltas
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  File Changes        Pattern Changes      Coupling Changes
  (added/removed)     (detected/removed)   (delta/cycles)
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                      Risk Assessment
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  High file growth    Coupling increase    New cycles
  (>10 files)         (>1.0 delta)         (any increase)
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                    Generate Summary
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      COMPARISON RESULT                           │
├─────────────────────────────────────────────────────────────────┤
│  snapshot1: {id, date, files, deps, coupling, patterns, arch}   │
│  snapshot2: {id, date, files, deps, coupling, patterns, arch}   │
│  changes: {                                                      │
│    files_added: [...],                                          │
│    files_removed: [...],                                        │
│    file_delta: +5,                                              │
│    dependency_delta: +15,                                       │
│    coupling_delta: +0.4,                                        │
│    cycle_delta: +2,                                             │
│    pattern_changes: {mvc: "newly_detected"}                     │
│  }                                                               │
│  risk_assessment: {                                             │
│    risk_level: "medium",                                        │
│    risk_areas: ["Coupling increased by 0.4", ...]              │
│  }                                                               │
│  summary: "Added 5 files; Coupling increased..."               │
└─────────────────────────────────────────────────────────────────┘
```

## Data Storage Per Snapshot

```
┌─────────────────────────────────────────────────────────────────┐
│                         SNAPSHOT DATA                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 METRICS (Quantitative)                                      │
│  ├─ total_files: 50                                             │
│  ├─ total_deps: 120                                             │
│  ├─ avg_coupling: 2.4                                           │
│  └─ cycle_count: 3                                              │
│                                                                  │
│  🏗️  PATTERNS (Architectural)                                   │
│  ├─ layered: {detected: true, confidence: 0.8}                 │
│  ├─ mvc: {detected: true, confidence: 0.9}                     │
│  └─ hexagonal: {detected: false}                               │
│                                                                  │
│  🔗 COUPLING (Code Quality)                                     │
│  ├─ high_coupling: [{file: "x.py", fan_in: 8}, ...]           │
│  ├─ cycles: [["a.py", "b.py", "a.py"], ...]                   │
│  └─ metrics: {avg_coupling: 2.4, ...}                          │
│                                                                  │
│  📝 ARCHITECTURE (LLM Generated)                                │
│  ├─ macro: "System follows layered architecture..."            │
│  ├─ meso: "Module breakdown: presentation, business, data..."  │
│  └─ micro: "File-level details: auth.py handles..."            │
│                                                                  │
│  📁 FILES (Analyzed)                                            │
│  └─ [:ANALYZED_FILE]->(:File) relationships                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Comparison Output Structure

```json
{
  "snapshot1": {
    "id": "abc123",
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
    "id": "def456",
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
    "files_added": ["new_file.py", "another.py"],
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

## Risk Assessment Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                      RISK THRESHOLDS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  File Growth:                                                    │
│  ├─ > 10 files added → ⚠️  Risk                                 │
│  └─ ≤ 10 files added → ✅ OK                                    │
│                                                                  │
│  Coupling Delta:                                                 │
│  ├─ > 1.0 increase → ⚠️  Risk                                   │
│  └─ ≤ 1.0 increase → ✅ OK                                      │
│                                                                  │
│  Circular Dependencies:                                          │
│  ├─ Any increase → ⚠️  Risk                                     │
│  └─ No change/decrease → ✅ OK                                  │
│                                                                  │
│  High Coupling Files:                                            │
│  ├─ Count increased → ⚠️  Risk                                  │
│  └─ Count same/decreased → ✅ OK                                │
│                                                                  │
│  Overall Risk Level:                                             │
│  ├─ 3+ risk areas → 🔴 HIGH                                     │
│  ├─ 1-2 risk areas → 🟡 MEDIUM                                  │
│  └─ 0 risk areas → 🟢 LOW                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Use Case Examples

### 1. Refactoring Validation
```
Before Refactoring (Snapshot 1)
├─ avg_coupling: 3.2
├─ cycles: 5
└─ high_coupling_files: 15

After Refactoring (Snapshot 2)
├─ avg_coupling: 2.1  ✅ Improved
├─ cycles: 1          ✅ Improved
└─ high_coupling_files: 8  ✅ Improved

Risk Level: LOW ✅
Summary: "Coupling decreased (-1.1); 4 circular dependencies resolved"
```

### 2. Feature Addition
```
Main Branch (Snapshot 1)
├─ files: 50
├─ dependencies: 120
└─ patterns: [layered]

Feature Branch (Snapshot 2)
├─ files: 55          ⚠️  +5 files
├─ dependencies: 140  ⚠️  +20 deps
└─ patterns: [layered, mvc]  ℹ️  New pattern

Risk Level: MEDIUM ⚠️
Summary: "Added 5 files; 1 architectural pattern changes"
```

### 3. Technical Debt Accumulation
```
Week 1 (Snapshot 1)
├─ avg_coupling: 2.0
├─ cycles: 2
└─ files: 45

Week 4 (Snapshot 2)
├─ avg_coupling: 3.5  🔴 +1.5
├─ cycles: 8          🔴 +6
└─ files: 60          🔴 +15

Risk Level: HIGH 🔴
Summary: "Added 15 files; Coupling increased significantly (+1.5); 6 new circular dependencies"
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────────┐
│                         PERFORMANCE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Comparison Speed:                                               │
│  └─ O(1) - Reads cached data from Neo4j                         │
│                                                                  │
│  Storage Overhead:                                               │
│  └─ ~10KB per snapshot (JSON data)                              │
│                                                                  │
│  Scalability:                                                    │
│  └─ Handles 100+ snapshots efficiently                          │
│                                                                  │
│  No Re-analysis:                                                 │
│  └─ Uses cached patterns, coupling, architecture                │
│                                                                  │
│  Query Time:                                                     │
│  └─ < 100ms for typical comparison                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                      INTEGRATION READY                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Backend API:                                                    │
│  └─ GET /repository/{id}/compare-snapshots/{s1}/{s2}            │
│                                                                  │
│  Frontend Visualization:                                         │
│  ├─ Timeline view of snapshots                                  │
│  ├─ Coupling trend charts                                       │
│  ├─ Dependency growth graphs                                    │
│  └─ Pattern evolution display                                   │
│                                                                  │
│  CI/CD Integration:                                              │
│  ├─ Compare PR branch vs main                                   │
│  ├─ Automated risk assessment                                   │
│  └─ Block merge if risk too high                                │
│                                                                  │
│  Reporting:                                                      │
│  ├─ Weekly architecture reports                                 │
│  ├─ Technical debt tracking                                     │
│  └─ Refactoring impact analysis                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
