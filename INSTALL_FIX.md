# Installation Fix

## Issue: tree-sitter version mismatch

**Fixed!** Updated `requirements.txt` to use compatible versions.

## Install Steps

```bash
cd backend

# Install all dependencies
pip install -r requirements.txt

# Verify installation
python -c "import tree_sitter; import neo4j; import groq; print('✅ All imports work')"
```

## If Still Having Issues

### Option 1: Use Virtual Environment (Recommended)

```bash
# Create venv
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install
pip install -r requirements.txt
```

### Option 2: Install Individually

```bash
pip install fastapi uvicorn
pip install neo4j gitpython networkx
pip install chromadb sentence-transformers
pip install groq python-dotenv
pip install tree-sitter==0.21.0
pip install tree-sitter-python==0.21.0
pip install tree-sitter-javascript==0.21.0
```

## Verify Setup

```bash
python init_system.py
```

Should show:
```
✅ Neo4j initialized successfully
✅ ChromaDB initialized successfully
✅ Groq API key found
✅ System ready to use!
```

## Start Server

```bash
python main.py
```

Visit: http://localhost:8000/docs

## Common Issues

### "No module named 'neo4j'"
```bash
pip install neo4j==5.14.1
```

### "No module named 'git'"
```bash
pip install gitpython==3.1.40
```

### "No module named 'groq'"
```bash
pip install groq==0.4.1
```

### Neo4j Connection Error
```bash
# Start Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.14

# Or check if running
docker ps
```

## Python Version

Requires: **Python 3.8 - 3.12**

Check version:
```bash
python --version
```

If using Python 3.13+, downgrade to 3.12 or use pyenv.
