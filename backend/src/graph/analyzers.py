from typing import Dict, List
import networkx as nx

class PatternDetector:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def detect_patterns(self) -> Dict:
        return {
            'layered': self._detect_layered(),
            'mvc': self._detect_mvc(),
            'hexagonal': self._detect_hexagonal()
        }
    
    def _detect_layered(self) -> Dict:
        layers = []
        for node in self.graph.nodes():
            if any(x in node.lower() for x in ['controller', 'api', 'route']):
                layers.append('presentation')
            elif any(x in node.lower() for x in ['service', 'business']):
                layers.append('business')
            elif any(x in node.lower() for x in ['repository', 'dao', 'db']):
                layers.append('data')
        
        unique_layers = list(set(layers))
        return {
            'detected': len(unique_layers) >= 3,
            'layers': unique_layers,
            'confidence': 0.8 if len(unique_layers) >= 3 else 0.3
        }
    
    def _detect_mvc(self) -> Dict:
        controllers = [n for n in self.graph.nodes() if any(x in n.lower() for x in ['controller', 'route'])]
        models = [n for n in self.graph.nodes() if any(x in n.lower() for x in ['model', 'entity'])]
        
        return {
            'detected': bool(controllers and models),
            'controllers': len(controllers),
            'models': len(models),
            'confidence': 0.9 if controllers and models else 0.2
        }
    
    def _detect_hexagonal(self) -> Dict:
        ports = [n for n in self.graph.nodes() if any(x in n.lower() for x in ['port', 'interface'])]
        adapters = [n for n in self.graph.nodes() if any(x in n.lower() for x in ['adapter', 'repository'])]
        
        return {
            'detected': bool(ports and adapters),
            'confidence': 0.7 if ports and adapters else 0.1
        }

class CouplingAnalyzer:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def analyze(self) -> Dict:
        return {
            'high_coupling': self._find_high_coupling(),
            'cycles': self._detect_cycles(),
            'metrics': self._calculate_metrics()
        }
    
    def _find_high_coupling(self, threshold: int = 5) -> List[Dict]:
        high = []
        for node in self.graph.nodes():
            fan_in = self.graph.in_degree(node)
            fan_out = self.graph.out_degree(node)
            if fan_in + fan_out > threshold:
                high.append({'file': node, 'fan_in': fan_in, 'fan_out': fan_out})
        return high
    
    def _detect_cycles(self) -> List[List[str]]:
        try:
            return list(nx.simple_cycles(self.graph))
        except:
            return []
    
    def _calculate_metrics(self) -> Dict:
        return {
            'total_files': self.graph.number_of_nodes(),
            'total_dependencies': self.graph.number_of_edges(),
            'avg_coupling': self.graph.number_of_edges() / max(self.graph.number_of_nodes(), 1)
        }
