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
            'event_driven': self._detect_event_driven(),
            'pipe_filter': self._detect_pipe_filter(),
            'client_server': self._detect_client_server(),
            'microkernel': self._detect_microkernel(),
            'microservices': self._detect_microservices()
        }
    
    def _get_filename(self, node: str) -> str:
        """Extract filename from full path"""
        return Path(node).stem.lower() if node else ''
    
    def _get_directory(self, node: str) -> str:
        """Extract parent directory name from full path"""
        return Path(node).parent.name.lower() if node else ''
    
    def _get_node_symbols(self, node: str) -> Dict:
        """Extract class names, function names, and imports from graph node data.
        
        The dependency_mapper stores parsed file data as node attributes,
        so we can access classes, functions, and imports for smarter detection.
        """
        data = self.graph.nodes.get(node, {})
        classes = [c['name'].lower() if isinstance(c, dict) else str(c).lower()
                   for c in data.get('classes', [])]
        functions = [f['name'].lower() if isinstance(f, dict) else str(f).lower()
                     for f in data.get('functions', [])]
        imports = [i.lower() if isinstance(i, str) else str(i).lower()
                   for i in data.get('imports', [])]
        return {'classes': classes, 'functions': functions, 'imports': imports}
    
    # --- Framework import indicators ---
    _PRESENTATION_IMPORTS = {
        'flask', 'fastapi', 'django.http', 'django.views', 'django.urls',
        'express', 'router', 'rest_framework', 'starlette', 'tornado.web',
        'streamlit', 'gradio', 'dash', 'tkinter', 'pyqt5', 'kivy',
    }
    _DATA_IMPORTS = {
        'sqlalchemy', 'pymongo', 'psycopg2', 'mysql', 'sqlite3',
        'django.db', 'mongoengine', 'peewee', 'redis', 'elasticsearch',
        'pandas', 'csv', 'openpyxl', 'firebase_admin',
    }
    _BUSINESS_IMPORTS = {
        'sklearn', 'tensorflow', 'torch', 'keras', 'numpy', 'scipy',
        'transformers', 'openai', 'langchain', 'groq',
    }
    
    def _classify_node(self, node: str) -> str:
        """Classify a node into presentation/business/data using multiple signals:
        filenames, directories, class/function names, and framework imports.
        """
        filename = self._get_filename(node)
        dirname = self._get_directory(node)
        symbols = self._get_node_symbols(node)
        all_classes = ' '.join(symbols['classes'])
        all_functions = ' '.join(symbols['functions'])
        all_imports = ' '.join(symbols['imports'])
        
        # --- Presentation layer signals ---
        pres_file_kw = ['controller', 'route', 'view', 'handler', 'endpoint', 'api',
                        'rest', 'app', 'server', 'web', 'ui', 'frontend', 'page']
        pres_dir_kw  = ['controller', 'api', 'route', 'presentation', 'ui', 'views',
                        'handlers', 'templates', 'static', 'frontend', 'pages']
        pres_sym_kw  = ['route', 'endpoint', 'handler', 'view', 'controller',
                        'render', 'response', 'request', 'blueprint']
        
        if any(x in filename for x in pres_file_kw) or \
           any(x in dirname for x in pres_dir_kw) or \
           any(x in all_classes for x in pres_sym_kw) or \
           any(x in all_functions for x in pres_sym_kw) or \
           any(imp in all_imports for imp in self._PRESENTATION_IMPORTS):
            return 'presentation'
        
        # --- Data layer signals ---
        data_file_kw = ['repository', 'dao', 'model', 'entity', 'db', 'database',
                        'schema', 'migration', 'seed', 'store', 'persist']
        data_dir_kw  = ['repository', 'dao', 'data', 'persistence', 'model', 'models',
                        'db', 'database', 'migrations', 'schemas']
        data_sym_kw  = ['model', 'schema', 'entity', 'repository', 'dao', 'query',
                        'table', 'column', 'database', 'cursor', 'connection', 'session']
        
        if any(x in filename for x in data_file_kw) or \
           any(x in dirname for x in data_dir_kw) or \
           any(x in all_classes for x in data_sym_kw) or \
           any(x in all_functions for x in data_sym_kw) or \
           any(imp in all_imports for imp in self._DATA_IMPORTS):
            return 'data'
        
        # --- Business / Logic layer signals ---
        biz_file_kw = ['service', 'business', 'logic', 'usecase', 'manager',
                       'processor', 'engine', 'core', 'predict', 'train',
                       'pipeline', 'analyze', 'chatbot', 'agent']
        biz_dir_kw  = ['service', 'business', 'domain', 'core', 'logic',
                       'services', 'engine', 'ml', 'ai', 'pipeline', 'lib']
        biz_sym_kw  = ['service', 'processor', 'engine', 'manager', 'pipeline',
                       'predict', 'train', 'analyze', 'compute', 'transform',
                       'evaluate', 'classify', 'detect', 'extract']
        
        if any(x in filename for x in biz_file_kw) or \
           any(x in dirname for x in biz_dir_kw) or \
           any(x in all_classes for x in biz_sym_kw) or \
           any(x in all_functions for x in biz_sym_kw) or \
           any(imp in all_imports for imp in self._BUSINESS_IMPORTS):
            return 'business'
        
        return 'unknown'
    
    def _detect_layered(self) -> Dict:
        presentation = set()
        business = set()
        data = set()
        
        for node in self.graph.nodes():
            layer = self._classify_node(node)
            if layer == 'presentation':
                presentation.add(node)
            elif layer == 'business':
                business.add(node)
            elif layer == 'data':
                data.add(node)
        
        layers_found = []
        if len(presentation) >= 1: layers_found.append('presentation')
        if len(business) >= 1: layers_found.append('business')
        if len(data) >= 1: layers_found.append('data')
        
        # Validate layering: check for inter-layer dependencies
        valid_layering = False
        if len(layers_found) >= 2:
            pres_to_biz = any(self.graph.has_edge(p, b) for p in presentation for b in business)
            biz_to_data = any(self.graph.has_edge(b, d) for b in business for d in data)
            pres_to_data = any(self.graph.has_edge(p, d) for p in presentation for d in data)
            valid_layering = pres_to_biz or biz_to_data or pres_to_data
        
        confidence = 0.0
        if len(layers_found) >= 3 and valid_layering:
            confidence = 0.85
        elif len(layers_found) >= 3:
            confidence = 0.65
        elif len(layers_found) >= 2 and valid_layering:
            confidence = 0.6
        elif len(layers_found) >= 2:
            confidence = 0.5
        
        return {
            'detected': len(layers_found) >= 2,
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
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            # Controller: routes, endpoints, API handlers
            if any(x in filename for x in ['controller', 'route', 'endpoint', 'api']) or \
               any(x in dirname for x in ['controller', 'api', 'routes']) or \
               any(x in all_functions for x in ['route', 'endpoint', 'handler']) or \
               any(imp in all_imports for imp in self._PRESENTATION_IMPORTS):
                controllers.add(node)
            # Model: data models, schemas, DB interaction
            elif any(x in filename for x in ['model', 'entity', 'schema', 'dto', 'db']) or \
                 any(x in dirname for x in ['model', 'models', 'schemas']) or \
                 any(x in all_classes for x in ['model', 'schema', 'entity', 'table']) or \
                 any(imp in all_imports for imp in self._DATA_IMPORTS):
                models.add(node)
            # View: templates, HTML pages, UI rendering
            elif any(x in filename for x in ['view', 'template', 'page', 'component', 'form']) or \
                 any(x in dirname for x in ['view', 'template', 'page', 'templates',
                                            'components', 'static']) or \
                 any(x in all_functions for x in ['render', 'display', 'show', 'template']):
                views.add(node)
        
        # Check if controllers actually use models
        controller_model_links = sum(1 for c in controllers for m in models
                                     if self.graph.has_edge(c, m))
        
        has_mvc = len(controllers) >= 1 and len(models) >= 1
        confidence = 0.0
        
        if has_mvc and len(views) >= 2 and controller_model_links > 0:
            confidence = 0.9
        elif has_mvc and controller_model_links > 0:
            confidence = 0.75
        elif has_mvc and len(views) >= 1:
            confidence = 0.65
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
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            
            if any(x in filename for x in ['port', 'interface', 'iface', 'abstract']) or \
               'port' in dirname or \
               any(x in all_classes for x in ['port', 'interface', 'abstract', 'base']):
                ports.add(node)
            elif any(x in filename for x in ['adapter', 'impl', 'implementation', 'connector']) or \
                 any(x in dirname for x in ['adapter', 'adapters', 'infrastructure']) or \
                 any(x in all_classes for x in ['adapter', 'connector', 'gateway']):
                adapters.add(node)
            elif any(x in dirname for x in ['domain', 'core', 'business', 'entities']):
                domain.add(node)
        
        # Check if domain has minimal external dependencies
        domain_external_deps = sum(1 for d in domain 
                                   for succ in self.graph.successors(d) 
                                   if succ not in domain and succ not in ports)
        
        has_hexagonal = len(ports) >= 1 and len(adapters) >= 1 and len(domain) >= 1
        domain_isolated = domain_external_deps < len(domain) * 0.3
        
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
        
        _EVENT_IMPORTS = {
            'celery', 'kombu', 'kafka', 'rabbitmq', 'pika',
            'socketio', 'signal', 'eventlet', 'asyncio',
        }
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            if any(x in filename for x in ['event', 'message', 'notification', 'signal']) or \
               any(x in all_classes for x in ['event', 'message', 'signal', 'notification']):
                events.add(node)
            elif any(x in filename for x in ['publisher', 'emitter', 'producer', 'sender', 'dispatch']) or \
                 any(x in all_functions for x in ['publish', 'emit', 'send', 'dispatch', 'broadcast', 'notify']):
                publishers.add(node)
            elif any(x in filename for x in ['subscriber', 'listener', 'consumer', 'handler',
                                             'receiver', 'callback']) or \
                 any(x in all_functions for x in ['subscribe', 'listen', 'consume',
                                                  'on_event', 'on_message', 'callback']):
                subscribers.add(node)
            elif any(imp in all_imports for imp in _EVENT_IMPORTS):
                events.add(node)
        
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

    def _detect_pipe_filter(self) -> Dict:
        """Detect Pipe-Filter / Pipeline architecture.
        
        Signals: directories named pipeline/pipes/filters/stages,
        files named *_filter/*_pipe/*_stage/*_transform,
        classes/functions with filter/pipe/stage/transform semantics.
        """
        pipes = set()
        filters = set()
        
        _PIPELINE_IMPORTS = {
            'luigi', 'airflow', 'prefect', 'dagster', 'beam',
            'sklearn.pipeline', 'pipe', 'pypipes',
        }
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            # Pipe / Stage / Pipeline nodes
            if any(x in filename for x in ['pipe', 'pipeline', 'stage', 'step',
                                            'workflow', 'chain', 'stream']) or \
               any(x in dirname for x in ['pipeline', 'pipes', 'stages', 'steps',
                                           'workflows', 'streams']) or \
               any(x in all_classes for x in ['pipeline', 'pipe', 'stage', 'step',
                                               'chain', 'stream', 'workflow']) or \
               any(x in all_functions for x in ['pipe', 'chain', 'stream',
                                                 'next_stage', 'run_pipeline']) or \
               any(imp in all_imports for imp in _PIPELINE_IMPORTS):
                pipes.add(node)
            # Filter / Transform / Processor nodes
            elif any(x in filename for x in ['filter', 'transform', 'mapper',
                                              'reducer', 'processor', 'converter']) or \
                 any(x in dirname for x in ['filter', 'filters', 'transforms',
                                             'processors', 'converters']) or \
                 any(x in all_classes for x in ['filter', 'transform', 'mapper',
                                                 'reducer', 'converter', 'processor']) or \
                 any(x in all_functions for x in ['filter', 'transform', 'map',
                                                   'reduce', 'convert', 'process']):
                filters.add(node)
        
        # Check for chaining: pipes -> filters or filters -> pipes
        chain_links = sum(1 for p in pipes for f in filters
                         if self.graph.has_edge(p, f) or self.graph.has_edge(f, p))
        
        has_pattern = len(pipes) >= 1 and len(filters) >= 1
        
        confidence = 0.0
        if has_pattern and chain_links > 0 and len(filters) >= 2:
            confidence = 0.8
        elif has_pattern and chain_links > 0:
            confidence = 0.65
        elif has_pattern:
            confidence = 0.5
        
        return {
            'detected': has_pattern,
            'pipes': len(pipes),
            'filters': len(filters),
            'chain_links': chain_links,
            'confidence': confidence
        }
    
    def _detect_client_server(self) -> Dict:
        """Detect Client-Server pattern.
        
        Signals: server-side framework imports (express/flask/fastapi) +
        separate client modules making HTTP calls (fetch/axios/requests).
        """
        servers = set()
        clients = set()
        
        _SERVER_IMPORTS = {
            'flask', 'fastapi', 'django', 'express', 'starlette',
            'tornado', 'http.server', 'uvicorn', 'gunicorn',
            'socket', 'socketserver', 'aiohttp.web',
        }
        _CLIENT_IMPORTS = {
            'requests', 'axios', 'fetch', 'httpx', 'urllib',
            'aiohttp', 'http.client', 'urllib3', 'grpc',
        }
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            is_server = (
                any(x in filename for x in ['server', 'app', 'api', 'endpoint',
                                             'route', 'handler', 'backend']) or
                any(x in dirname for x in ['server', 'backend', 'api', 'routes',
                                            'handlers', 'endpoints']) or
                any(x in all_classes for x in ['server', 'handler', 'endpoint']) or
                any(x in all_functions for x in ['serve', 'listen', 'bind',
                                                  'route', 'handler']) or
                any(imp in all_imports for imp in _SERVER_IMPORTS)
            )
            
            is_client = (
                any(x in filename for x in ['client', 'consumer', 'caller',
                                             'fetcher', 'sdk', 'frontend']) or
                any(x in dirname for x in ['client', 'clients', 'frontend',
                                            'sdk', 'consumer']) or
                any(x in all_classes for x in ['client', 'consumer', 'caller',
                                                'sdk', 'fetcher']) or
                any(x in all_functions for x in ['fetch', 'request', 'call_api',
                                                  'get_data', 'post_data']) or
                any(imp in all_imports for imp in _CLIENT_IMPORTS)
            )
            
            if is_server:
                servers.add(node)
            elif is_client:
                clients.add(node)
        
        has_pattern = len(servers) >= 1 and len(clients) >= 1
        
        # Check for client->server communication edges
        comm_links = sum(1 for c in clients for s in servers
                        if self.graph.has_edge(c, s))
        
        confidence = 0.0
        if has_pattern and comm_links > 0 and len(servers) >= 2:
            confidence = 0.8
        elif has_pattern and comm_links > 0:
            confidence = 0.7
        elif has_pattern:
            confidence = 0.5
        
        return {
            'detected': has_pattern,
            'servers': len(servers),
            'clients': len(clients),
            'communication_links': comm_links,
            'confidence': confidence
        }
    
    def _detect_microkernel(self) -> Dict:
        """Detect Microkernel (Plug-in) architecture.
        
        Signals: core/kernel modules + plugin/extension directories,
        plugin registry patterns, dynamic loading.
        """
        core_modules = set()
        plugins = set()
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            # Core / Kernel modules
            if any(x in filename for x in ['kernel', 'core', 'registry',
                                            'loader', 'bootstrap', 'dispatcher']) or \
               any(x in dirname for x in ['kernel', 'core', 'internal']) or \
               any(x in all_classes for x in ['kernel', 'registry', 'dispatcher',
                                               'loader', 'core', 'bootstrap']) or \
               any(x in all_functions for x in ['register', 'load_plugin',
                                                 'register_plugin', 'dispatch',
                                                 'bootstrap', 'initialize']):
                core_modules.add(node)
            # Plugin / Extension modules
            elif any(x in filename for x in ['plugin', 'extension', 'addon',
                                              'module', 'hook', 'middleware']) or \
                 any(x in dirname for x in ['plugin', 'plugins', 'extensions',
                                             'addons', 'modules', 'hooks',
                                             'middleware', 'contrib']) or \
                 any(x in all_classes for x in ['plugin', 'extension', 'addon',
                                                 'hook', 'middleware']) or \
                 any(x in all_functions for x in ['on_load', 'on_init', 'activate',
                                                   'deactivate', 'hook', 'extend']):
                plugins.add(node)
        
        has_pattern = len(core_modules) >= 1 and len(plugins) >= 2
        
        # Check for core -> plugin edges (core loads plugins)
        core_plugin_links = sum(1 for c in core_modules for p in plugins
                               if self.graph.has_edge(c, p) or self.graph.has_edge(p, c))
        
        confidence = 0.0
        if has_pattern and core_plugin_links > 0 and len(plugins) >= 3:
            confidence = 0.8
        elif has_pattern and core_plugin_links > 0:
            confidence = 0.65
        elif has_pattern:
            confidence = 0.5
        
        return {
            'detected': has_pattern,
            'core_modules': len(core_modules),
            'plugins': len(plugins),
            'core_plugin_links': core_plugin_links,
            'confidence': confidence
        }
    
    def _detect_microservices(self) -> Dict:
        """Detect Microservices architecture.
        
        Signals: multiple independent service directories, API gateways,
        service discovery, inter-service communication patterns,
        separate config/Dockerfiles per service.
        """
        services = set()
        gateways = set()
        
        _MICROSERVICE_IMPORTS = {
            'consul', 'eureka', 'zookeeper', 'etcd',
            'grpc', 'protobuf', 'thrift',
            'docker', 'kubernetes',
        }
        
        for node in self.graph.nodes():
            filename = self._get_filename(node)
            dirname = self._get_directory(node)
            symbols = self._get_node_symbols(node)
            all_classes = ' '.join(symbols['classes'])
            all_functions = ' '.join(symbols['functions'])
            all_imports = ' '.join(symbols['imports'])
            
            # API Gateway / Proxy
            if any(x in filename for x in ['gateway', 'proxy', 'router',
                                            'load_balancer', 'ingress']) or \
               any(x in dirname for x in ['gateway', 'proxy', 'ingress']) or \
               any(x in all_classes for x in ['gateway', 'proxy', 'loadbalancer',
                                               'router', 'ingress']):
                gateways.add(node)
            # Service modules
            elif any(x in filename for x in ['service', 'svc', 'microservice']) or \
                 any(x in dirname for x in ['service', 'services', 'svc',
                                             'microservice', 'microservices']) or \
                 any(x in all_classes for x in ['service', 'microservice']) or \
                 any(imp in all_imports for imp in _MICROSERVICE_IMPORTS):
                services.add(node)
        
        # Microservices need multiple independent services
        has_pattern = len(services) >= 3
        
        # Check for inter-service communication
        inter_service_links = sum(1 for s1 in services for s2 in services
                                 if s1 != s2 and self.graph.has_edge(s1, s2))
        
        confidence = 0.0
        if has_pattern and len(gateways) >= 1 and inter_service_links > 0:
            confidence = 0.8
        elif has_pattern and (len(gateways) >= 1 or inter_service_links > 0):
            confidence = 0.65
        elif has_pattern:
            confidence = 0.5
        
        return {
            'detected': has_pattern,
            'services': len(services),
            'gateways': len(gateways),
            'inter_service_links': inter_service_links,
            'confidence': confidence
        }


class CouplingAnalyzer:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self._cycles_cache = None
    
    def analyze(self) -> Dict:
        return {
            'high_coupling': self._find_high_coupling(),
            'cycles': self._detect_cycles(),
            'metrics': self._calculate_metrics()
        }
    
    def compute_structural_risk(self, file_path: str) -> Dict:
        """Compute structural risk score for a single file.
        
        Score formula:
        - fan_in * 8 (many dependents = risky to change)
        - fan_out * 5 (many dependencies = fragile)
        - +30 if participates in circular dependency
        - +10 bonus if fan_in > 5
        - +10 bonus if fan_out > 5
        Capped at 100.
        """
        if file_path not in self.graph:
            return {'score': 0, 'level': 'unknown', 'fan_in': 0, 'fan_out': 0, 'in_cycle': False, 'breakdown': {}}
        
        fan_in = self.graph.in_degree(file_path)
        fan_out = self.graph.out_degree(file_path)
        
        # Check if file is in any cycle
        cycles = self._get_cycles_cached()
        in_cycle = any(file_path in cycle for cycle in cycles)
        
        # Calculate score
        score = fan_in * 8 + fan_out * 5
        if in_cycle:
            score += 30
        if fan_in > 5:
            score += 10
        if fan_out > 5:
            score += 10
        score = min(score, 100)
        
        # Determine level
        if score >= 80:
            level = 'critical'
        elif score >= 60:
            level = 'high'
        elif score >= 30:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'score': score,
            'level': level,
            'fan_in': fan_in,
            'fan_out': fan_out,
            'in_cycle': in_cycle,
            'breakdown': {
                'fan_in_pts': fan_in * 8,
                'fan_out_pts': fan_out * 5,
                'cycle_pts': 30 if in_cycle else 0,
                'high_fan_in_bonus': 10 if fan_in > 5 else 0,
                'high_fan_out_bonus': 10 if fan_out > 5 else 0
            }
        }
    
    def compute_risk_for_all(self, top_n: int = None) -> List[Dict]:
        """Compute structural risk for all files, sorted by score descending."""
        risks = []
        for node in self.graph.nodes():
            risk = self.compute_structural_risk(node)
            risk['file'] = node
            risks.append(risk)
        risks.sort(key=lambda x: x['score'], reverse=True)
        if top_n:
            risks = risks[:top_n]
        return risks
    
    def _get_cycles_cached(self) -> List:
        if self._cycles_cache is None:
            self._cycles_cache = self._detect_cycles()
        return self._cycles_cache
    
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
