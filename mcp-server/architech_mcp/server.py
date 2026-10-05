from __future__ import annotations

import asyncio
import atexit
import json
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .config import config
from .incremental import IncrementalAnalyzer, LiveSyncManager
from .service import ArchitechService
from .storage import StateStore
from .utils import bounded_text, clamp, compact


service = ArchitechService()
store = StateStore(config.state_db, config.checkpoint_retention)
incremental = IncrementalAnalyzer(service, store)
live_sync = LiveSyncManager(incremental)

server = MCPServer(
    name="architech",
    title="ARCHITECH Code Intelligence",
    description="Repository-scoped architecture, dependency, impact, and code-health intelligence.",
    instructions=(
        "Start with list_repositories. Always pass repo_id and disambiguate functions with file_path. "
        "Prefer summaries; request source or LLM generation only when required. "
        "Call sync_repository_changes after local edits when live sync is not active."
    ),
    version=__version__,
)

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
LOCAL_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
ANALYZE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


def _bound_architecture(result: dict[str, Any], max_chars: int) -> dict[str, Any]:
    budget = clamp(max_chars, 1000, config.max_response_chars)
    prose_fields = [field for field in ("macro", "meso", "micro") if result.get(field)]
    per_field = max(500, budget // max(1, len(prose_fields)))
    truncated = False
    for field in prose_fields:
        result[field], was_truncated = bounded_text(str(result[field]), per_field)
        truncated = truncated or was_truncated
    if truncated:
        result["truncated"] = True
        result["hint"] = "Request a larger max_chars only if the missing prose is necessary."
    return compact(result)


@server.tool(
    description="List analyzed repositories. Returns small paginated summaries.",
    annotations=READ_ONLY,
)
async def list_repositories(
    query: str = "",
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return await asyncio.to_thread(service.list_repositories, query, cursor, limit)


@server.tool(
    description="Analyze a local directory or Git URL and store its ARCHITECH graph. This can be expensive.",
    annotations=ANALYZE,
)
async def analyze_repository(
    source: str,
    source_kind: Literal["local", "git"] = "local",
) -> dict[str, Any]:
    return await asyncio.to_thread(service.analyze_repository, source, source_kind)


@server.tool(
    description="Search files, functions, and classes inside one repository.",
    annotations=READ_ONLY,
)
async def search_symbols(
    repo_id: str,
    query: str,
    kinds: list[Literal["file", "function", "class"]] | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    selected = list(kinds) if kinds else ["file", "function", "class"]
    return await asyncio.to_thread(service.search_symbols, repo_id, query, selected, cursor, limit)


@server.tool(
    description="Get a file's symbols and direct dependency neighborhood. Source is opt-in and bounded.",
    annotations=READ_ONLY,
)
async def get_file_context(
    repo_id: str,
    file_path: str,
    include_source: bool = False,
    max_source_lines: int = 120,
    relation_limit: int = 20,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        service.file_context,
        repo_id,
        file_path,
        include_source,
        max_source_lines,
        relation_limit,
    )


@server.tool(
    description="Get one file-disambiguated function with callers and callees. Source is opt-in.",
    annotations=READ_ONLY,
)
async def get_function_context(
    repo_id: str,
    file_path: str,
    function_name: str,
    include_source: bool = False,
    relation_limit: int = 20,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        service.function_context,
        repo_id,
        file_path,
        function_name,
        include_source,
        relation_limit,
    )


@server.tool(
    description="Get cached architecture metrics, pattern evidence, and bounded prose for one repository.",
    annotations=READ_ONLY,
)
async def get_architecture(
    repo_id: str,
    include_components: bool = False,
    generate_if_missing: bool = False,
    max_chars: int = 8000,
) -> dict[str, Any]:
    result = await asyncio.to_thread(
        service.architecture,
        repo_id,
        include_components,
        generate_if_missing,
    )
    return _bound_architecture(result, max_chars)


@server.tool(
    description="Estimate reverse-dependency blast radius for modifying, moving, or deleting one file.",
    annotations=READ_ONLY,
)
async def get_change_impact(
    repo_id: str,
    file_path: str,
    change_type: Literal["modify", "move", "delete"] = "modify",
    depth: int = 2,
    limit: int = 30,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        service.change_impact,
        repo_id,
        file_path,
        change_type,
        depth,
        limit,
    )


@server.tool(
    description="List bounded static-review candidates: unused files/functions or duplicate groups.",
    annotations=READ_ONLY,
)
async def get_code_health(
    repo_id: str,
    category: Literal["files", "functions", "duplicate_functions", "duplicate_files"] = "files",
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return await asyncio.to_thread(service.code_health, repo_id, category, cursor, limit)


@server.tool(
    description="List repository snapshots or compare two snapshot IDs using compact structural metrics.",
    annotations=READ_ONLY,
)
async def get_snapshots(
    repo_id: str,
    compare_from: str | None = None,
    compare_to: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return await asyncio.to_thread(service.snapshots, repo_id, compare_from, compare_to, limit)


@server.tool(
    description="Parse only changed local files and batch-refresh graph edges; optionally keep an ephemeral checkpoint.",
    annotations=LOCAL_WRITE,
)
async def sync_repository_changes(
    repo_id: str,
    create_checkpoint: bool = False,
) -> dict[str, Any]:
    return await asyncio.to_thread(incremental.sync, repo_id, create_checkpoint, None)


@server.tool(
    description="Start, stop, or inspect a debounced local file-save watcher for incremental graph refreshes.",
    annotations=LOCAL_WRITE,
)
async def manage_live_sync(
    action: Literal["start", "stop", "status"],
    repo_id: str | None = None,
    debounce_ms: int = 750,
    checkpoint_on_change: bool = False,
) -> dict[str, Any]:
    if action in {"start", "stop"} and not repo_id:
        raise ValueError("repo_id is required for start and stop")
    if action == "start":
        return await live_sync.start(repo_id or "", debounce_ms, checkpoint_on_change)
    if action == "stop":
        return await live_sync.stop(repo_id or "")
    return live_sync.status(repo_id)


def main() -> None:
    atexit.register(service.close)
    server.run(transport="stdio")
