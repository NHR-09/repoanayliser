from pathlib import Path
from typing import Dict, List
import logging
from .parser.repo_loader import RepositoryLoader
from .parser.static_parser import StaticParser
from .graph.graph_db import GraphDB
from .graph.dependency_mapper import DependencyMapper
from .graph.analyzers import PatternDetector, CouplingAnalyzer
from .retrieval.vector_store import VectorStore
from .retrieval.retrieval_engine import RetrievalEngine
from .reasoning.llm_reasoner import LLMReasoner
from .config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnalysisEngine:
    def __init__(self):
        self.repo_loader = RepositoryLoader()
        self.parser = StaticParser()
        self.graph_db = GraphDB(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password
        )
        self.dependency_mapper = DependencyMapper()
        self.vector_store = VectorStore(settings.chroma_path)
        self.retrieval_engine = RetrievalEngine(self.vector_store, self.graph_db)
        self.llm = LLMReasoner()
        self.pattern_detector = None
        self.coupling_analyzer = None
        self.repo_path = None  # Store repo path for path resolution
    
    def analyze_repository(self, repo_url: str) -> Dict:
        logger.info(f"\n{'='*60}")
        logger.info("🚀 Starting repository analysis")
        logger.info(f"{'='*60}")
        
        logger.info("🧹 Clearing previous analysis data...")
        self.vector_store.clear()
        
        repo_path = self.repo_loader.clone_repository(repo_url)
        self.repo_path = repo_path  # Store for later use
        
        files = self.repo_loader.scan_files(
            repo_path,
            ['.py', '.js', '.java']
        )
        
        logger.info(f"\n📝 Parsing {len(files)} files...")
        parsed_files = []
        for i, file_info in enumerate(files, 1):
            if i % 5 == 1 or i == len(files):
                logger.info(f"  [{i}/{len(files)}] Parsing: {file_info['relative_path']}")
            parsed = self.parser.parse_file(
                file_info['path'],
                file_info['language']
            )
            parsed_files.append(parsed)
            self._store_in_graph(parsed)
            self._store_in_vector(parsed)
        
        logger.info("\n🕸️ Building dependency graph...")
        self.dependency_mapper.build_graph(parsed_files)
        
        logger.info("🔍 Detecting architectural patterns...")
        self.pattern_detector = PatternDetector(self.dependency_mapper.graph)
        self.coupling_analyzer = CouplingAnalyzer(self.dependency_mapper.graph)
        
        patterns = self.pattern_detector.detect_patterns()
        coupling = self.coupling_analyzer.analyze()
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Analysis completed successfully!")
        logger.info(f"{'='*60}\n")
        
        return {
            'repo_path': str(repo_path),
            'total_files': len(files),
            'patterns': patterns,
            'coupling': coupling,
            'status': 'completed'
        }
    
    def get_architecture_explanation(self) -> Dict:
        """Generate comprehensive architecture explanation using LLM"""
        if not self.pattern_detector:
            return {
                'macro': 'No analysis completed yet. Please analyze a repository first.',
                'meso': '',
                'micro': '',
                'evidence': []
            }
        
        # Get patterns
        patterns = self.pattern_detector.detect_patterns()
        
        # Get all files and their dependencies from graph
        all_files = self.graph_db.get_all_files()
        
        # Get graph structure data
        graph_data = self.graph_db.get_graph_data(limit=100)
        
        # Build graph context for LLM
        graph_context = self._build_graph_context(graph_data, all_files)
        
        # Retrieve evidence from vector store
        evidence = self.retrieval_engine.retrieve_evidence(
            "system architecture patterns modules structure"
        )
        
        # Generate explanations using LLM with graph context
        macro_explanation = self.llm.explain_architecture(evidence['evidence'])
        
        # Generate meso level with graph structure
        meso_explanation = self.llm.explain_meso_level(patterns, graph_context)
        
        # Generate micro level with detailed file analysis
        micro_explanation = self.llm.explain_micro_level(all_files[:20], graph_data)
        
        return {
            'macro': macro_explanation.get('explanation', 'Architecture analysis in progress'),
            'meso': meso_explanation,
            'micro': micro_explanation,
            'evidence': evidence['evidence'][:5]
        }
    
    def _build_graph_context(self, graph_data: Dict, all_files: List[str]) -> str:
        """Build textual representation of graph structure"""
        context_parts = []
        context_parts.append(f"Total files: {len(all_files)}")
        context_parts.append(f"Total dependencies: {len(graph_data.get('edges', []))}")
        
        # Group files by directory
        directories = {}
        for file_path in all_files:
            parts = file_path.replace('\\', '/').split('/')
            if len(parts) > 1:
                dir_name = parts[-2]
                directories[dir_name] = directories.get(dir_name, 0) + 1
        
        context_parts.append("\nDirectory structure:")
        for dir_name, count in sorted(directories.items(), key=lambda x: x[1], reverse=True)[:10]:
            context_parts.append(f"  {dir_name}/: {count} files")
        
        # Analyze dependency patterns
        if graph_data.get('edges'):
            context_parts.append(f"\nDependency relationships: {len(graph_data['edges'])} connections")
        
        return '\n'.join(context_parts)
    
    def analyze_change_impact(self, file_path: str) -> Dict:
        resolved_path = self._resolve_path(file_path)
        affected = self.graph_db.get_affected_files(resolved_path)
        blast_radius = self.dependency_mapper.get_blast_radius(resolved_path)
        evidence = self.retrieval_engine.retrieve_evidence(
            f"dependencies and usage of {file_path}",
            context_file=resolved_path
        )
        result = self.llm.analyze_impact(file_path, evidence['evidence'], affected)
        result['blast_radius'] = blast_radius
        result['risk_level'] = 'high' if len(blast_radius) > 10 else 'medium' if len(blast_radius) > 5 else 'low'
        return result
    
    def analyze_function(self, function_name: str) -> Dict:
        """Analyze function usage, callers, and provide LLM explanation"""
        # Get function info from graph
        function_info = self.graph_db.get_function_info(function_name)
        if not function_info:
            return {"error": f"Function '{function_name}' not found"}
        
        # Get callers (who calls this function)
        callers = self.graph_db.get_function_callers(function_name)
        
        # Get semantic context from vector store
        search_results = self.vector_store.search(
            f"function {function_name} implementation usage",
            n_results=3
        )
        
        # Generate LLM explanation
        explanation = self.llm.explain_function(
            function_name,
            function_info,
            callers,
            search_results
        )
        
        return {
            "function_name": function_name,
            "file": function_info.get('file'),
            "line": function_info.get('line'),
            "callers": callers,
            "usage_count": len(callers),
            "explanation": explanation,
            "related_code": search_results
        }
    
    def _resolve_path(self, file_path: str) -> str:
        """Convert relative path to absolute path stored in graph"""
        if self.repo_path and not Path(file_path).is_absolute():
            # Try to find matching file in repo
            full_path = self.repo_path / file_path
            if full_path.exists():
                return str(full_path)
        return file_path
    
    def _store_in_graph(self, parsed: Dict):
        self.graph_db.create_file_node(parsed['file'], parsed['language'])
        
        for cls in parsed.get('classes', []):
            self.graph_db.create_class_node(
                parsed['file'],
                cls['name'],
                cls['line']
            )
        
        for func in parsed.get('functions', []):
            self.graph_db.create_function_node(
                parsed['file'],
                func['name'],
                func['line']
            )
        
        imports = parsed.get('imports', [])
        if imports:
            logger.info(f"   📦 Storing {len(imports)} imports for {parsed['file']}")
        for imp in imports:
            self.graph_db.create_import_relationship(parsed['file'], imp)
        
        # Store function calls
        function_calls = parsed.get('function_calls', [])
        if function_calls:
            for called_func in set(function_calls):
                self.graph_db.create_function_call(parsed['file'], called_func)
    
    def _store_in_vector(self, parsed: Dict):
        """Store code in vector database for semantic search"""
        code_text = self._extract_code_text(parsed)
        if code_text.strip():
            self.vector_store.add_code_chunk(
                chunk_id=parsed['file'],
                code=code_text,
                metadata={
                    'file_path': parsed['file'],
                    'language': parsed['language'],
                    'num_classes': len(parsed.get('classes', [])),
                    'num_functions': len(parsed.get('functions', []))
                }
            )
    
    def _extract_code_text(self, parsed: Dict) -> str:
        """Extract meaningful code text for embedding"""
        parts = []
        
        # Add file path as context
        parts.append(f"File: {parsed['file']}")
        
        # Add classes
        for cls in parsed.get('classes', []):
            parts.append(f"Class {cls['name']} at line {cls['line']}")
        
        # Add functions
        for func in parsed.get('functions', []):
            parts.append(f"Function {func['name']} at line {func['line']}")
        
        # Add imports
        if parsed.get('imports'):
            parts.append(f"Imports: {', '.join(parsed['imports'])}")
        
        return '\n'.join(parts)
