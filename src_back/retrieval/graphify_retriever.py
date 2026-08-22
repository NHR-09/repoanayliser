"""
GraphifyRetriever
-----------------
Runs the `graphify` CLI on a cloned repository to produce a structured
knowledge graph (graphify-out/graph.json), then queries that graph to
provide rich, structure-aware LLM context.

This replaces ChromaDB as the primary context provider.  Neo4j is still
used for blast-radius / dependency data (unchanged).

Installation requirement (once, in the venv):
    pip install graphifyy
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphifyRetriever:
    """Provides structured LLM context from Graphify's knowledge graph."""

    def __init__(self):
        self._graph: Dict = {}          # parsed graph.json content
        self._nodes: List[Dict] = []    # flat list of graph nodes
        self._edges: List[Dict] = []    # flat list of graph edges
        self._repo_path: Optional[Path] = None
        self._indexed: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_repo(self, repo_path: str) -> bool:
        """
        Run `graphify update <repo_path>` and load the resulting graph.json.
        Returns True on success, False if Graphify is not installed or fails.
        """
        self._repo_path = Path(repo_path).resolve()  # graphify requires absolute path
        out_dir = self._repo_path / "graphify-out"
        graph_file = out_dir / "graph.json"

        # Check if already indexed (SHA256 cache inside graphify itself)
        if graph_file.exists():
            logger.info("📊 Graphify graph.json already exists — loading cached graph")
            return self._load_graph(graph_file)

        # Run graphify CLI
        logger.info(f"🔍 Running Graphify on repo: {self._repo_path}")
        success = self._run_graphify(str(self._repo_path))
        if not success:
            return False

        if not graph_file.exists():
            logger.warning("⚠️ Graphify ran but graph.json was not produced")
            return False

        return self._load_graph(graph_file)

    def get_context_for_query(self, query: str, top_k: int = 8) -> List[Dict]:
        """
        Return the top-K graph nodes most relevant to the query.
        Scores by matching query tokens against node names, types, and summaries.
        """
        if not self._nodes:
            return []

        query_tokens = set(query.lower().split())
        scored = []

        for node in self._nodes:
            score = self._score_node(node, query_tokens)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]

    def get_path_context(self, file_path: str) -> Dict:
        """
        Return all nodes that belong to a specific file and their relationships.
        Used to augment blast-radius LLM explanations with actual function names.
        """
        if not self._nodes:
            return {"functions": [], "classes": [], "imports": [], "callers": []}

        file_name = Path(file_path).name
        file_stem = Path(file_path).stem

        functions = []
        classes = []
        imports = []

        for node in self._nodes:
            node_file = node.get("file", "") or ""
            if file_name in node_file or file_stem in node_file:
                ntype = node.get("type", "")
                name = node.get("name", "")
                if not name:
                    continue
                if ntype in ("function", "method"):
                    functions.append(name)
                elif ntype == "class":
                    classes.append(name)
                elif ntype == "import":
                    imports.append(name)

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
        }

    def format_context_for_llm(self, nodes: List[Dict]) -> str:
        """
        Format a list of Graphify nodes into a structured, LLM-readable string.
        Groups nodes by file for better readability and includes signatures,
        line numbers, and inter-node call relationships.
        """
        if not nodes:
            return "No structural context available."

        # Group nodes by file
        by_file: Dict[str, List[Dict]] = {}
        for node in nodes:
            file_ = node.get("file", "") or "unknown"
            file_label = Path(file_).name if file_ != "unknown" else "unknown"
            by_file.setdefault(file_label, []).append(node)

        lines = []
        for file_label, file_nodes in by_file.items():
            lines.append(f"\n  [{file_label}]")
            for node in file_nodes:
                ntype = node.get("type", "unknown")
                name = node.get("name", "?")
                line_num = node.get("line", "")
                signature = node.get("signature", "")
                summary = node.get("summary", "") or node.get("docstring", "")
                parent = node.get("parent_class", "") or node.get("parent", "")

                detail_parts = []
                if parent:
                    detail_parts.append(f"in {parent}")
                if line_num:
                    detail_parts.append(f"L{line_num}")
                if signature:
                    detail_parts.append(f"sig: {signature[:80]}")
                if summary:
                    detail_parts.append(summary[:100])

                detail_str = f" — {', '.join(detail_parts)}" if detail_parts else ""
                lines.append(f"    {ntype}: {name}{detail_str}")

        # Add call relationships from edges
        if self._edges:
            # Build node-id to name lookup
            id_to_name: Dict[str, str] = {}
            for node in self._nodes:
                nid = node.get("id") or node.get("node_id") or node.get("name")
                if nid:
                    id_to_name[str(nid)] = node.get("name", str(nid))

            call_edges = []
            for edge in self._edges:
                etype = (edge.get("type") or edge.get("relation") or "").lower()
                if etype in ("calls", "invokes", "uses", ""):
                    src_id = str(edge.get("source") or edge.get("from") or "")
                    tgt_id = str(edge.get("target") or edge.get("to") or "")
                    src_name = id_to_name.get(src_id, "")
                    tgt_name = id_to_name.get(tgt_id, "")
                    if src_name and tgt_name and src_name != tgt_name:
                        call_edges.append(f"    {src_name} → {tgt_name}")

            if call_edges:
                lines.append("\n  [Call Relationships]")
                for ce in call_edges[:20]:
                    lines.append(ce)

        return "\n".join(lines)

    def get_dependency_edges(self) -> List[tuple]:
        """
        Extract file-to-file dependency edges from Graphify's graph.json.

        Returns a list of (source_file_path, target_file_path) tuples
        that can be merged into the NetworkX dependency graph to supplement
        the fuzzy import resolution in dependency_mapper.py.

        Edge types included: imports, depends, requires, uses, calls
        (file-level only — symbol→symbol edges filtered out).
        """
        if not self._indexed or not self._edges:
            return []

        # Build node-id → file-path lookup from all nodes
        id_to_file: Dict[str, str] = {}
        for node in self._nodes:
            node_id = node.get("id") or node.get("node_id") or node.get("name")
            file_path = node.get("file") or node.get("path") or ""
            if node_id and file_path:
                id_to_file[str(node_id)] = file_path

        # File-level edge types to include
        file_edge_types = {
            "imports", "depends", "depends_on", "requires",
            "uses", "include", "import", "dependency",
        }

        dep_edges: List[tuple] = []
        seen: set = set()

        for edge in self._edges:
            etype = (edge.get("type") or edge.get("relation") or "").lower()
            src_id  = str(edge.get("source") or edge.get("from") or "")
            tgt_id  = str(edge.get("target") or edge.get("to")   or "")

            if not src_id or not tgt_id:
                continue

            src_file = id_to_file.get(src_id, "")
            tgt_file = id_to_file.get(tgt_id, "")

            # Both ends must resolve to actual file paths
            if not src_file or not tgt_file:
                continue
            if src_file == tgt_file:
                continue  # skip self-loops

            # Only include import/dependency-style edges
            # (if etype is empty we still accept it as a dependency edge)
            if etype and etype not in file_edge_types:
                continue

            pair = (src_file, tgt_file)
            if pair not in seen:
                seen.add(pair)
                dep_edges.append(pair)

        logger.info(f"   🔗 Graphify resolved {len(dep_edges)} file-level dependency edges")
        return dep_edges

    @property
    def is_available(self) -> bool:
        """True if graph was successfully loaded and has nodes."""
        return self._indexed and len(self._nodes) > 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_graphify(self, repo_path: str) -> bool:
        """Invoke the graphify CLI as a subprocess."""
        graphify_cmd = self._find_graphify_executable()
        if not graphify_cmd:
            logger.warning(
                "⚠️ `graphify` not found on PATH. "
                "Install with: pip install graphifyy  — falling back to no structural context."
            )
            return False

        try:
            result = subprocess.run(
                [graphify_cmd, "update", repo_path],
                capture_output=True,
                text=True,
                timeout=120,   # 2 min max for large repos
                cwd=repo_path,
            )
            if result.returncode == 0:
                logger.info("✅ Graphify indexing complete")
                return True
            else:
                logger.warning(f"⚠️ Graphify exited with code {result.returncode}: {result.stderr[:300]}")
                return False
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Graphify timed out after 120 seconds")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Graphify subprocess error: {e}")
            return False

    def _find_graphify_executable(self) -> Optional[str]:
        """
        Locate the `graphify` CLI.  Checks:
          1. The venv Scripts/bin directory
          2. System PATH via `shutil.which`
        """
        import shutil

        # Check venv Scripts directory first (Windows & Unix)
        scripts_dir = Path(sys.executable).parent
        for candidate in ["graphify", "graphify.exe"]:
            full = scripts_dir / candidate
            if full.exists():
                return str(full)

        # Fallback: system PATH
        found = shutil.which("graphify")
        if found:
            return found

        return None

    def _load_graph(self, graph_file: Path) -> bool:
        """Parse graph.json and flatten into self._nodes."""
        try:
            with open(graph_file, "r", encoding="utf-8") as f:
                self._graph = json.load(f)

            # Graphify graph.json structure variants:
            # { "nodes": [...], "edges": [...] }   — standard
            # { "files": { "<path>": { "nodes": [...] } } }  — file-keyed
            # Try both.
            nodes: List[Dict] = []

            if "nodes" in self._graph:
                nodes = self._graph["nodes"]
            elif "files" in self._graph:
                for file_data in self._graph["files"].values():
                    if isinstance(file_data, dict):
                        nodes.extend(file_data.get("nodes", []))
            elif isinstance(self._graph, list):
                nodes = self._graph

            self._nodes = [n for n in nodes if isinstance(n, dict)]

            # Store edges (multiple possible key names)
            raw_edges = (
                self._graph.get("edges")
                or self._graph.get("links")
                or self._graph.get("relationships")
                or []
            )
            self._edges = [e for e in raw_edges if isinstance(e, dict)]

            self._indexed = True
            logger.info(
                f"📊 Graphify loaded {len(self._nodes)} nodes, "
                f"{len(self._edges)} edges from {graph_file}"
            )
            return True

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse graph.json: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error loading Graphify graph: {e}")
            return False

    def _score_node(self, node: Dict, query_tokens: set) -> float:
        """Score a single node for relevance to query_tokens."""
        score = 0.0
        name = (node.get("name", "") or "").lower()
        ntype = (node.get("type", "") or "").lower()
        summary = (node.get("summary", "") or node.get("docstring", "") or "").lower()
        file_ = (node.get("file", "") or "").lower()

        for token in query_tokens:
            if len(token) < 3:          # skip short stop-words
                continue
            if token in name:
                score += 3.0            # exact name match = strongest signal
            if token in summary:
                score += 1.5
            if token in file_:
                score += 1.0
            if token == ntype:
                score += 0.5

        # Boost classes and functions over imports/literals
        if ntype in ("function", "method", "class"):
            score *= 1.2

        return score
