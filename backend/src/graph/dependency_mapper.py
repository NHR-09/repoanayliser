from typing import Dict, List
from pathlib import Path
import networkx as nx
import logging

logger = logging.getLogger(__name__)

class DependencyMapper:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def build_graph(self, parsed_files: List[Dict]):
        # First pass: Add all files as nodes
        file_map = {}  # Map module paths to file paths
        for file_data in parsed_files:
            file_path = file_data['file']
            self.graph.add_node(file_path, **file_data)
            
            # Build module-to-file mapping
            path_obj = Path(file_path)
            filename = path_obj.stem  # filename without extension
            
            # Map: filename → file_path
            file_map[filename] = file_path
            
            # Map: ./filename → file_path (relative imports)
            file_map[f'./{filename}'] = file_path
            file_map[f'../{filename}'] = file_path
            
            # Map: full relative path from repo root
            parts = path_obj.parts
            if len(parts) >= 2:
                # Get last 2-3 parts for matching
                for i in range(max(0, len(parts)-3), len(parts)):
                    rel_path = '/'.join(parts[i:]).replace('.py', '').replace('.js', '').replace('.java', '')
                    file_map[rel_path] = file_path
        
        logger.info(f"   📋 Built module map with {len(file_map)} entries")
        
        # Second pass: Create edges based on imports
        edge_count = 0
        for file_data in parsed_files:
            file_path = file_data['file']
            
            for imp in file_data.get('imports', []):
                # Try to resolve import to actual file
                target_file = None
                
                # Direct match
                if imp in file_map:
                    target_file = file_map[imp]
                else:
                    # Try partial matches
                    for module_key, module_file in file_map.items():
                        if imp.endswith(module_key) or module_key.endswith(imp):
                            target_file = module_file
                            break
                
                if target_file and target_file != file_path:
                    self.graph.add_edge(file_path, target_file, type='imports')
                    edge_count += 1
                else:
                    # External dependency (not in our codebase)
                    self.graph.add_edge(file_path, imp, type='external')
        
        logger.info(f"   🔗 Created {edge_count} file-to-file dependencies")
        logger.info(f"   📊 Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def detect_cycles(self) -> List[List[str]]:
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []
    
    def calculate_fan_in(self, node: str) -> int:
        return self.graph.in_degree(node)
    
    def calculate_fan_out(self, node: str) -> int:
        return self.graph.out_degree(node)
    
    def get_strongly_connected_components(self) -> List[List[str]]:
        return list(nx.strongly_connected_components(self.graph))
    
    def get_blast_radius(self, file_path: str, depth: int = 3) -> List[str]:
        # Normalize path for matching
        normalized = str(Path(file_path).resolve()) if Path(file_path).exists() else file_path
        
        # Try to find the node with flexible matching
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
            except:
                pass
        
        return list(affected)
