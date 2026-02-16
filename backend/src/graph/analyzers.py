from typing import Dict, List
import networkx as nx
from pathlib import Path

class PatternDetector:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def detect_patterns(self) -> Dict:
        return {
            'layered': self._detect_layered(),
            'mvc': self._detect_mvc(),
            'hexagonal': self._detect_hexagonal(),
            'event_driven': self._detect_event_driven()
        }
    
    def _get_filename(self, node: str) -> str:
        """Extract filename from full path"""
        return Path(node).stem.lower() if node else ''
    
    def _get_directory(self, node: str) -> str:
        """Extract parent directory name from full path"""
        return Path(node).parent.name.lower() if node else ''
    
    def _detect_layered(self) -> Dict:
        presentation = set()
        business = set()
        data = set()
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            
            if any(x in filename for x in ['controller', 'route', 'view', 'handler', 'endpoint', 'api', 'rest']) or \
               any(x in dirname for x in ['controller', 'api', 'route', 'presentation', 'ui', 'views', 'handlers']):
                presentation.add(node)
            elif any(x in filename for x in ['service', 'business', 'logic', 'usecase', 'manager', 'processor']) or \
                 any(x in dirname for x in ['service', 'business', 'domain', 'core', 'logic', 'services']):
                business.add(node)
            elif any(x in filename for x in ['repository', 'dao', 'model', 'entity', 'db', 'database']) or \
                 any(x in dirname for x in ['repository', 'dao', 'data', 'persistence', 'model', 'models', 'db', 'database']):
                data.add(node)
        
        layers_found = []
        if len(presentation) >= 1: layers_found.append('presentation')
        if len(business) >= 1: layers_found.append('business')
        if len(data) >= 1: layers_found.append('data')
        
        # Validate layering: presentation should depend on business, business on data
        valid_layering = False
        if len(layers_found) >= 3:
            pres_to_biz = any(self.graph.has_edge(p, b) for p in presentation for b in business)
            biz_to_data = any(self.graph.has_edge(b, d) for b in business for d in data)
            valid_layering = pres_to_biz or biz_to_data
        
        confidence = 0.0
        if len(layers_found) >= 3 and valid_layering:
            confidence = 0.85
        elif len(layers_found) >= 3:
            confidence = 0.6
        elif len(layers_found) == 2:
            confidence = 0.5
        
        return {
            'detected': len(layers_found) >= 3,
            'layers': layers_found,
            'layer_counts': {
                'presentation': len(presentation),
                'business': len(business),
                'data': len(data)
            },
            'valid_layering': valid_layering,
            'confidence': confidence
        }
    
    def _detect_mvc(self) -> Dict:
        controllers = set()
        models = set()
        views = set()
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            
            if any(x in filename for x in ['controller', 'route', 'endpoint', 'api']) or 'controller' in dirname or 'api' in dirname:
                controllers.add(node)
            elif any(x in filename for x in ['model', 'entity', 'schema', 'dto']) or 'model' in dirname or 'models' in dirname:
                models.add(node)
            elif any(x in filename for x in ['view', 'template', 'page']) or \
                 any(x in dirname for x in ['view', 'template', 'page']):
                views.add(node)
        
        # Check if controllers actually use models
        controller_model_links = sum(1 for c in controllers for m in models if self.graph.has_edge(c, m))
        
        has_mvc = len(controllers) >= 1 and len(models) >= 1
        confidence = 0.0
        
        if has_mvc and len(views) >= 2 and controller_model_links > 0:
            confidence = 0.9
        elif has_mvc and controller_model_links > 0:
            confidence = 0.75
        elif has_mvc:
            confidence = 0.5
        
        return {
            'detected': has_mvc,
            'controllers': len(controllers),
            'models': len(models),
            'views': len(views),
            'controller_model_links': controller_model_links,
            'confidence': confidence
        }
    
    def _detect_hexagonal(self) -> Dict:
        ports = set()
        adapters = set()
        domain = set()
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            
            if any(x in filename for x in ['port', 'interface', 'iface']) or 'port' in dirname:
                ports.add(node)
            elif any(x in filename for x in ['adapter', 'impl', 'implementation']) or 'adapter' in dirname:
                adapters.add(node)
            elif any(x in dirname for x in ['domain', 'core', 'business']):
                domain.add(node)
        
        # Check if domain has minimal external dependencies
        domain_external_deps = sum(1 for d in domain 
                                   for succ in self.graph.successors(d) 
                                   if succ not in domain and succ not in ports)
        
        has_hexagonal = len(ports) >= 1 and len(adapters) >= 1 and len(domain) >= 1
        domain_isolated = domain_external_deps < len(domain) * 0.3  # Domain should be mostly isolated
        
        confidence = 0.0
        if has_hexagonal and domain_isolated:
            confidence = 0.8
        elif has_hexagonal:
            confidence = 0.5
        
        return {
            'detected': has_hexagonal,
            'ports': len(ports),
            'adapters': len(adapters),
            'domain': len(domain),
            'domain_isolated': domain_isolated,
            'confidence': confidence
        }
    
    def _detect_event_driven(self) -> Dict:
        publishers = set()
        subscribers = set()
        events = set()
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            
            if any(x in filename for x in ['event', 'message', 'notification']):
                events.add(node)
            elif any(x in filename for x in ['publisher', 'emitter', 'producer']):
                publishers.add(node)
            elif any(x in filename for x in ['subscriber', 'listener', 'consumer', 'handler']):
                subscribers.add(node)
        
        has_event_driven = len(events) >= 1 and (len(publishers) >= 1 or len(subscribers) >= 1)
        
        confidence = 0.0
        if has_event_driven and len(publishers) >= 1 and len(subscribers) >= 2:
            confidence = 0.75
        elif has_event_driven:
            confidence = 0.5
        
        return {
            'detected': has_event_driven,
            'events': len(events),
            'publishers': len(publishers),
            'subscribers': len(subscribers),
            'confidence': confidence
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
