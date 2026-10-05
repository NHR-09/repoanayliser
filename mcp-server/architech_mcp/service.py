from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from neo4j import GraphDatabase

from .config import BACKEND_ROOT, MCP_ROOT, config
from .utils import clamp, compact, ensure_inside, page, relative, source_excerpt

from src.parser.repository_filter import RepositoryFilter, is_obviously_ignored
from src.graph.live_events import notify_web_backend
from src.analysis.architecture_grounding import (
    ARCHITECTURE_SCHEMA_VERSION,
    ARCHITECTURE_VALIDATOR_VERSION,
    collect_architecture_evidence,
    interpretation_cache_status,
    parse_structured_interpretation,
    render_interpretation,
    validate_interpretation,
)


class ArchitechService:
    def __init__(self) -> None:
        self._driver = None
        self._backend_lock = threading.RLock()

    @property
    def driver(self):
        if self._driver is None:
            if not config.neo4j_password:
                raise RuntimeError("NEO4J_PASSWORD is missing from backend/.env")
            self._driver = GraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_user, config.neo4j_password),
            )
            self._driver.verify_connectivity()
        return self._driver

    def session(self):
        kwargs = {"database": config.database} if config.database else {}
        return self.driver.session(**kwargs)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def repository(self, repo_id: str) -> dict[str, Any]:
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})
                RETURN r.repo_id AS repo_id, r.name AS name, r.url AS url,
                       r.path AS path, r.current_commit AS current_commit,
                       toString(r.last_analyzed) AS last_analyzed
                """,
                repo_id=repo_id,
            ).single()
        if not row:
            raise ValueError(f"Repository '{repo_id}' was not found")
        return dict(row)

    def repository_root(self, repo_id: str) -> Path:
        repo = self.repository(repo_id)
        configured = Path(repo.get("path") or "")
        root = (
            configured.resolve()
            if configured.is_absolute()
            else (BACKEND_ROOT / configured).resolve()
        )
        if not root.is_dir():
            raise ValueError("The analyzed repository is not available on this machine")
        return root

    def repository_coverage(self, repo_id: str) -> dict[str, Any]:
        with self.session() as session:
            row = session.run(
                "MATCH (r:Repository {repo_id: $repo_id}) RETURN r.source_coverage AS coverage",
                repo_id=repo_id,
            ).single()
        try:
            return json.loads((row["coverage"] if row else None) or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def publish_graph_update(
        self,
        repo_id: str,
        changed_files: list[str],
        *,
        coverage: dict[str, Any],
        filter_policy_version: int,
    ) -> dict[str, Any]:
        """Publish a cross-process notification by advancing Neo4j's graph revision."""
        all_safe_paths = sorted({str(path).replace("\\", "/") for path in changed_files})
        safe_paths = all_safe_paths[:100]
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})
                SET r.graph_revision = coalesce(r.graph_revision, 0) + 1,
                    r.graph_updated_at = datetime(),
                    r.live_updated_at = datetime(),
                    r.graph_changed_files = $changed_files,
                    r.graph_changed_file_count = $changed_file_count,
                    r.source_coverage = $source_coverage,
                    r.filter_policy_version = $filter_policy_version
                RETURN r.graph_revision AS version, toString(r.graph_updated_at) AS updated_at
                """,
                repo_id=repo_id,
                changed_files=json.dumps(safe_paths, separators=(",", ":")),
                changed_file_count=len(all_safe_paths),
                source_coverage=json.dumps(coverage, separators=(",", ":")),
                filter_policy_version=filter_policy_version,
            ).single()
        if not row:
            raise ValueError(f"Repository '{repo_id}' was not found")
        event = {
            "event": "graph_updated",
            "repo_id": repo_id,
            "version": int(row["version"] or 0),
            "changed_files": safe_paths,
            "changed_file_count": len(all_safe_paths),
            "updated_at": row["updated_at"],
        }
        event["web_notified"] = notify_web_backend(event)
        return event

    def list_repositories(self, query: str, cursor: str | None, limit: int) -> dict[str, Any]:
        with self.session() as session:
            rows = session.run(
                """
                MATCH (r:Repository)
                WHERE $needle = '' OR toLower(coalesce(r.name, '')) CONTAINS $needle
                   OR toLower(coalesce(r.url, '')) CONTAINS $needle
                   OR toLower(coalesce(r.path, '')) CONTAINS $needle
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                WITH r, count(DISTINCT f) AS files
                OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(fn:Function)
                WITH r, files, count(DISTINCT fn) AS functions
                OPTIONAL MATCH (r)-[:HAS_SNAPSHOT]->(s:Snapshot)
                RETURN r.repo_id AS repo_id, r.name AS name, r.url AS url,
                       r.path AS local_path, r.current_commit AS commit,
                       toString(r.last_analyzed) AS analyzed_at,
                       files, functions, count(DISTINCT s) AS snapshots,
                       r.last_analyzed AS _sort_time
                ORDER BY _sort_time DESC
                """,
                needle=(query or "").casefold(),
            )
            items = []
            for row in rows:
                item = dict(row)
                item.pop("_sort_time", None)
                items.append(compact(item))
        return page(items, cursor, limit, config.max_page_size)

    def search_symbols(
        self,
        repo_id: str,
        query: str,
        kinds: list[str],
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        self.repository(repo_id)
        allowed = {"file", "function", "class"}
        requested = set(kinds or allowed) & allowed
        if not requested:
            raise ValueError("kinds must include file, function, or class")
        needle = (query or "").casefold()
        items: list[dict[str, Any]] = []
        with self.session() as session:
            if "file" in requested:
                rows = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WITH r, f, coalesce(f.file_path, f.path) AS path
                    WHERE $needle = '' OR toLower(path) CONTAINS $needle
                    RETURN 'file' AS kind, path, null AS name, null AS line
                    LIMIT 500
                    """,
                    repo_id=repo_id,
                    needle=needle,
                )
                items.extend(dict(row) for row in rows)
            if "function" in requested:
                rows = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(n:Function)
                    WITH n, coalesce(f.file_path, f.path) AS path
                    WHERE $needle = '' OR toLower(n.name) CONTAINS $needle OR toLower(path) CONTAINS $needle
                    RETURN 'function' AS kind, path, n.name AS name, n.line AS line
                    LIMIT 500
                    """,
                    repo_id=repo_id,
                    needle=needle,
                )
                items.extend(dict(row) for row in rows)
            if "class" in requested:
                rows = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(n:Class)
                    WITH n, coalesce(f.file_path, f.path) AS path
                    WHERE $needle = '' OR toLower(n.name) CONTAINS $needle OR toLower(path) CONTAINS $needle
                    RETURN 'class' AS kind, path, n.name AS name, n.line AS line
                    LIMIT 500
                    """,
                    repo_id=repo_id,
                    needle=needle,
                )
                items.extend(dict(row) for row in rows)
        root = self.repository_root(repo_id)
        repository_filter = RepositoryFilter(root)
        included_paths = {
            str(path.resolve())
            for path in repository_filter.filter_paths(
                item["path"] for item in items if item.get("path")
            )
        }
        items = [
            item for item in items
            if item.get("path") and str(Path(item["path"]).resolve()) in included_paths
        ]
        for item in items:
            item["path"] = relative(root, item.get("path"))
        items.sort(key=lambda item: (item["kind"], item.get("path") or "", item.get("line") or 0))
        result = page(items, cursor, limit, config.max_page_size)
        result["query"] = query
        return compact(result)

    def _resolve_graph_file(self, repo_id: str, file_path: str) -> tuple[Path, dict[str, Any]]:
        root = self.repository_root(repo_id)
        requested = ensure_inside(root, file_path)
        if not RepositoryFilter(root).should_include(requested):
            raise ValueError(f"File '{file_path}' is excluded by the repository filtering policy")
        normalized = requested.as_posix()
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WITH f, coalesce(f.file_path, f.path) AS path
                WHERE path = $native
                   OR f.path_normalized = $absolute
                   OR f.path_normalized ENDS WITH '/' + $relative
                RETURN path, f.language AS language, f.content_hash AS content_hash
                ORDER BY CASE WHEN path = $native OR f.path_normalized = $absolute THEN 0 ELSE 1 END
                LIMIT 1
                """,
                repo_id=repo_id,
                native=str(requested),
                absolute=normalized,
                relative=requested.relative_to(root).as_posix(),
            ).single()
        if not row:
            raise ValueError(f"File '{file_path}' is not present in repository '{repo_id}'")
        return Path(row["path"]), dict(row)

    def file_context(
        self,
        repo_id: str,
        file_path: str,
        include_source: bool,
        max_source_lines: int,
        relation_limit: int,
    ) -> dict[str, Any]:
        root = self.repository_root(repo_id)
        absolute, metadata = self._resolve_graph_file(repo_id, file_path)
        cap = clamp(relation_limit, 1, 100)
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE coalesce(f.file_path, f.path) = $path
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(out:File)<-[:CONTAINS]-(r)
                WITH r, f, collect(DISTINCT coalesce(out.file_path, out.path))[0..$limit] AS dependencies
                OPTIONAL MATCH (r)-[:CONTAINS]->(inc:File)-[:DEPENDS_ON]->(f)
                WITH r, f, dependencies, collect(DISTINCT coalesce(inc.file_path, inc.path))[0..$limit] AS dependents
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                WITH r, f, dependencies, dependents,
                     collect(DISTINCT {name: fn.name, line: fn.line, parent_class: fn.parent_class})[0..$limit] AS functions
                OPTIONAL MATCH (f)-[:CONTAINS]->(cls:Class)
                RETURN dependencies, dependents, functions,
                       collect(DISTINCT {name: cls.name, line: cls.line})[0..$limit] AS classes
                """,
                repo_id=repo_id,
                path=metadata["path"],
                limit=cap,
            ).single()
        data = dict(row) if row else {}
        for field in ("dependencies", "dependents"):
            data[field] = [
                relative(root, path) for path in data.get(field, [])
                if path and RepositoryFilter(root).should_include(Path(path))
            ]
        result = {
            "path": relative(root, metadata["path"]),
            "language": metadata.get("language"),
            "content_hash": metadata.get("content_hash"),
            **data,
        }
        if include_source:
            result["source"] = source_excerpt(
                absolute,
                max_lines=clamp(max_source_lines, 1, config.max_source_lines),
                max_chars=config.max_response_chars // 2,
            )
        return compact(result)

    def function_context(
        self,
        repo_id: str,
        file_path: str,
        function_name: str,
        include_source: bool,
        relation_limit: int,
    ) -> dict[str, Any]:
        root = self.repository_root(repo_id)
        absolute, metadata = self._resolve_graph_file(repo_id, file_path)
        cap = clamp(relation_limit, 1, 100)
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function {name: $name})
                WHERE coalesce(f.file_path, f.path) = $path
                OPTIONAL MATCH (r)-[:CONTAINS]->(caller_file:File)-[:CONTAINS]->(caller:Function)-[call:CALLS]->(fn)
                WITH r, f, fn, collect(DISTINCT {
                    name: caller.name, file: coalesce(caller_file.file_path, caller_file.path), line: call.line
                })[0..$limit] AS callers
                OPTIONAL MATCH (fn)-[out_call:CALLS]->(callee:Function)<-[:CONTAINS]-(callee_file:File)<-[:CONTAINS]-(r)
                RETURN fn.name AS name, fn.line AS line, fn.parent_class AS parent_class,
                       callers, collect(DISTINCT {
                           name: callee.name, file: coalesce(callee_file.file_path, callee_file.path), line: out_call.line
                       })[0..$limit] AS callees
                LIMIT 1
                """,
                repo_id=repo_id,
                path=metadata["path"],
                name=function_name,
                limit=cap,
            ).single()
        if not row:
            raise ValueError(f"Function '{function_name}' was not found in '{file_path}'")
        result = dict(row)
        result["file"] = relative(root, metadata["path"])
        for field in ("callers", "callees"):
            cleaned = []
            for item in result.get(field, []):
                if item.get("name"):
                    item = dict(item)
                    if item.get("file") and not RepositoryFilter(root).should_include(Path(item["file"])):
                        continue
                    item["file"] = relative(root, item.get("file"))
                    cleaned.append(compact(item))
            result[field] = cleaned
        if include_source:
            result["source"] = source_excerpt(
                absolute,
                start_line=int(result.get("line") or 1),
                max_lines=120,
                max_chars=config.max_response_chars // 2,
            )
        return compact(result)

    def architecture(self, repo_id: str, include_components: bool, generate_if_missing: bool) -> dict[str, Any]:
        root = self.repository_root(repo_id)
        with self.session() as session:
            row = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(s:Snapshot)
                RETURN s.snapshot_id AS snapshot_id, toString(s.created_at) AS created_at,
                       s.commit_hash AS commit, s.arch_macro AS macro,
                       s.arch_meso AS meso, s.arch_micro AS micro,
                       s.arch_interpretation_json AS interpretation_json,
                       s.arch_schema_version AS schema_version,
                       s.arch_validator_version AS validator_version,
                       s.arch_validation_status AS validation_status,
                       s.arch_validation_errors AS validation_errors,
                       s.arch_graph_revision AS interpretation_revision,
                       toString(s.arch_generated_at) AS interpretation_generated_at,
                       coalesce(r.graph_revision, 0) AS graph_revision,
                       r.source_coverage AS repository_coverage,
                       s.source_coverage AS snapshot_coverage
                ORDER BY s.created_at DESC LIMIT 1
                """,
                repo_id=repo_id,
            ).single()
        if not row:
            raise ValueError("No architecture snapshot exists for this repository")
        snapshot = dict(row)
        structural = self._live_architecture_evidence(repo_id, root)
        patterns = structural.pop("_raw_patterns", {})
        grounding = structural.pop("_grounding", None)
        result = {
            "snapshot_id": snapshot.get("snapshot_id"),
            "created_at": snapshot.get("created_at"),
            "commit": snapshot.get("commit"),
            "graph_revision": int(snapshot.get("graph_revision") or 0),
            **structural,
        }
        detected = []
        for name, evidence in patterns.items():
            if not isinstance(evidence, dict) or not evidence.get("detected"):
                continue
            item = {"name": name, "confidence": evidence.get("confidence")}
            if include_components:
                component_evidence = {}
                for key, values in evidence.items():
                    if not isinstance(values, list):
                        continue
                    if key.endswith("_files") or key in {"files", "components", "layers", "core_modules", "plugins"}:
                        component_evidence[key] = [
                            relative(root, value) if isinstance(value, str) else value
                            for value in values[:20]
                        ]
                item["evidence"] = component_evidence
            detected.append(compact(item))
        detected.sort(key=lambda item: item.get("confidence") or 0, reverse=True)
        result["patterns"] = detected
        coverage_raw = snapshot.get("repository_coverage") or snapshot.get("snapshot_coverage")
        try:
            coverage = json.loads(coverage_raw or "{}")
        except (json.JSONDecodeError, TypeError):
            coverage = {}
        if coverage:
            result["source_coverage"] = coverage

        interpretation_revision = snapshot.get("interpretation_revision")
        graph_revision = result["graph_revision"]
        status = interpretation_cache_status(
            interpretation_revision=interpretation_revision,
            current_revision=graph_revision,
            schema_version=snapshot.get("schema_version"),
            validator_version=snapshot.get("validator_version"),
            validation_status=snapshot.get("validation_status"),
            has_interpretation=bool(snapshot.get("interpretation_json")),
        )
        if generate_if_missing and status != "current":
            self._generate_architecture(repo_id)
            return self.architecture(repo_id, include_components, False)
        if status == "current" and grounding is None:
            status = "invalid"
            validation_errors = ["Current graph evidence was unavailable for validation."]
        if status == "current" and grounding is not None:
            parsed, parse_errors = parse_structured_interpretation(snapshot.get("interpretation_json"))
            validated, validation_errors = (None, parse_errors)
            if parsed is not None:
                validated, validation_errors = validate_interpretation(parsed, grounding)
            if validated is None:
                status = "invalid"
                validation_errors = list(dict.fromkeys(validation_errors))[:20]
            else:
                rendered = render_interpretation(validated)
                result.update({
                    "macro": rendered["overview"],
                    "meso": rendered["modules"],
                    "micro": rendered["key_files"],
                })
                result["interpretation"] = {
                    "status": "current",
                    "graph_revision": graph_revision,
                    "current_graph_revision": graph_revision,
                    "generated_at": snapshot.get("interpretation_generated_at"),
                    "schema_version": ARCHITECTURE_SCHEMA_VERSION,
                    "validator_version": ARCHITECTURE_VALIDATOR_VERSION,
                    "data": validated,
                }
        if status != "current":
            try:
                cached_errors = json.loads(snapshot.get("validation_errors") or "[]")
            except (json.JSONDecodeError, TypeError):
                cached_errors = []
            if 'validation_errors' in locals():
                cached_errors = validation_errors
            result["interpretation"] = {
                "status": status,
                "generated_for_graph_revision": interpretation_revision,
                "current_graph_revision": graph_revision,
                "schema_version": snapshot.get("schema_version"),
                "validator_version": snapshot.get("validator_version"),
                "validation_errors": cached_errors[:20],
                "reason": (
                    "Current structural evidence is authoritative. Architecture prose is withheld "
                    "because it is stale, missing, or has not passed the current grounding validator. "
                    "Set generate_if_missing=true to regenerate explicitly."
                ),
            }
        return compact(result)

    def _live_architecture_evidence(self, repo_id: str, root: Path) -> dict[str, Any]:
        """Compute current architecture evidence directly from repository-scoped graph nodes."""
        import networkx as nx
        from src.graph.analyzers import CouplingAnalyzer, PatternDetector

        grounding = collect_architecture_evidence(
            SimpleNamespace(driver=self.driver), repo_id, root
        )
        graph = nx.DiGraph()
        for path_key, path in grounding.files.items():
            detail = grounding.file_details[path_key]
            graph.add_node(
                path,
                language=detail.get("language"),
                functions=[{"name": name} for name in detail.get("functions", [])],
                classes=[{"name": name} for name in detail.get("classes", [])],
                imports=detail.get("imports", []),
            )
        for source, target in grounding.dependencies:
            graph.add_edge(grounding.files[source], grounding.files[target])

        patterns = PatternDetector(graph).detect_patterns()
        coupling = CouplingAnalyzer(graph).analyze()
        return {
            "total_files": graph.number_of_nodes(),
            "total_dependencies": graph.number_of_edges(),
            "avg_coupling": coupling.get("metrics", {}).get("avg_coupling", 0),
            "cycle_count": len(coupling.get("cycles", [])),
            "_raw_patterns": patterns,
            "structural_evidence": grounding.public_evidence(patterns),
            "_grounding": grounding,
        }

    def _generate_architecture(self, repo_id: str) -> dict[str, Any]:
        return self._run_backend("architecture", {"repo_id": repo_id})

    def analyze_repository(self, source: str, source_kind: str) -> dict[str, Any]:
        if source_kind not in {"local", "git"}:
            raise ValueError("source_kind must be 'local' or 'git'")
        result = self._run_backend(
            "analyze",
            {"source": source, "source_kind": source_kind},
            timeout=3600,
        )
        return compact({
            "status": result.get("status"),
            "repo_id": result.get("repo_id"),
            "snapshot_id": result.get("snapshot_id"),
            "cached": result.get("cached", False),
            "files": result.get("files"),
            "source_coverage": result.get("source_coverage"),
            "graph_revision": result.get("graph_revision"),
            "message": "Analysis complete. Query focused context with repository-scoped tools.",
        })

    def _run_backend(self, action: str, payload: dict[str, Any], timeout: int = 900) -> dict[str, Any]:
        python = config.backend_python.resolve()
        if not python.is_file():
            raise RuntimeError(
                "Backend Python was not found. Set ARCHITECH_BACKEND_PYTHON to backend's virtual-environment Python."
            )
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        with self._backend_lock:
            process = subprocess.run(
                [
                    str(python),
                    str(MCP_ROOT / "backend_bridge.py"),
                    action,
                    json.dumps(payload, ensure_ascii=False),
                ],
                cwd=BACKEND_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        if process.returncode != 0:
            detail = process.stderr.strip().splitlines()[-1] if process.stderr.strip() else "unknown backend error"
            raise RuntimeError(f"ARCHITECH backend operation failed: {detail}")
        try:
            return json.loads(process.stdout.strip())
        except json.JSONDecodeError:
            raise RuntimeError("ARCHITECH backend returned an invalid response") from None

    def change_impact(self, repo_id: str, file_path: str, change_type: str, depth: int, limit: int) -> dict[str, Any]:
        if change_type not in {"modify", "delete", "move"}:
            raise ValueError("change_type must be modify, delete, or move")
        root = self.repository_root(repo_id)
        _, metadata = self._resolve_graph_file(repo_id, file_path)
        hops = clamp(depth, 1, 3)
        cap = clamp(limit, 1, 100)
        upstream_query = f"""
            MATCH (r:Repository {{repo_id: $repo_id}})-[:CONTAINS]->(target:File)
            WHERE coalesce(target.file_path, target.path) = $path
            OPTIONAL MATCH p=(source:File)-[:DEPENDS_ON*1..{hops}]->(target)
            WHERE (r)-[:CONTAINS]->(source)
              AND all(n IN nodes(p) WHERE (r)-[:CONTAINS]->(n))
            WITH target, source, CASE WHEN p IS NULL THEN null ELSE length(p) END AS distance
            ORDER BY distance, coalesce(source.file_path, source.path)
            RETURN collect(DISTINCT {{file: coalesce(source.file_path, source.path), distance: distance}})[0..$limit] AS items
        """
        downstream_query = f"""
            MATCH (r:Repository {{repo_id: $repo_id}})-[:CONTAINS]->(target:File)
            WHERE coalesce(target.file_path, target.path) = $path
            OPTIONAL MATCH p=(target)-[:DEPENDS_ON*1..{hops}]->(dependency:File)
            WHERE (r)-[:CONTAINS]->(dependency)
              AND all(n IN nodes(p) WHERE (r)-[:CONTAINS]->(n))
            WITH target, dependency, CASE WHEN p IS NULL THEN null ELSE length(p) END AS distance
            ORDER BY distance, coalesce(dependency.file_path, dependency.path)
            RETURN collect(DISTINCT {{file: coalesce(dependency.file_path, dependency.path), distance: distance}})[0..$limit] AS items
        """
        with self.session() as session:
            upstream_row = session.run(
                upstream_query,
                repo_id=repo_id,
                path=metadata["path"],
                limit=cap,
            ).single()
            downstream_row = session.run(
                downstream_query,
                repo_id=repo_id,
                path=metadata["path"],
                limit=cap,
            ).single()
        repository_filter = RepositoryFilter(root)

        def clean(row):
            return [
                {"file": relative(root, item["file"]), "distance": item.get("distance")}
                for item in (row["items"] if row else [])
                if item.get("file") and repository_filter.should_include(Path(item["file"]))
            ]

        upstream = clean(upstream_row)
        downstream = clean(downstream_row)
        direct = sum(1 for item in upstream if item.get("distance") == 1)
        indirect = len(upstream) - direct
        base = direct * 12 + indirect * 5
        multiplier = {"modify": 1.0, "move": 1.25, "delete": 1.5}[change_type]
        score = min(100, round(base * multiplier))
        level = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 20 else "low"
        return {
            "file": relative(root, metadata["path"]),
            "change_type": change_type,
            "risk": {"score": score, "level": level},
            "upstream_impact": {
                "semantics": "Reverse dependencies: code that depends on the changed file and may be affected by the change.",
                "counts": {"direct": direct, "transitive": indirect, "returned": len(upstream)},
                "items": upstream,
            },
            "downstream_dependencies": {
                "semantics": "Forward dependencies: code the changed file relies on; these are not automatically classified as affected.",
                "items": downstream,
                "returned": len(downstream),
            },
            "depth": hops,
            "caveat": (
                "Risk scoring uses upstream impact only. Static analysis can miss framework registration, "
                "reflection, runtime imports, and dynamically dispatched relationships."
            ),
        }

    def code_health(self, repo_id: str, category: str, cursor: str | None, limit: int) -> dict[str, Any]:
        root = self.repository_root(repo_id)
        conventional_names = {
            "__init__", "__new__", "main", "run", "setup", "teardown",
            "setUp", "tearDown", "render", "register", "configure", "initialize",
        }
        queries = {
            "files": """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (r)-[:CONTAINS]->(incoming:File)-[:DEPENDS_ON]->(f)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(outgoing:File)<-[:CONTAINS]-(r)
                WITH f, count(DISTINCT incoming) AS fan_in, count(DISTINCT outgoing) AS fan_out
                WHERE fan_in = 0
                RETURN coalesce(f.file_path, f.path) AS file, fan_in, fan_out
                ORDER BY fan_out, file LIMIT 500
            """,
            "functions": """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(caller:Function)-[:CALLS]->(fn)
                OPTIONAL MATCH (r)-[:CONTAINS]->(caller_file:File)-[:CALLS]->(fn)
                WITH f, fn, count(DISTINCT caller) + count(DISTINCT caller_file) AS callers
                WHERE callers = 0 AND NOT fn.name STARTS WITH 'test' AND NOT fn.name STARTS WITH '__'
                RETURN fn.name AS name, coalesce(f.file_path, f.path) AS file, fn.line AS line
                ORDER BY file, line LIMIT 500
            """,
            "duplicate_functions": """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                WITH fn.name AS name, collect(DISTINCT {file: coalesce(f.file_path, f.path), line: fn.line}) AS occurrences
                WHERE size(occurrences) > 1
                RETURN name, occurrences ORDER BY size(occurrences) DESC, name LIMIT 200
            """,
            "duplicate_files": """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE f.content_hash IS NOT NULL AND f.content_hash <> ''
                WITH f.content_hash AS hash, collect(DISTINCT coalesce(f.file_path, f.path)) AS files
                WHERE size(files) > 1
                RETURN hash, files ORDER BY size(files) DESC LIMIT 200
            """,
        }
        if category not in queries:
            raise ValueError(f"category must be one of: {', '.join(queries)}")
        with self.session() as session:
            items = [dict(row) for row in session.run(queries[category], repo_id=repo_id)]
        repository_filter = RepositoryFilter(root)
        candidate_paths = []
        for item in items:
            if item.get("file"):
                candidate_paths.append(item["file"])
            candidate_paths.extend(item.get("files") or [])
            candidate_paths.extend(
                entry.get("file") for entry in (item.get("occurrences") or [])
                if entry.get("file")
            )
        included_paths = {
            str(path.resolve()) for path in repository_filter.filter_paths(candidate_paths)
        }
        filtered = []
        for item in items:
            paths = []
            if item.get("file"):
                paths.append(item["file"])
            paths.extend(item.get("files") or [])
            paths.extend(entry.get("file") for entry in (item.get("occurrences") or []) if entry.get("file"))
            if paths and not all(str(Path(path).resolve()) in included_paths for path in paths):
                continue
            if category == "duplicate_functions" and item.get("name") in conventional_names:
                continue
            if item.get("file"):
                item["file"] = relative(root, item["file"])
            if item.get("files"):
                item["files"] = [relative(root, path) for path in item["files"]]
            if item.get("occurrences"):
                item["occurrences"] = [
                    {**dict(entry), "file": relative(root, entry.get("file"))}
                    for entry in item["occurrences"]
                ]
            if category == "duplicate_functions":
                item["confidence"] = "low"
                item["reason"] = "Repeated names are candidates only; bodies and behavior are not proven identical."
            elif category in {"files", "functions"}:
                item["confidence"] = "candidate"
            filtered.append(item)
        result = page(filtered, cursor, limit, config.max_page_size)
        result.update({
            "category": category,
            "caveat": "Candidates require human review; dynamic entry points and framework hooks can look unused.",
        })
        return compact(result)

    def snapshots(
        self,
        repo_id: str,
        compare_from: str | None,
        compare_to: str | None,
        limit: int,
    ) -> dict[str, Any]:
        self.repository(repo_id)
        if bool(compare_from) != bool(compare_to):
            raise ValueError("Provide both compare_from and compare_to, or neither")
        with self.session() as session:
            if compare_from and compare_to:
                rows = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(a:Snapshot {snapshot_id: $from_id})
                    MATCH (r)-[:HAS_SNAPSHOT]->(b:Snapshot {snapshot_id: $to_id})
                    RETURN a.snapshot_id AS from_id, b.snapshot_id AS to_id,
                           a.total_files AS from_files, b.total_files AS to_files,
                           a.total_deps AS from_dependencies, b.total_deps AS to_dependencies,
                           a.cycle_count AS from_cycles, b.cycle_count AS to_cycles,
                           a.avg_coupling AS from_coupling, b.avg_coupling AS to_coupling,
                           a.patterns AS from_patterns, b.patterns AS to_patterns
                    """,
                    repo_id=repo_id,
                    from_id=compare_from,
                    to_id=compare_to,
                ).single()
                if not rows:
                    raise ValueError("One or both snapshots were not found in this repository")
                data = dict(rows)
                for key in ("from_patterns", "to_patterns"):
                    try:
                        parsed = json.loads(data.pop(key) or "{}")
                    except json.JSONDecodeError:
                        parsed = {}
                    data[key.replace("_patterns", "_detected_patterns")] = sorted(
                        name for name, evidence in parsed.items()
                        if isinstance(evidence, dict) and evidence.get("detected")
                    )[:clamp(limit, 1, 100)]
                return compact(data)
            rows = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(s:Snapshot)
                RETURN s.snapshot_id AS snapshot_id, s.commit_hash AS commit,
                       toString(s.created_at) AS created_at, s.total_files AS files,
                       s.total_deps AS dependencies, s.cycle_count AS cycles,
                       s.avg_coupling AS avg_coupling
                ORDER BY s.created_at DESC LIMIT $limit
                """,
                repo_id=repo_id,
                limit=clamp(limit, 1, 100),
            )
            return {"items": [compact(dict(row)) for row in rows]}
