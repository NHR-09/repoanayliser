from typing import Dict, List, Optional, Set
from pathlib import Path
import json
import os
import networkx as nx
import logging

logger = logging.getLogger(__name__)


class DependencyMapper:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, parsed_files: List[Dict]):
        self.graph = nx.DiGraph()
        source_paths = {Path(item['file']).resolve() for item in parsed_files}
        repo_root = self._find_repo_root(source_paths)
        workspace_packages = self._load_workspace_packages(repo_root, source_paths)

        for file_data in parsed_files:
            file_path = str(Path(file_data['file']).resolve())
            self.graph.add_node(file_path, **file_data)

        logger.info(
            "   Built source map with %d files and %d workspace packages",
            len(source_paths), len(workspace_packages)
        )

        edge_count = 0
        for file_data in parsed_files:
            file_path = str(Path(file_data['file']).resolve())
            for imported_module in file_data.get('imports', []):
                target = self._resolve_import(
                    imported_module,
                    Path(file_path),
                    source_paths,
                    workspace_packages
                )

                if target and str(target) != file_path:
                    self.graph.add_edge(file_path, str(target), type='imports')
                    edge_count += 1
                else:
                    self.graph.add_edge(file_path, imported_module, type='external')

        logger.info("   Created %d file-to-file dependencies", edge_count)
        logger.info(
            "   Graph: %d nodes, %d edges",
            self.graph.number_of_nodes(), self.graph.number_of_edges()
        )

    @staticmethod
    def _find_repo_root(source_paths: Set[Path]) -> Optional[Path]:
        if not source_paths:
            return None
        common = Path(os.path.commonpath([str(path) for path in source_paths]))
        if common.is_file():
            common = common.parent
        for candidate in (common, *common.parents):
            if (candidate / 'package.json').exists() or (candidate / '.git').exists():
                return candidate
        return common

    @staticmethod
    def _load_workspace_packages(
        repo_root: Optional[Path], source_paths: Set[Path]
    ) -> Dict[str, Path]:
        """Map npm workspace package names to their source entry points."""
        packages = {}
        if not repo_root:
            return packages

        for package_file in repo_root.rglob('package.json'):
            if 'node_modules' in package_file.parts:
                continue
            try:
                data = json.loads(package_file.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue

            name = data.get('name')
            if not name:
                continue

            package_dir = package_file.parent
            candidates = [
                package_dir / 'src' / 'index.ts',
                package_dir / 'src' / 'index.tsx',
                package_dir / 'src' / 'index.js',
                package_dir / 'index.ts',
                package_dir / 'index.js'
            ]
            for candidate in candidates:
                resolved = candidate.resolve()
                if resolved in source_paths:
                    packages[name] = resolved
                    break
        return packages

    def _resolve_import(
        self,
        specifier: str,
        source_file: Path,
        source_paths: Set[Path],
        workspace_packages: Dict[str, Path]
    ) -> Optional[Path]:
        specifier = specifier.split('?', 1)[0].replace('\\', '/')

        if specifier.startswith('.'):
            base = (source_file.parent / specifier).resolve()
            return self._match_source_path(base, source_paths)

        for package_name, entry_point in workspace_packages.items():
            if specifier == package_name:
                return entry_point
            if specifier.startswith(package_name + '/'):
                subpath = specifier[len(package_name) + 1:]
                package_root = (
                    entry_point.parent.parent
                    if entry_point.parent.name == 'src'
                    else entry_point.parent
                )
                for candidate in (
                    package_root / 'src' / subpath,
                    package_root / subpath
                ):
                    match = self._match_source_path(candidate.resolve(), source_paths)
                    if match:
                        return match

        return None

    @staticmethod
    def _match_source_path(candidate: Path, source_paths: Set[Path]) -> Optional[Path]:
        candidates = [candidate]
        suffix = candidate.suffix.lower()

        if suffix in ('.js', '.jsx', '.mjs', '.cjs'):
            stem = candidate.with_suffix('')
            candidates.extend(
                stem.with_suffix(ext) for ext in ('.ts', '.tsx', '.js', '.jsx')
            )
        elif not suffix:
            candidates.extend(
                candidate.with_suffix(ext)
                for ext in ('.ts', '.tsx', '.js', '.jsx', '.py')
            )

        candidates.extend(
            candidate / f'index{ext}'
            for ext in ('.ts', '.tsx', '.js', '.jsx', '.py')
        )
        for path in candidates:
            resolved = path.resolve()
            if resolved in source_paths:
                return resolved
        return None

    def detect_cycles(self) -> List[List[str]]:
        try:
            return list(nx.simple_cycles(self.graph))
        except Exception:
            return []

    def calculate_fan_in(self, node: str) -> int:
        return self.graph.in_degree(node)

    def calculate_fan_out(self, node: str) -> int:
        return self.graph.out_degree(node)

    def get_strongly_connected_components(self) -> List[List[str]]:
        return list(nx.strongly_connected_components(self.graph))

    def get_blast_radius(self, file_path: str, depth: int = 3) -> List[str]:
        normalized = str(Path(file_path).resolve()) if Path(file_path).exists() else file_path

        target_node = None
        for node in self.graph.nodes():
            if node == normalized or node.endswith(str(Path(file_path).name)):
                target_node = node
                break

        if not target_node:
            return []

        affected = set()
        for node in self.graph.nodes():
            try:
                if nx.has_path(self.graph, node, target_node):
                    path_length = nx.shortest_path_length(self.graph, node, target_node)
                    if path_length <= depth:
                        affected.add(node)
            except (nx.NetworkXError, nx.NodeNotFound):
                pass
        return list(affected)
