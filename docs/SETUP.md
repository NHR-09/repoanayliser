# ARCHITECH Setup Guide

## Prerequisites

- Python 3.9+
- Neo4j 5.x
- Node.js 18+ (for frontend)
- Git

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Neo4j

**Option A: Docker**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.14
```

**Option B: Local Installation**
- Download from https://neo4j.com/download/
- Set password to `password` or update `.env`

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

CHROMA_PERSIST_DIR=./chroma_db

OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here
```

### 4. Run Backend

```bash
python main.py
```

Server runs at `http://localhost:8000`

API docs at `http://localhost:8000/docs`

## Testing the System

### 1. Analyze a Repository

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pallets/flask"}'
```

Response:
```json
{"job_id": "abc-123", "status": "processing"}
```

### 2. Check Status

```bash
curl http://localhost:8000/status/abc-123
```

### 3. Get Architecture

```bash
curl http://localhost:8000/architecture
```

### 4. Get Patterns

```bash
curl http://localhost:8000/patterns
```

### 5. Analyze Impact

```bash
curl -X POST http://localhost:8000/impact \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/src/app.py"}'
```

## Frontend Setup (Future)

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Neo4j Connection Failed
- Check Neo4j is running: `docker ps` or check Neo4j Desktop
- Verify credentials in `.env`
- Test connection: `http://localhost:7474`

### ChromaDB Issues
- Delete `./chroma_db` folder and restart
- Check disk space

### LLM API Errors
- Verify API key in `.env`
- Check API quota/billing

### Parser Errors
- Ensure repository has supported languages (Python, JavaScript, Java)
- Check file permissions

## Architecture Verification

After analysis completes, verify:

1. **Neo4j Browser** (`http://localhost:7474`)
   ```cypher
   MATCH (n) RETURN n LIMIT 25
   ```

2. **Check patterns detected**
   ```bash
   curl http://localhost:8000/patterns
   ```

3. **Verify coupling analysis**
   ```bash
   curl http://localhost:8000/coupling
   ```

## Performance Notes

- Small repos (<50 files): ~30 seconds
- Medium repos (50-200 files): 1-3 minutes
- Large repos (>200 files): 3-5 minutes

Analysis time depends on:
- Number of files
- LLM API latency
- Embedding generation speed
