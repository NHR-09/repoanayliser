from typing import Dict, List
import networkx as nx

class DependencyMapper:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def build_graph(self, parsed_files: List[Dict]):
        for file_data in parsed_files:
            file_path = file_data['file']
            self.graph.add_node(file_path, **file_data)
            
            for imp in file_data.get('imports', []):
                self.graph.add_edge(file_path, imp, type='imports')
    
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
        normalized = file_path.replace('/', '\\')
        
        # Find matching node
        matching_node = None
        for node in self.graph.nodes():
            if node == file_path or node.endswith(file_path) or file_path in node:
                matching_node = node
                break
        
        if not matching_node:
            return []
        
        affected = set()
        for node in self.graph.nodes():
            try:
                if nx.has_path(self.graph, node, matching_node):
                    path_length = nx.shortest_path_length(self.graph, node, matching_node)
                    if path_length <= depth:
                        affected.add(node)
            except:
                pass
        
        return list(affected)
