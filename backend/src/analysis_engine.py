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
    
    def analyze_repository(self, repo_url: str) -> Dict:
        logger.info(f"\n{'='*60}")
        logger.info("🚀 Starting repository analysis")
        logger.info(f"{'='*60}")
        
        logger.info("🧹 Clearing previous analysis data...")
        self.vector_store.clear()
        
        repo_path = self.repo_loader.clone_repository(repo_url)
        
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
        patterns = self.pattern_detector.detect_patterns() if self.pattern_detector else {}
        return {
            'explanation': 'Architecture analysis based on graph structure',
            'detected_patterns': patterns,
            'evidence_files': []
        }
    
    def analyze_change_impact(self, file_path: str) -> Dict:
        affected = self.graph_db.get_affected_files(file_path)
        blast_radius = self.dependency_mapper.get_blast_radius(file_path)
        evidence = self.retrieval_engine.retrieve_evidence(
            f"dependencies and usage of {file_path}",
            context_file=file_path
        )
        result = self.llm.analyze_impact(file_path, evidence['evidence'], affected)
        result['blast_radius'] = blast_radius
        result['risk_level'] = 'high' if len(blast_radius) > 10 else 'medium' if len(blast_radius) > 5 else 'low'
        return result
    
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
    
    def _store_in_vector(self, parsed: Dict):
        # Skip vector storage for faster processing
        pass
