from __future__ import annotations

import asyncio
import hashlib
import sys
import threading
import time
from pathlib import Path
from typing import Any

from watchfiles import awatch

from .config import BACKEND_ROOT
from .service import ArchitechService
from .storage import StateStore
from .utils import SUPPORTED_EXTENSIONS, ensure_inside, relative, supported_files

from src.parser.repository_filter import FILTER_POLICY_VERSION, RepositoryFilter


class IncrementalAnalyzer:
    def __init__(self, service: ArchitechService, store: StateStore) -> None:
        self.service = service
        self.store = store
        self._lock = threading.RLock()
        backend = str(BACKEND_ROOT)
        if backend not in sys.path:
            sys.path.insert(0, backend)
        from src.graph.dependency_mapper import DependencyMapper
        from src.parser.static_parser import StaticParser

        self.parser = StaticParser()
        self.DependencyMapper = DependencyMapper

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def sync(
        self,
        repo_id: str,
        create_checkpoint: bool = False,
        changed_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        with self._lock:
            root = self.service.repository_root(repo_id)
            repository_filter = RepositoryFilter(root)
            self.store.set_repository(repo_id, str(root))
            stored_hashes = self.store.hashes(repo_id)
            bootstrap = not stored_hashes

            if bootstrap or changed_paths is None:
                candidates = supported_files(root)
                candidate_map = {str(path): path for path in candidates}
                deleted = sorted(set(stored_hashes) - set(candidate_map))
            else:
                candidate_map: dict[str, Path] = {}
                deleted = []
                for raw_path in changed_paths:
                    path = ensure_inside(root, raw_path)
                    key = str(path)
                    if not path.exists():
                        if key in stored_hashes:
                            deleted.append(key)
                        continue
                    if (
                        path.is_file()
                        and path.suffix.lower() in SUPPORTED_EXTENSIONS
                        and repository_filter.should_include(path)
                    ):
                        candidate_map[key] = path

            current_hashes: dict[str, str] = {}
            modified: list[str] = []
            for key, path in candidate_map.items():
                digest = self._hash(path)
                current_hashes[key] = digest
                if stored_hashes.get(key) != digest:
                    modified.append(key)

            if not modified and not deleted:
                return {
                    "status": "unchanged",
                    "repo_id": repo_id,
                    "bootstrap": bootstrap,
                    "storage": self.store.stats(repo_id),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                }

            parsed_changes: dict[str, dict[str, Any]] = {}
            for key in modified:
                path = candidate_map[key]
                language = SUPPORTED_EXTENSIONS[path.suffix.lower()]
                parsed = self.parser.parse_file(str(path), language)
                parsed["file_hash"] = current_hashes[key]
                parsed_changes[key] = parsed

            cached = {
                str(Path(item["file"]).resolve()): item
                for item in self.store.parsed_files(repo_id)
                if item.get("file")
            }
            cached.update(parsed_changes)
            for key in deleted:
                cached.pop(key, None)
            all_parsed = list(cached.values())

            graph_counts = self._refresh_graph(
                repo_id,
                modified,
                deleted,
                all_parsed,
                prune=bootstrap or changed_paths is None,
            )

            for key, parsed in parsed_changes.items():
                self.store.put_file(
                    repo_id,
                    key,
                    current_hashes[key],
                    parsed.get("language") or SUPPORTED_EXTENSIONS[Path(key).suffix.lower()],
                    parsed,
                )
            self.store.delete_files(repo_id, deleted)

            delta = {
                "modified": [relative(root, path) for path in modified],
                "deleted": [relative(root, path) for path in deleted],
                "hashes": {relative(root, key): current_hashes[key] for key in modified},
            }
            checkpoint_id = self.store.add_checkpoint(repo_id, delta) if create_checkpoint else None
            stored_coverage = (
                self.service.repository_coverage(repo_id)
                if not bootstrap and changed_paths is not None
                and hasattr(self.service, "repository_coverage")
                else {}
            )
            coverage = stored_coverage or repository_filter.source_coverage()
            event = self.service.publish_graph_update(
                repo_id,
                sorted(set(delta["modified"] + delta["deleted"])),
                coverage=coverage,
                filter_policy_version=FILTER_POLICY_VERSION,
            )
            return {
                "status": "updated",
                "repo_id": repo_id,
                "bootstrap": bootstrap,
                "changed": delta,
                "checkpoint_id": checkpoint_id,
                "graph": graph_counts,
                "graph_event": event,
                "source_coverage": coverage,
                "storage": self.store.stats(repo_id),
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "note": "Live graph updated without regenerating LLM architecture prose.",
            }

    def _refresh_graph(
        self,
        repo_id: str,
        modified: list[str],
        deleted: list[str],
        all_parsed: list[dict[str, Any]],
        prune: bool = False,
    ) -> dict[str, int]:
        with self.service.session() as session:
            snapshot = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(s:Snapshot)
                RETURN s.snapshot_id AS id ORDER BY s.created_at DESC LIMIT 1
                """,
                repo_id=repo_id,
            ).single()
            if not snapshot:
                raise ValueError("Run a full repository analysis before incremental synchronization")

            if prune:
                active_files = [str(Path(item["file"]).resolve()) for item in all_parsed]
                session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE NOT coalesce(f.file_path, f.path) IN $active_files
                    OPTIONAL MATCH (f)-[:CONTAINS]->(child)
                    DETACH DELETE child
                    """,
                    repo_id=repo_id,
                    active_files=active_files,
                ).consume()
                session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE NOT coalesce(f.file_path, f.path) IN $active_files
                    DETACH DELETE f
                    """,
                    repo_id=repo_id,
                    active_files=active_files,
                ).consume()

            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE coalesce(f.file_path, f.path) IN $modified
                OPTIONAL MATCH (f)-[:CONTAINS]->(child)
                DETACH DELETE child
                """,
                repo_id=repo_id,
                modified=modified,
            ).consume()
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE coalesce(f.file_path, f.path) IN $modified
                WITH DISTINCT f
                OPTIONAL MATCH (f)-[rel:IMPORTS]->()
                DELETE rel
                """,
                repo_id=repo_id,
                modified=modified,
            ).consume()
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE coalesce(f.file_path, f.path) IN $deleted
                OPTIONAL MATCH (f)-[:CONTAINS]->(child)
                DETACH DELETE child
                """,
                repo_id=repo_id,
                deleted=deleted,
            ).consume()
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE coalesce(f.file_path, f.path) IN $deleted
                DETACH DELETE f
                """,
                repo_id=repo_id,
                deleted=deleted,
            ).consume()
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[rel:DEPENDS_ON]->()
                DELETE rel
                """,
                repo_id=repo_id,
            ).consume()
            session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                WITH collect(DISTINCT f) + collect(DISTINCT fn) AS nodes
                UNWIND nodes AS n
                WITH n WHERE n IS NOT NULL
                MATCH (n)-[rel:CALLS]-()
                WITH DISTINCT rel
                DELETE rel
                """,
                repo_id=repo_id,
            ).consume()
        graph_db = self._graph_db_adapter()
        stored = graph_db.bulk_store_analysis(all_parsed, repo_id, snapshot["id"])
        mapper = self.DependencyMapper()
        mapper.build_graph(all_parsed)
        source_files = {str(Path(item["file"]).resolve()) for item in all_parsed}
        edges = [
            (source, target)
            for source, target in mapper.graph.edges()
            if source in source_files and target in source_files
        ]
        dependency_count = graph_db.bulk_create_dependencies(
            edges,
            source="mcp-live-sync",
            repo_id=repo_id,
        )
        return {
            "files": stored.get("files", 0),
            "functions": stored.get("functions", 0),
            "dependencies": dependency_count,
            "function_calls": stored.get("function_calls", 0),
        }

    def _graph_db_adapter(self):
        """Use existing batched writers while sharing this service's driver."""
        backend = str(BACKEND_ROOT)
        if backend not in sys.path:
            sys.path.insert(0, backend)
        from src.graph.graph_db import GraphDB

        adapter = object.__new__(GraphDB)
        adapter.driver = self.service.driver
        return adapter


