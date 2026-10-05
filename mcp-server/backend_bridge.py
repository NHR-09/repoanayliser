"""Run heavyweight existing AnalysisEngine operations in the backend environment."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: backend_bridge.py ACTION JSON_PAYLOAD")
    action = sys.argv[1]
    payload = json.loads(sys.argv[2])
    project_root = Path(__file__).resolve().parent.parent
    backend_root = project_root / "backend"
    os.chdir(backend_root)
    sys.path.insert(0, str(backend_root))

    from src.analysis_engine import AnalysisEngine

    engine = None
    try:
        with contextlib.redirect_stdout(sys.stderr):
            engine = AnalysisEngine()
            if action == "analyze":
                source = payload["source"]
                result = (
                    engine.analyze_local_path(str(Path(source).resolve()))
                    if payload.get("source_kind") == "local"
                    else engine.analyze_repository(source)
                )
                output = {
                    "status": result.get("status"),
                    "repo_id": result.get("repo_id") or engine.current_repo_id,
                    "snapshot_id": result.get("snapshot_id") or engine.current_snapshot_id,
                    "cached": result.get("cached", False),
                    "files": (result.get("architecture") or {}).get("stats", {}).get("total_files"),
                    "source_coverage": result.get("source_coverage"),
                    "graph_revision": result.get("graph_revision"),
                }
            elif action == "architecture":
                output = engine.get_architecture_explanation(payload["repo_id"])
            else:
                raise ValueError(f"Unsupported backend action: {action}")
    finally:
        if engine is not None:
            engine.graph_db.close()
    print(json.dumps(output, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
