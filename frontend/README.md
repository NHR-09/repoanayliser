# Frontend - Coming Soon

The frontend is intentionally minimal for the hackathon backend demo.

## Why Backend-First?

The PS-10 challenge focuses on **architectural recovery logic**, not UI:
- Pattern detection algorithms
- Graph-based dependency analysis
- Hybrid retrieval system
- Evidence-bound LLM reasoning

The backend API is **fully functional** and can be tested via:
- cURL commands
- Postman
- Python test script
- Neo4j Browser (for graph visualization)

## Quick Visualization

Use **Neo4j Browser** for interactive graph visualization:

1. Open http://localhost:7474
2. Login with `neo4j/password`
3. Run query:
```cypher
MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 50
```

## API Testing

```bash
# Test all endpoints
python test_system.py

# Or manually
curl http://localhost:8000/patterns
curl http://localhost:8000/coupling
curl http://localhost:8000/architecture
```

## Future Frontend (Optional)

If needed, create React app:

```bash
npx create-react-app frontend
cd frontend
npm install d3 axios
```

Key components:
- Architecture diagram (D3.js force graph)
- Pattern detection dashboard
- Coupling heatmap
- Impact analysis visualizer

## Current Demo Strategy

**Show judges:**
1. API responses (JSON)
2. Neo4j graph visualization
3. Terminal output
4. Postman collection

This proves the **core intelligence** works without UI complexity.

---

**Status**: Backend complete ✅ | Frontend optional for future
