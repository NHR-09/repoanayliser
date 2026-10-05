# ARCHITECH MCP server

ARCHITECH exposes the repository knowledge graph to coding agents through a local MCP stdio server. It provides repository discovery, symbol/file/function context, architecture evidence, change impact, code-health checks, snapshots, and incremental synchronization.

## Prerequisites

- Windows, macOS, or Linux
- Python 3.11 or newer
- Neo4j running with the same database used by ARCHITECH
- The main project dependencies installed in `backend/.venv`

The MCP environment is intentionally separate from `backend/.venv`. The MCP SDK and the FastAPI application use incompatible dependency versions.

## Install

From the repository root:

```powershell
cd mcp-server
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` in the commands below.

Create or update `backend/.env` with the Neo4j settings used by the main app:

```dotenv
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
# NEO4J_DATABASE=neo4j
```

The server automatically loads `backend/.env`. If the backend environment is not at `backend/.venv`, set `ARCHITECH_BACKEND_PYTHON` to its Python executable. The optional `ARCHITECH_MCP_STATE_DB` variable changes the SQLite state-file location.

## Start manually

```powershell
cd mcp-server
.\.venv\Scripts\python.exe server.py
```

Keep this process attached to the agent. MCP uses stdin/stdout for the protocol; diagnostic output is sent to stderr.

## Agent configuration

Use absolute paths. Replace `C:\path\to\AI-CP` with this repository’s absolute path.

### Codex

Add a local MCP server in Codex settings with:

```json
{
  "mcpServers": {
    "architech": {
      "command": "C:\\path\\to\\AI-CP\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\AI-CP\\mcp-server\\server.py"]
    }
  }
}
```

Restart Codex and ask it to call `list_repositories`.

### Claude Code

```powershell
claude mcp add --transport stdio architech -- C:\path\to\AI-CP\mcp-server\.venv\Scripts\python.exe C:\path\to\AI-CP\mcp-server\server.py
```

Verify with `claude mcp list`.

### Antigravity

In Antigravity’s MCP settings, add a local/stdio server:

- Name: `architech`
- Command: `C:\path\to\AI-CP\mcp-server\.venv\Scripts\python.exe`
- Arguments: `C:\path\to\AI-CP\mcp-server\server.py`

Save and reload the workspace.

### GitHub Copilot (VS Code)

Add this to the workspace MCP configuration, normally `.vscode/mcp.json`:

```json
{
  "servers": {
    "architech": {
      "type": "stdio",
      "command": "C:\\path\\to\\AI-CP\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\AI-CP\\mcp-server\\server.py"]
    }
  }
}
```

Start or restart the server from VS Code’s MCP controls, then enable it for Copilot Chat. Do not commit credentials in `.vscode/mcp.json`; this server reads the password from `backend/.env`.

## Recommended first-use flow

1. Call `list_repositories` and choose a `repo_id`.
2. Use `search_symbols`, then request focused file or function context.
3. Run `sync_repository_changes` after edits, or use `manage_live_sync` for a local repository.
4. Request architecture generation explicitly when prose is needed.

`manage_live_sync` is process-local, so restart it after an agent restart. The first sync bootstraps parser state; later syncs process only changed files. No database-delete tool is exposed.

## Troubleshooting

- `NEO4J_PASSWORD is missing`: add it to `backend/.env` and restart the MCP process.
- Neo4j connection failure: start Neo4j and verify URI, user, password, and database.
- Backend import failure: install the main project dependencies in `backend/.venv`, or set `ARCHITECH_BACKEND_PYTHON`.
- No tools appear: verify the client uses the MCP virtualenv Python and absolute `server.py` path, then reload it.
- A repository is missing: analyze it through ARCHITECH first, then call `list_repositories` again.

Runtime parser state is stored in `mcp-server/.data/state.sqlite3` and is local cache data.