class LiveSyncManager:
    def __init__(self, analyzer: IncrementalAnalyzer) -> None:
        self.analyzer = analyzer
        self._tasks: dict[str, asyncio.Task] = {}
        self._status: dict[str, dict[str, Any]] = {}

    async def start(self, repo_id: str, debounce_ms: int, checkpoint: bool) -> dict[str, Any]:
        existing = self._tasks.get(repo_id)
        if existing and not existing.done():
            return {"status": "already_running", **self._status.get(repo_id, {})}
        root = self.analyzer.service.repository_root(repo_id)
        debounce = max(100, min(5000, debounce_ms))
        self._status[repo_id] = {
            "repo_id": repo_id,
            "root": str(root),
            "debounce_ms": debounce,
            "checkpoint_on_change": checkpoint,
            "state": "running",
            "updates": 0,
        }
        task = asyncio.create_task(self._watch(repo_id, root, debounce, checkpoint))
        self._tasks[repo_id] = task
        return {"status": "started", **self._status[repo_id]}

    async def stop(self, repo_id: str) -> dict[str, Any]:
        task = self._tasks.pop(repo_id, None)
        if not task:
            return {"status": "not_running", "repo_id": repo_id}
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        state = self._status.get(repo_id, {"repo_id": repo_id})
        state["state"] = "stopped"
        return {"status": "stopped", **state}

    def status(self, repo_id: str | None = None) -> dict[str, Any]:
        if repo_id:
            return self._status.get(repo_id, {"repo_id": repo_id, "state": "not_running"})
        return {"watchers": list(self._status.values())}

    async def _watch(self, repo_id: str, root: Path, debounce_ms: int, checkpoint: bool) -> None:
        try:
            await asyncio.to_thread(self.analyzer.sync, repo_id, False, None)
            repository_filter = RepositoryFilter(root)
            async for changes in awatch(root, debounce=debounce_ms):
                policy_changed = any(Path(path).name == ".gitignore" for _, path in changes)
                paths = [
                    path for _, path in changes
                    if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS
                    and repository_filter.should_include(Path(path))
                ]
                if not paths and not policy_changed:
                    continue
                result = await asyncio.to_thread(
                    self.analyzer.sync,
                    repo_id,
                    checkpoint,
                    None if policy_changed else paths,
                )
                status = self._status[repo_id]
                status["updates"] = int(status.get("updates", 0)) + (result.get("status") == "updated")
                status["last_result"] = {
                    "status": result.get("status"),
                    "changed": result.get("changed"),
                    "elapsed_ms": result.get("elapsed_ms"),
                }
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._status[repo_id]["state"] = "error"
            self._status[repo_id]["error"] = f"{exc.__class__.__name__}: {exc}"
