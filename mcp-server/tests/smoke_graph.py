from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from architech_mcp.service import ArchitechService


def smoke() -> None:
    service = ArchitechService()
    try:
        repositories = service.list_repositories("", None, 1)
        if not repositories["items"]:
            print(json.dumps({"status": "skipped", "reason": "No analyzed repositories"}))
            return
        repo_id = repositories["items"][0]["repo_id"]
        symbols = service.search_symbols(repo_id, "", ["file", "function"], None, 3)
        functions = service.search_symbols(repo_id, "", ["function"], None, 1)
        function = functions["items"][0] if functions["items"] else None
        function_context = (
            service.function_context(repo_id, function["path"], function["name"], False, 3)
            if function else None
        )
        file_context = (
            service.file_context(repo_id, function["path"], False, 20, 3)
            if function else None
        )
        impact = (
            service.change_impact(repo_id, function["path"], "modify", 2, 3)
            if function else None
        )
        architecture = service.architecture(repo_id, False, False)
        snapshots = service.snapshots(repo_id, None, None, 2)
        health = service.code_health(repo_id, "files", None, 2)
        print(json.dumps({
            "status": "ok",
            "repo_id": repo_id,
            "symbol_count": symbols["returned"],
            "function_context": function_context and function_context.get("name"),
            "file_context": file_context and file_context.get("path"),
            "upstream_impact_returned": impact and impact.get("upstream_impact", {}).get("counts", {}).get("returned"),
            "downstream_dependencies_returned": impact and impact.get("downstream_dependencies", {}).get("returned"),
            "architecture_snapshot": architecture.get("snapshot_id"),
            "snapshot_count": len(snapshots["items"]),
            "health_count": health["returned"],
        }))
    finally:
        service.close()


if __name__ == "__main__":
    smoke()
