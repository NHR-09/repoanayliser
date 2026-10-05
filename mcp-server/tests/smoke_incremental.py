from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from architech_mcp.incremental import IncrementalAnalyzer
from architech_mcp.service import ArchitechService
from architech_mcp.storage import StateStore


REPO_ID = "architech-mcp-smoke"
SNAPSHOT_ID = "architech-mcp-smoke-snapshot"


def smoke() -> None:
    service = ArchitechService()
    root = (Path(__file__).parent / "fixtures" / "live_repo").resolve()
    try:
        with service.session() as session:
            session.run(
                """
                MERGE (r:Repository {repo_id: $repo_id})
                SET r.name='MCP smoke fixture', r.path=$path, r.last_analyzed=datetime()
                MERGE (s:Snapshot {snapshot_id: $snapshot_id})
                SET s.repo_id=$repo_id, s.created_at=datetime()
                MERGE (r)-[:HAS_SNAPSHOT]->(s)
                """,
                repo_id=REPO_ID,
                snapshot_id=SNAPSHOT_ID,
                path=str(root),
            ).consume()
        with tempfile.TemporaryDirectory() as directory:
            analyzer = IncrementalAnalyzer(service, StateStore(Path(directory) / "state.db"))
            result = analyzer.sync(REPO_ID)
            functions = service.search_symbols(REPO_ID, "", ["function"], None, 10)
            context = service.function_context(REPO_ID, "main.py", "run", False, 10)
        print(json.dumps({
            "status": result["status"],
            "graph": result["graph"],
            "functions": [item["name"] for item in functions["items"]],
            "run_callees": [item["name"] for item in context.get("callees", [])],
        }))
    finally:
        with service.session() as session:
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(child)
                DETACH DELETE child, f
                """,
                repo_id=REPO_ID,
            ).consume()
            session.run(
                "MATCH (s:Snapshot {snapshot_id: $snapshot_id}) DETACH DELETE s",
                snapshot_id=SNAPSHOT_ID,
            ).consume()
            session.run(
                "MATCH (r:Repository {repo_id: $repo_id}) DETACH DELETE r",
                repo_id=REPO_ID,
            ).consume()
        service.close()


if __name__ == "__main__":
    smoke()
