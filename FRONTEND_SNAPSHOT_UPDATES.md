# Frontend Updates for Snapshot System

## Changes Made

### 1. API Service (`services/api.js`)
Added new endpoints:
- `getSnapshots(repoId)` - Fetch all snapshots for a repository
- `compareSnapshots(repoId, snapshot1, snapshot2)` - Compare two snapshots

### 2. New Component: `SnapshotComparison.js`
**Features:**
- Lists all analysis snapshots for a repository
- Shows metrics for each snapshot (files, dependencies, coupling, cycles)
- Allows selection of two snapshots for comparison
- Displays side-by-side comparison with delta calculations
- Color-coded deltas (red = increase, green = decrease)

**UI Elements:**
- Snapshot cards with numbered badges (#1, #2, etc.)
- Metrics grid showing key statistics
- Selection buttons for choosing snapshots to compare
- Comparison result panel with 3-column layout (Snapshot 1 | Delta | Snapshot 2)

### 3. Updated: `RepositoryManager.js`
**Changes:**
- Changed "Versions" label to "Snapshots" throughout
- Added new "📸 Snapshots" tab (first tab)
- Integrated `SnapshotComparison` component
- Updated stats display to show "Analysis Runs" instead of "Avg Versions/File"

## User Flow

1. **View Repositories**: See list with file count and snapshot count
2. **Select Repository**: Click to view details
3. **Snapshots Tab**: Default view showing all analysis snapshots
4. **Select Snapshots**: Choose two snapshots to compare
5. **Compare**: Click "Compare Snapshots" button
6. **View Results**: See metrics comparison with deltas

## Visual Improvements

- Snapshot cards with gradient badges
- Metrics displayed in grid layout
- Color-coded comparison deltas
- Clean, modern UI with proper spacing
- Responsive design

## Example Snapshot Display

```
#3  📸  2/16/2025, 7:30:00 PM
┌─────────────────────────────────┐
│ 📁 Files: 68  🔗 Deps: 135      │
│ 📊 Coupling: 2.8  🔄 Cycles: 5  │
└─────────────────────────────────┘
[Select as 1] [Select as 2]
```

## Example Comparison

```
Snapshot 1          Changes (Δ)        Snapshot 2
─────────────────   ──────────────     ─────────────────
Files: 64           Files: +4          Files: 68
Deps: 120           Deps: +15          Deps: 135
Coupling: 2.4       Coupling: +0.4     Coupling: 2.8
Cycles: 3           Cycles: +2         Cycles: 5
```

## Benefits

✅ Clear visualization of analysis history
✅ Easy snapshot comparison
✅ Tracks architectural evolution
✅ Identifies trends (coupling increase, new cycles)
✅ Better than file-level version tracking for architecture analysis
