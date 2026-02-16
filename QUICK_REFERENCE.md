# ARCHITECH - Quick Reference Card

## 🚀 START SYSTEM

```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
npm start
```

**Access**: http://localhost:3000

---

## 🧹 CLEAN DATABASE (if needed)

```bash
cd backend
python cleanup_database.py
```

---

## 🔍 COMMON API CALLS

### Analyze Repository
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

### Get Patterns
```bash
curl http://localhost:8000/patterns
```

### Get Coupling
```bash
curl http://localhost:8000/coupling
```

### Blast Radius (3 types)
```bash
# DELETE
curl "http://localhost:8000/blast-radius/src/app.py?change_type=delete"

# MODIFY
curl "http://localhost:8000/blast-radius/src/app.py?change_type=modify"

# MOVE
curl "http://localhost:8000/blast-radius/src/app.py?change_type=move"
```

### Function Graph
```bash
curl http://localhost:8000/graph/functions
```

### Compare Snapshots
```bash
curl "http://localhost:8000/repository/{repo_id}/compare-snapshots/{snapshot1}/{snapshot2}"
```

### Compare Commits
```bash
curl "http://localhost:8000/repository/{repo_id}/compare-architecture/{commit1}/{commit2}"
```

---

## ✅ VERIFY FIXES

### 1. Check Blast Radius Works
```bash
curl "http://localhost:8000/blast-radius/src/main.py?change_type=modify"
```
**Expected**: Returns `direct_dependents`, `indirect_dependents`, `risk_level`

### 2. Check Function Graph Has No Orphans
```bash
curl http://localhost:8000/graph/functions | jq '.nodes[] | select(.file == null)'
```
**Expected**: Empty output (no functions without files)

### 3. Check Path Resolution
```bash
curl "http://localhost:8000/dependencies/src/main.py"
```
**Expected**: Returns list of dependencies (not empty if file has imports)

---

## 🐛 TROUBLESHOOTING

### Functions Without Files?
```bash
# Run cleanup
python cleanup_database.py

# Re-analyze repository
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

### Empty Blast Radius?
- Check file path is correct
- Try different path formats (relative/absolute)
- Verify file exists in database: `curl http://localhost:8000/files`

### Neo4j Connection Error?
- Open Neo4j Desktop
- Start database
- Check credentials in `backend/.env`

---

## 📊 WHAT'S FIXED

✅ Blast radius MODIFY risk assessment  
✅ Path normalization (cross-platform)  
✅ Function graph orphan filtering  
✅ Architecture comparison implementation  

---

## 📝 KEY FILES

- `backend/main.py` - API server
- `backend/cleanup_database.py` - Database cleanup
- `backend/src/graph/blast_radius.py` - Blast radius logic
- `backend/src/graph/function_graph.py` - Function graph logic
- `backend/src/analysis_engine.py` - Core analysis engine

---

## 🎯 QUICK TESTS

```bash
# 1. Analyze Flask
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pallets/flask"}'

# 2. Wait for completion (check status)
curl http://localhost:8000/status/{job_id}

# 3. Get patterns
curl http://localhost:8000/patterns

# 4. Get function graph
curl http://localhost:8000/graph/functions

# 5. Test blast radius
curl "http://localhost:8000/blast-radius/src/flask/app.py?change_type=delete"
```

---

## 💡 TIPS

- Use `jq` to format JSON: `curl ... | jq`
- Check Neo4j Browser: http://localhost:7474
- View API docs: http://localhost:8000/docs
- All functions now have files (no orphans)
- Blast radius works for DELETE, MODIFY, MOVE

---

**Status**: ✅ All fixes complete  
**Version**: 1.1  
**Ready**: YES
