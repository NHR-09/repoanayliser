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

Add the local stdio server from a terminal:

```powershell
codex mcp add architech -- C:\path\to\AI-CP\mcp-server\.venv\Scripts\python.exe C:\path\to\AI-CP\mcp-server\server.py
```

Verify it with `codex mcp list`. Alternatively, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.architech]
command = "C:\\path\\to\\AI-CP\\mcp-server\\.venv\\Scripts\\python.exe"
args = ["C:\\path\\to\\AI-CP\\mcp-server\\server.py"]
```

Restart Codex, if it is already running, and ask it to call `list_repositories`.

### Claude Code

```powershell
claude mcp add --transport stdio architech -- C:\path\to\AI-CP\mcp-server\.venv\Scripts\python.exe C:\path\to\AI-CP\mcp-server\server.py
```

Verify with `claude mcp list`.

### Antigravity

In the IDE, open the agent panel’s **MCP Servers** menu, choose **Manage MCP Servers**, then **View raw config**. Add this entry to either the workspace `.agents/mcp_config.json` or the global `~/.gemini/config/mcp_config.json`:

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

Save and reload the workspace. In Antigravity CLI, `/mcp` opens the MCP manager and shows the server connection status.

### GitHub Copilot (VS Code)

For new configurations, create `.mcp.json` in the repository root (the portable format preferred by current VS Code and Copilot):

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

Run **MCP: Add Server** from the Command Palette or start the configured server through VS Code’s MCP controls, then enable it in Copilot Chat’s tool picker. VS Code still supports `.vscode/mcp.json` with a top-level `servers` object for compatibility. Do not commit credentials in either configuration file; this server reads the password from `backend/.env`.

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
