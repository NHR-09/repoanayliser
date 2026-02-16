# 🚀 Snapshot Comparison - Quick Start Guide

## ⚡ 5-Minute Setup

### 1. Start Backend
```bash
cd backend
python main.py
```
✅ Backend running on http://localhost:8000

### 2. Start Frontend
```bash
cd frontend
npm start
```
✅ Frontend running on http://localhost:3000

---

## 📸 Create Your First Comparison

### Step 1: Analyze a Repository (First Time)
1. Open http://localhost:3000
2. Click **"Analyze"** tab
3. Enter repository URL: `https://github.com/pallets/flask`
4. Click **"Analyze Repository"**
5. Wait for analysis to complete (~30 seconds)

✅ **Snapshot 1 Created**

### Step 2: Make Changes & Re-analyze
Option A: Analyze same repo again (simulates time-based comparison)
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pallets/flask"}'
```

Option B: Modify code and re-analyze (simulates refactoring comparison)

✅ **Snapshot 2 Created**

### Step 3: Compare Snapshots
1. Click **"Repositories"** tab
2. Click on your repository to select it
3. Click **"Snapshots"** tab
4. Click **"Select as 1"** on first snapshot (turns purple)
5. Click **"Select as 2"** on second snapshot (turns purple)
6. Click **"🔍 Compare Snapshots"** button

✅ **Comparison Results Displayed**

---

## 🎯 What You'll See

### Risk Assessment
```
🟡 Risk Level: MEDIUM
⚠️ Coupling increased by 0.4
⚠️ 2 new circular dependencies
```

### Summary
```
📝 Summary: Added 5 files; Coupling increased 
significantly (+0.4); 2 new circular dependencies
```

### Metrics Comparison
```
Snapshot 1 → Changes → Snapshot 2
Files: 50  →  +5    → 55
Deps: 120  →  +15   → 135
Coupling: 2.4 → +0.4 → 2.8
Cycles: 3  →  +2    → 5
```

### Pattern Changes
```
mvc: newly_detected
layered: confidence_changed: +0.05
```

### File Changes
```
➕ Files Added: new_file.py, another.py, ...
➖ Files Removed: old_file.py, ...
```

---

## 🧪 Test with Sample Data

### Quick Test Script
```bash
cd backend
python test_snapshot_comparison.py
```

This will:
1. ✅ List all repositories
2. ✅ List all snapshots
3. ✅ Compare first two snapshots
4. ✅ Display detailed results

---

## 💡 Pro Tips

### Tip 1: Create Multiple Snapshots
Analyze the same repository multiple times to track evolution:
```bash
# Week 1
POST /analyze {"repo_url": "..."}

# Week 2 (after changes)
POST /analyze {"repo_url": "..."}

# Week 3 (after more changes)
POST /analyze {"repo_url": "..."}
```

### Tip 2: Compare Any Two Snapshots
You can compare:
- ✅ Consecutive snapshots (track incremental changes)
- ✅ First vs latest (track overall evolution)
- ✅ Before/after refactoring (validate improvements)

### Tip 3: Use Risk Assessment
- 🟢 **LOW**: Safe to proceed
- 🟡 **MEDIUM**: Review changes carefully
- 🔴 **HIGH**: Requires immediate attention

### Tip 4: Monitor Coupling Trends
Track coupling over time:
- Decreasing = 👍 Good refactoring
- Increasing = 👎 Technical debt accumulating

---

## 🎓 Common Use Cases

### Use Case 1: Validate Refactoring
```
Before Refactoring:
- Analyze repository → Snapshot A

After Refactoring:
- Analyze repository → Snapshot B

Compare A vs B:
- Expect: Coupling ↓, Cycles ↓
- Risk Level: LOW
```

### Use Case 2: Feature Impact Assessment
```
Main Branch:
- Analyze main → Snapshot Main

Feature Branch:
- Analyze feature → Snapshot Feature

Compare Main vs Feature:
- See: New files, dependencies, patterns
- Assess: Risk level before merge
```

### Use Case 3: Technical Debt Tracking
```
Monthly Analysis:
- Jan: Snapshot 1
- Feb: Snapshot 2
- Mar: Snapshot 3

Compare 1 vs 3:
- Track: Coupling trend, cycle growth
- Action: Address high-risk areas
```

---

## 🔧 Troubleshooting

### Issue: "No snapshots found"
**Solution**: Analyze a repository first
```bash
POST /analyze {"repo_url": "https://github.com/your/repo"}
```

### Issue: "Please select a repository first"
**Solution**: 
1. Go to "Repositories" tab
2. Click on a repository
3. Then go to "Snapshots" tab

### Issue: "Snapshots not found" error
**Solution**: Verify snapshot IDs are correct
```bash
GET /repository/{repo_id}/snapshots
```

### Issue: Empty comparison results
**Solution**: Ensure both snapshots belong to same repository

---

## 📊 Understanding Results

### Delta Colors
- **Red (+)**: Increase (usually bad for coupling/cycles)
- **Green (-)**: Decrease (usually good for coupling/cycles)
- **Gray (0)**: No change

### Risk Indicators
- **🔴 HIGH**: 3+ risk areas → Immediate action needed
- **🟡 MEDIUM**: 1-2 risk areas → Review recommended
- **🟢 LOW**: 0 risk areas → All good!

### Pattern Changes
- **newly_detected**: New architectural pattern found
- **no_longer_detected**: Pattern no longer present
- **confidence_changed**: Pattern confidence shifted

---

## 🎯 Next Steps

1. ✅ **Create snapshots** by analyzing repositories
2. ✅ **Compare snapshots** to track changes
3. ✅ **Monitor trends** over time
4. ✅ **Take action** on high-risk areas
5. ✅ **Validate improvements** after refactoring

---

## 📚 More Information

- Full Documentation: `docs/SNAPSHOT_COMPARISON.md`
- Quick Reference: `docs/SNAPSHOT_COMPARISON_QUICK_REF.md`
- UI Guide: `frontend/SNAPSHOT_COMPARISON_UI.md`
- Visual Guide: `frontend/SNAPSHOT_UI_VISUAL_GUIDE.md`

---

## 🆘 Need Help?

### Check Backend Status
```bash
curl http://localhost:8000/repositories
```

### Check Frontend
Open http://localhost:3000 in browser

### View Logs
- Backend: Terminal running `python main.py`
- Frontend: Terminal running `npm start`

---

**Ready to Start?** 🚀

1. Start backend: `cd backend && python main.py`
2. Start frontend: `cd frontend && npm start`
3. Open http://localhost:3000
4. Analyze → Select → Compare!

**Happy Comparing!** 🎉
