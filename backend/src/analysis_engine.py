from pathlib import Path
from typing import Dict, List
import logging
import hashlib
import subprocess
from threading import Lock
from collections import OrderedDict
from .parser.repo_loader import RepositoryLoader
from .parser.static_parser import StaticParser
from .graph.graph_db import GraphDB
from .graph.dependency_mapper import DependencyMapper
from .graph.analyzers import PatternDetector, CouplingAnalyzer
from .graph.version_tracker import VersionTracker
from .graph.blast_radius import BlastRadiusAnalyzer
from .retrieval.vector_store import VectorStore
from .retrieval.retrieval_engine import RetrievalEngine
from .reasoning.llm_reasoner import LLMReasoner
from .config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_CACHE_SIZE = 100

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
        self.version_tracker = VersionTracker(self.graph_db)
        self.pattern_detector = None
        self.coupling_analyzer = None
        self.blast_radius_analyzer = None
        self.repo_path = None
        self.current_repo_id = None
        self.current_snapshot_id = None
        self.analysis_cache = {}  # Cache for loaded analyses
        self.memory_cache = OrderedDict()  # LRU cache for LLM results
        self.cache_lock = Lock()  # Thread-safe cache access
    
    def analyze_repository(self, repo_url: str) -> Dict:
        logger.info(f"\n{'='*60}")
        logger.info("🚀 Starting repository analysis")
        logger.info(f"{'='*60}")
        
        repo_path = self.repo_loader.clone_repository(repo_url)
        self.repo_path = repo_path
        
        # Check if repo has changes
        repo_id = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        commit_info = self.version_tracker.get_current_commit(str(repo_path))
        
        # Check for uncommitted changes
        if commit_info and self._has_uncommitted_changes(str(repo_path)):
            logger.info("⚠️ Uncommitted changes detected - forcing fresh analysis")
            commit_info = None
        
        # Check for existing analysis with same commit (thread-safe)
        if commit_info:
            with self.cache_lock:
                cached = self._get_cached_snapshot(repo_id, commit_info['commit_hash'])
            if cached and cached.get('total_files', 0) > 0 and cached.get('patterns') and cached.get('arch_macro'):
                logger.info("✅ No changes detected - using cached analysis")
                logger.info(f"📦 Repository ID: {repo_id}")
                logger.info(f"📸 Cached Snapshot ID: {cached['snapshot_id']}")
                logger.info(f"💾 Commit: {commit_info['commit_hash'][:8]}")
                
                self.current_repo_id = repo_id
                self.current_snapshot_id = cached['snapshot_id']
                self.repo_path = repo_path
                
                # Rebuild analyzers from cached data
                self._rebuild_from_cache(repo_id)
                
                # Warm memory cache with architecture data (version-scoped key)
                cache_key = f"arch_{repo_id}_{commit_info['commit_hash']}"
                with self.cache_lock:
                    self.memory_cache[cache_key] = cached.get('architecture', {})
                    self._enforce_cache_limit()
                
                # Link files to snapshot if not already linked
                with self.graph_db.driver.session() as session:
                    session.run("""
                        MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                        MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                        MERGE (s)-[:ANALYZED_FILE]->(f)
                        """,
                        repo_id=repo_id,
                        snapshot_id=cached['snapshot_id']
                    )
                
                return {
                    'repo_path': str(repo_path),
                    'repo_id': repo_id,
                    'total_files': cached['total_files'],
                    'patterns': cached['patterns'],
                    'coupling': cached['coupling'],
                    'architecture': cached.get('architecture', {}),
                    'status': 'completed',
                    'cached': True
                }
            elif cached:
                logger.info("⚠️ Incomplete cached snapshot - re-analyzing with LLM")
        
        # Full analysis with LLM
        return self._full_analysis(repo_url, repo_path, repo_id)
    def _is_snapshot_complete(self, snapshot_id: str) -> bool:
        """Check if a snapshot has all required data (patterns, coupling, files)."""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (s:Snapshot {snapshot_id: $sid})
                WHERE s.patterns IS NOT NULL AND s.coupling IS NOT NULL AND s.total_files > 0
                OPTIONAL MATCH (s)-[af:ANALYZED_FILE]->()
                WITH s, COUNT(af) as file_links
                RETURN s.snapshot_id as sid, file_links, s.snapshot_files as sf
                """, sid=snapshot_id)
            record = result.single()
            if not record:
                return False
            # Complete if has live file links OR preserved snapshot_files
            if record['file_links'] > 0:
                return True
            if record['sf'] is not None:
                return True
            return False
    
    def _full_analysis(self, repo_url: str, repo_path: Path, repo_id: str) -> Dict:
        """Perform full analysis with LLM and caching"""
        # Check if snapshot already exists for current commit (prevent duplicates)
        commit_info = self.version_tracker.get_current_commit(str(repo_path))
        if commit_info:
            with self.cache_lock:
                existing = self._get_cached_snapshot(repo_id, commit_info['commit_hash'])
            if existing and existing.get('snapshot_id'):
                # Check if the snapshot is actually complete
                if self._is_snapshot_complete(existing['snapshot_id']):
                    logger.info(f"♻️ Complete snapshot found: {existing['snapshot_id'][:8]} — skipping re-analysis")
                    self.current_repo_id = repo_id
                    self.current_snapshot_id = existing['snapshot_id']
                    # Rebuild analyzers from cache so they're available for blast radius etc.
                    self._rebuild_from_cache(repo_id)
                    return {
                        'repo_path': str(repo_path),
                        'repo_id': repo_id,
                        'total_files': existing.get('total_files', 0),
                        'patterns': existing.get('patterns', {}),
                        'coupling': existing.get('coupling', {}),
                        'architecture': existing.get('architecture', {}),
                        'status': 'cached'
                    }
                else:
                    logger.info(f"⚠️ Incomplete snapshot {existing['snapshot_id'][:8]} — re-analyzing")
                    self.current_repo_id = repo_id
                    self.current_snapshot_id = existing['snapshot_id']
                    repo_exists = True
            else:
                # Create new snapshot only if none exists
                self.current_repo_id, repo_exists, self.current_snapshot_id = self.version_tracker.create_repository(
                    repo_url, str(repo_path)
                )
                logger.info(f"📦 Repository ID: {self.current_repo_id}")
                logger.info(f"📸 New Snapshot ID: {self.current_snapshot_id}")
        else:
            self.current_repo_id, repo_exists, self.current_snapshot_id = self.version_tracker.create_repository(
                repo_url, str(repo_path)
            )
            logger.info(f"📦 Repository ID: {self.current_repo_id}")
            logger.info(f"📸 New Snapshot ID: {self.current_snapshot_id}")
        if not repo_exists:
            logger.info("📜 Importing git commit history (first analysis)...")
            git_result = self.version_tracker.import_git_history(
                self.current_repo_id, str(repo_path), max_commits=100
            )
            if git_result['status'] == 'success':
                logger.info(f"   ✓ Processed {git_result['commits_processed']} commits")
                logger.info(f"   ✓ Created {git_result['versions_created']} versions")
            else:
                logger.warning(f"   ⚠ Git history not available: {git_result.get('message', 'Unknown')}")
        else:
            logger.info("🔄 Re-analyzing existing repository (tracking new changes)...")
        
        # Preserve file data on snapshot edges BEFORE clearing File nodes
        logger.info("📋 Preserving snapshot file metadata...")
        self._preserve_snapshot_file_data(self.current_repo_id)
        
        # Only clear graph/vector for THIS repo, not version history
        logger.info("🧹 Clearing analysis data (preserving versions)...")
        self._clear_repo_analysis(self.current_repo_id)
        self.dependency_mapper = DependencyMapper()
        self.pattern_detector = None
        self.coupling_analyzer = None
        
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
            
            # Track version with SHA-256 (only creates new version if commit changed)
            version_result = self.version_tracker.track_file_version(
                self.current_repo_id,
                file_info['path'],
                str(repo_path)
            )
            parsed['version_status'] = version_result['status']
            parsed['file_hash'] = version_result.get('hash', '')
            
            if version_result['status'] == 'new_version':
                logger.info(f"   📌 New version: {file_info['relative_path']}")
            elif version_result['status'] == 'unchanged':
                logger.debug(f"   ✓ Unchanged: {file_info['relative_path']} (commit {version_result.get('commit', 'N/A')})")
            
            self._store_in_graph(parsed)
            self._store_in_vector(parsed)
            
            # Link file to snapshot
            with self.graph_db.driver.session() as session:
                session.run("""
                    MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                    MATCH (f:File {file_path: $file_path})
                    MERGE (s)-[:ANALYZED_FILE]->(f)
                    """,
                    snapshot_id=self.current_snapshot_id,
                    file_path=file_info['path']
                )
        
        logger.info("\n🕸️ Building dependency graph...")
        self.dependency_mapper.build_graph(parsed_files)
        
        # Store dependencies in Neo4j
        logger.info("💾 Storing dependencies in Neo4j...")
        self._store_dependencies_in_neo4j()
        
        # Create transitive function call relationships
        logger.info("🔗 Creating transitive function relationships...")
        transitive_count = self.graph_db.create_transitive_function_calls(self.current_repo_id)
        logger.info(f"   ✅ Created {transitive_count} transitive relationships")
        
        logger.info("🔍 Detecting architectural patterns...")
        self.pattern_detector = PatternDetector(self.dependency_mapper.graph)
        self.coupling_analyzer = CouplingAnalyzer(self.dependency_mapper.graph)
        self.blast_radius_analyzer = BlastRadiusAnalyzer(self.dependency_mapper, self.graph_db)
        
        patterns = self.pattern_detector.detect_patterns()
        coupling = self.coupling_analyzer.analyze()
        
        # Store dependency snapshot for this snapshot
        commit_info = self.version_tracker.get_current_commit(str(repo_path))
        if commit_info:
            edges = [(u, v) for u, v in self.dependency_mapper.graph.edges()]
            
            # Store in snapshot instead of commit
            with self.graph_db.driver.session() as session:
                session.run("""
                    MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                    SET s.dependencies = $deps,
                        s.total_files = $total_files,
                        s.total_deps = $total_deps
                    """,
                    snapshot_id=self.current_snapshot_id,
                    deps=str(edges),
                    total_files=len(files),
                    total_deps=len(edges)
                )
            
            metrics = {
                'total_files': len(files),
                'total_deps': len(edges),
                'avg_coupling': coupling.get('metrics', {}).get('avg_coupling', 0),
                'cycle_count': len(coupling.get('cycles', []))
            }
            
            # Store metrics in snapshot
            with self.graph_db.driver.session() as session:
                session.run("""
                    MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                    SET s.avg_coupling = $avg_coupling,
                        s.cycle_count = $cycle_count
                    """,
                    snapshot_id=self.current_snapshot_id,
                    avg_coupling=metrics['avg_coupling'],
                    cycle_count=metrics['cycle_count']
                )
        
        # Generate architecture explanation with LLM and cache
        logger.info("🤖 Generating architecture explanation with LLM...")
        arch_explanation = self._generate_and_cache_architecture()
        
        # Store everything in snapshot
        self._store_architecture_cache(self.current_repo_id, self.current_snapshot_id, 
                                      patterns, coupling, arch_explanation)
        
        # Preserve file list on snapshot node for future comparisons
        self._preserve_snapshot_file_data(self.current_repo_id)
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Analysis completed successfully!")
        logger.info(f"{'='*60}\n")
        
        return {
            'repo_path': str(repo_path),
            'repo_id': self.current_repo_id,
            'total_files': len(files),
            'patterns': patterns,
            'coupling': coupling,
            'architecture': arch_explanation,
            'status': 'completed'
        }
    
    def load_repository_analysis(self, repo_id: str) -> bool:
        """Load existing analysis for a repository"""
        try:
            with self.graph_db.driver.session() as session:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})
                    RETURN r.path as path, r.current_commit as commit
                    """, repo_id=repo_id)
                record = result.single()
                if not record:
                    return False
                
                # Clear stale memory cache when switching repos
                old_repo_id = self.current_repo_id
                if old_repo_id and old_repo_id != repo_id:
                    with self.cache_lock:
                        stale_keys = [k for k in self.memory_cache 
                                     if k.startswith(f"arch_{old_repo_id}") or 
                                        k.startswith(f"impact_{old_repo_id}")]
                        for k in stale_keys:
                            del self.memory_cache[k]
                        logger.info(f"🗑️ Cleared {len(stale_keys)} stale cache entries from repo {old_repo_id[:8]}")
                
                self.current_repo_id = repo_id
                self.repo_path = Path(record['path'])
                
                # Rebuild dependency graph from stored data (with imports & dependencies)
                self._rebuild_from_cache(repo_id)
                
                logger.info(f"✅ Loaded analysis for repo {repo_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            return False
    
    def get_architecture_explanation(self, repo_id: str = None) -> Dict:
        """Get cached or generate architecture explanation"""
        # Load repo if specified
        if repo_id and repo_id != self.current_repo_id:
            if not self.load_repository_analysis(repo_id):
                return {'error': 'Repository not found'}
        
        if not self.pattern_detector:
            return {
                'overview': 'No analysis completed yet. Please analyze a repository first.',
                'modules': '',
                'key_files': '',
                'stats': {},
                'evidence': []
            }
        
        # Check memory cache first (thread-safe, version-scoped)
        commit_info = self.version_tracker.get_current_commit(str(self.repo_path)) if self.repo_path else None
        commit_hash = commit_info['commit_hash'] if commit_info else 'unknown'
        cache_key = f"arch_{self.current_repo_id}_{commit_hash}"
        with self.cache_lock:
            if cache_key in self.memory_cache:
                logger.info("💾 Using in-memory cached architecture")
                # Move to end (LRU)
                self.memory_cache.move_to_end(cache_key)
                return self.memory_cache[cache_key]
        
        # Check database cache
        if commit_info:
            with self.cache_lock:
                cached = self._get_cached_architecture(self.current_repo_id, commit_hash)
            if cached:
                logger.info("📦 Using database cached architecture")
                # Compute stats on-the-fly for cached text data
                cached['stats'] = self._compute_arch_stats()
                with self.cache_lock:
                    self.memory_cache[cache_key] = cached
                    self._enforce_cache_limit()
                return cached
        
        # Generate new explanation and cache it
        logger.info("🤖 Generating architecture explanation with LLM...")
        arch_explanation = self._generate_and_cache_architecture()
        
        # Store in database
        if self.current_snapshot_id:
            import json
            with self.graph_db.driver.session() as session:
                session.run("""
                    MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                    SET s.arch_macro = $macro,
                        s.arch_meso = $meso,
                        s.arch_micro = $micro
                    """,
                    snapshot_id=self.current_snapshot_id,
                    macro=arch_explanation.get('macro', ''),
                    meso=arch_explanation.get('meso', ''),
                    micro=arch_explanation.get('micro', '')
                )
        
        # Store in memory (thread-safe with size limit)
        with self.cache_lock:
            self.memory_cache[cache_key] = arch_explanation
            self._enforce_cache_limit()
        
        return arch_explanation
    
    def _compute_arch_stats(self) -> Dict:
        """Compute structural stats from existing analyzers (no LLM needed).
        Falls back to Snapshot node properties when File nodes are missing."""
        all_files = self.graph_db.get_all_files()
        graph_data = self.graph_db.get_graph_data(limit=100)
        coupling_data = self.coupling_analyzer.analyze() if self.coupling_analyzer else {}
        cycles = self.dependency_mapper.detect_cycles() if self.dependency_mapper else []
        patterns = self.pattern_detector.detect_patterns() if self.pattern_detector else {}
        
        total_files = len(all_files)
        total_deps = len(graph_data.get('edges', []))
        avg_coupling = coupling_data.get('metrics', {}).get('avg_coupling', 0)
        cycle_count = len(cycles)
        
        # Fallback: if no live files found, read from Snapshot node properties
        if total_files == 0 and self.current_snapshot_id:
            with self.graph_db.driver.session() as session:
                result = session.run("""
                    MATCH (s:Snapshot {snapshot_id: $sid})
                    RETURN s.total_files as tf, s.total_deps as td,
                           s.avg_coupling as ac, s.cycle_count as cc,
                           s.snapshot_files as sf
                    """, sid=self.current_snapshot_id)
                rec = result.single()
                if rec:
                    total_files = rec['tf'] or 0
                    total_deps = rec['td'] or 0
                    avg_coupling = rec['ac'] or 0
                    cycle_count = rec['cc'] or 0
                    # Build directories from snapshot_files JSON
                    if rec['sf']:
                        import json
                        try:
                            sf_list = json.loads(rec['sf'])
                            all_files = [f.get('path', '') for f in sf_list if f.get('path')]
                        except:
                            pass
        
        directories = {}
        for fp in all_files:
            if not fp:
                continue
            parts = fp.replace('\\', '/').split('/')
            if len(parts) > 1:
                directories[parts[-2]] = directories.get(parts[-2], 0) + 1
        top_dirs_list = sorted(directories.items(), key=lambda x: x[1], reverse=True)[:8]
        
        detected_patterns = []
        for name, data in patterns.items():
            if data.get('detected'):
                detected_patterns.append({
                    'name': name,
                    'confidence': round(data.get('confidence', 0), 2),
                    'layers': data.get('layers', [])
                })
        
        return {
            'total_files': total_files,
            'total_dependencies': total_deps,
            'avg_coupling': round(avg_coupling, 2),
            'cycle_count': cycle_count,
            'detected_patterns': detected_patterns,
            'top_directories': [{'name': d, 'count': c} for d, c in top_dirs_list]
        }
    
    def _generate_and_cache_architecture(self) -> Dict:
        """Generate architecture explanation using LLM"""
        if not self.pattern_detector:
            return {
                'overview': 'No analysis completed yet.',
                'modules': '',
                'key_files': '',
                'stats': {},
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
        
        # Compute structural stats (no LLM tokens needed)
        coupling_data = self.coupling_analyzer.analyze() if self.coupling_analyzer else {}
        cycles = self.dependency_mapper.detect_cycles() if self.dependency_mapper else []
        
        # Build top directories
        directories = {}
        for fp in all_files:
            if not fp:
                continue
            parts = fp.replace('\\', '/').split('/')
            if len(parts) > 1:
                directories[parts[-2]] = directories.get(parts[-2], 0) + 1
        top_dirs_list = sorted(directories.items(), key=lambda x: x[1], reverse=True)[:8]
        top_dirs_text = '\n'.join([f"  {d}/: {c} files" for d, c in top_dirs_list])
        
        # Build detected patterns list
        detected_patterns = []
        for name, data in patterns.items():
            if data.get('detected'):
                detected_patterns.append({
                    'name': name,
                    'confidence': round(data.get('confidence', 0), 2),
                    'layers': data.get('layers', [])
                })
        
        # Format patterns for LLM prompt
        patterns_text = self.llm._format_patterns(patterns)
        
        # Format evidence for LLM prompt (limit to save tokens)
        evidence_items = evidence.get('evidence', [])[:3]
        evidence_text = '\n'.join([
            f"File: {e.get('file', 'unknown')}\n{e.get('code', '')[:200]}"
            for e in evidence_items
        ])
        
        # Single LLM call instead of 3
        logger.info("🤖 Generating architecture report (single LLM call)...")
        sections = self.llm.explain_architecture_report(
            patterns_text, graph_context, top_dirs_text, evidence_text
        )
        
        stats = {
            'total_files': len(all_files),
            'total_dependencies': len(graph_data.get('edges', [])),
            'avg_coupling': round(coupling_data.get('metrics', {}).get('avg_coupling', 0), 2),
            'cycle_count': len(cycles),
            'detected_patterns': detected_patterns,
            'top_directories': [{'name': d, 'count': c} for d, c in top_dirs_list]
        }
        
        result = {
            'overview': sections.get('overview', ''),
            'modules': sections.get('modules', ''),
            'key_files': sections.get('key_files', ''),
            'stats': stats,
            'evidence': evidence_items[:5],
            # Keep backward compat for cache
            'macro': sections.get('overview', ''),
            'meso': sections.get('modules', ''),
            'micro': sections.get('key_files', '')
        }
        return result
    
    def _store_architecture_cache(self, repo_id: str, snapshot_id: str, 
                                   patterns: Dict, coupling: Dict, arch_explanation: Dict):
        """Store analysis results in snapshot atomically"""
        import json
        with self.graph_db.driver.session() as session:
            # Atomic update - all properties set in single operation
            session.run("""
                MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                SET s += {
                    patterns: $patterns,
                    coupling: $coupling,
                    arch_macro: $macro,
                    arch_meso: $meso,
                    arch_micro: $micro,
                    cached_at: datetime()
                }
                """,
                snapshot_id=snapshot_id,
                patterns=json.dumps(patterns),
                coupling=json.dumps(coupling),
                macro=arch_explanation.get('macro', ''),
                meso=arch_explanation.get('meso', ''),
                micro=arch_explanation.get('micro', '')
            )
    
    def _get_cached_snapshot(self, repo_id: str, commit_hash: str) -> Dict:
        """Check if snapshot exists for this commit with valid data"""
        import json
        with self.graph_db.driver.session() as session:
            # Check if commit changed - invalidate cache if different
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})
                OPTIONAL MATCH (s:Snapshot {repo_id: $repo_id, commit_hash: $commit_hash})
                WHERE s.patterns IS NOT NULL AND s.total_files > 0
                OPTIONAL MATCH (s)-[:ANALYZED_FILE]->(f:File)
                WITH r, s, COUNT(f) as file_count
                WHERE file_count > 0
                RETURN r.current_commit as current_commit,
                       s.snapshot_id as snapshot_id,
                       s.patterns as patterns,
                       s.coupling as coupling,
                       s.total_files as total_files,
                       s.arch_macro as macro,
                       s.arch_meso as meso,
                       s.arch_micro as micro
                """,
                repo_id=repo_id,
                commit_hash=commit_hash
            )
            record = result.single()
            
            # Invalidate cache if commit changed
            if record and record['current_commit'] != commit_hash:
                logger.info(f"🔄 Commit changed: {record['current_commit'][:8]} → {commit_hash[:8]}")
                return None
            
            if record:
                return {
                    'snapshot_id': record['snapshot_id'],
                    'patterns': json.loads(record['patterns']) if record['patterns'] else {},
                    'coupling': json.loads(record['coupling']) if record['coupling'] else {},
                    'total_files': record['total_files'] or 0,
                    'arch_macro': record['macro'],
                    'architecture': {
                        'macro': record['macro'] or '',
                        'meso': record['meso'] or '',
                        'micro': record['micro'] or ''
                    }
                }
            return None
    
    def _rebuild_from_cache(self, repo_id: str):
        """Rebuild analyzers from cached snapshot data"""
        import json as json_mod
        with self.graph_db.driver.session() as session:
            # Get files with their imports and dependencies
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(cls:Class)
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                RETURN COALESCE(f.file_path, f.path) as file,
                       f.language as language,
                       COLLECT(DISTINCT m.name) as imports,
                       COLLECT(DISTINCT COALESCE(dep.file_path, dep.path)) as dependencies,
                       COLLECT(DISTINCT cls.name) as classes,
                       COLLECT(DISTINCT fn.name) as functions
                """, repo_id=repo_id)
            
            parsed_files = []
            deps_map = {}  # file -> list of dependency file paths
            for r in result:
                file_path = r['file']
                imports = [imp for imp in r['imports'] if imp]
                deps = [d for d in r['dependencies'] if d]
                parsed_files.append({
                    'file': file_path,
                    'language': r['language'] or 'python',
                    'imports': imports,
                    'classes': [{'name': c} for c in r['classes'] if c],
                    'functions': [{'name': f} for f in r['functions'] if f]
                })
                if deps:
                    deps_map[file_path] = deps
        
        # If no live File nodes, try to rebuild from snapshot_files JSON + dependencies
        if not parsed_files and self.current_snapshot_id:
            logger.info("📂 No live File nodes — rebuilding from snapshot_files")
            with self.graph_db.driver.session() as session:
                result = session.run("""
                    MATCH (s:Snapshot {snapshot_id: $sid})
                    RETURN s.snapshot_files as sf, s.dependencies as deps
                    """, sid=self.current_snapshot_id)
                rec = result.single()
                if rec and rec['sf']:
                    try:
                        sf_list = json_mod.loads(rec['sf'])
                        for f_entry in sf_list:
                            fp = f_entry.get('path', '')
                            if fp:
                                # Guess language from extension
                                ext = fp.rsplit('.', 1)[-1] if '.' in fp else ''
                                lang = {'py': 'python', 'js': 'javascript', 'java': 'java'}.get(ext, 'python')
                                parsed_files.append({
                                    'file': fp,
                                    'language': lang,
                                    'imports': [],
                                    'classes': [],
                                    'functions': []
                                })
                    except Exception as e:
                        logger.warning(f"Could not parse snapshot_files: {e}")
                
                # Rebuild edges from stored dependency string
                if rec and rec['deps']:
                    try:
                        edges = eval(rec['deps'])  # stored as str(list of tuples)
                        for src, tgt in edges:
                            if src not in deps_map:
                                deps_map[src] = []
                            deps_map[src].append(tgt)
                    except Exception as e:
                        logger.warning(f"Could not parse stored dependencies: {e}")
        
        # Rebuild dependency graph with import data
        self.dependency_mapper = DependencyMapper()
        self.dependency_mapper.build_graph(parsed_files)
        
        # Also add pre-resolved DEPENDS_ON edges from Neo4j
        # (import name resolution may miss some when loading from cache)
        added_deps = 0
        for source, targets in deps_map.items():
            for target in targets:
                if not self.dependency_mapper.graph.has_edge(source, target):
                    self.dependency_mapper.graph.add_edge(source, target, type='depends_on')
                    added_deps += 1
        if added_deps > 0:
            logger.info(f"   🔗 Added {added_deps} DEPENDS_ON edges from cache")
        
        logger.info(f"   📊 Rebuilt graph: {self.dependency_mapper.graph.number_of_nodes()} nodes, {self.dependency_mapper.graph.number_of_edges()} edges")
        
        # Rebuild analyzers
        self.pattern_detector = PatternDetector(self.dependency_mapper.graph)
        self.coupling_analyzer = CouplingAnalyzer(self.dependency_mapper.graph)
        self.blast_radius_analyzer = BlastRadiusAnalyzer(self.dependency_mapper, self.graph_db)
    
    def _get_cached_architecture(self, repo_id: str, commit_hash: str) -> Dict:
        """Retrieve cached architecture explanation from snapshot"""
        import json
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (s:Snapshot {repo_id: $repo_id, commit_hash: $commit_hash})
                WHERE s.arch_macro IS NOT NULL AND s.arch_macro <> ''
                RETURN s.arch_macro as macro, s.arch_meso as meso, 
                       s.arch_micro as micro
                ORDER BY s.created_at DESC
                LIMIT 1
                """,
                repo_id=repo_id,
                commit_hash=commit_hash
            )
            record = result.single()
            if record:
                return {
                    'overview': record['macro'] or '',
                    'modules': record['meso'] or '',
                    'key_files': record['micro'] or '',
                    'macro': record['macro'] or '',
                    'meso': record['meso'] or '',
                    'micro': record['micro'] or '',
                    'evidence': [],
                    'stats': {},
                    'cached': True
                }
            return None
    
    def _build_graph_context(self, graph_data: Dict, all_files: List[str]) -> str:
        """Build textual representation of graph structure"""
        context_parts = []
        context_parts.append(f"Total files: {len(all_files)}")
        context_parts.append(f"Total dependencies: {len(graph_data.get('edges', []))}")
        
        # Group files by directory
        directories = {}
        for file_path in all_files:
            if not file_path:  # Skip None values
                continue
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
    
    def analyze_change_impact(self, file_path: str, change_type: str = "modify") -> Dict:
        resolved_path = self._resolve_path(file_path)
        
        # Ensure blast radius analyzer is initialized
        if not self.blast_radius_analyzer:
            if not self.current_repo_id:
                # Load first available repository
                repos = self.version_tracker.list_repositories()
                if repos:
                    self.load_repository_analysis(repos[0]['repo_id'])
            
            # If still not initialized, create it
            if not self.blast_radius_analyzer:
                self.blast_radius_analyzer = BlastRadiusAnalyzer(self.dependency_mapper, self.graph_db)
        
        # Get blast radius analysis
        result = self.blast_radius_analyzer.analyze(resolved_path, change_type, self.current_repo_id)
        
        # Check memory cache (repo-scoped to prevent cross-repo contamination)
        cache_key = f"impact_{self.current_repo_id}_{resolved_path}_{change_type}"
        if cache_key in self.memory_cache:
            cached_entry = self.memory_cache[cache_key]
            # Invalidate if blast radius data changed (stale explanation)
            cached_total = cached_entry.get('_total_affected', -1)
            current_total = result.get('total_affected', 0)
            if cached_total == current_total:
                logger.info("💾 Using cached impact explanation")
                result['explanation'] = cached_entry['explanation']
                return result
            else:
                logger.info(f"🔄 Invalidating stale impact cache (was {cached_total}, now {current_total})")
                del self.memory_cache[cache_key]
        
        # Extract blast radius data
        direct = result.get('direct_dependents', [])
        indirect = result.get('indirect_dependents', [])
        functions = result.get('functions_affected', {}).get('functions', [])
        risk_level = result.get('risk_level', 'unknown')
        risk_score = result.get('risk_score', 0)
        
        # Build LLM prompt with blast radius data
        filename = Path(file_path).name
        direct_list = '\n'.join([f"  - {Path(f).name}" for f in direct[:10] if f]) or '  None'
        indirect_list = '\n'.join([f"  - {Path(f).name}" for f in indirect[:10] if f]) or '  None'
        func_list = '\n'.join([f"  - {fn['name']} ({fn['caller_count']} callers)" for fn in functions[:10]]) or '  None'
        
        prompt = f"""Analyze the impact of {change_type.upper()}ing file: {filename}

BLAST RADIUS ANALYSIS:

Direct Dependents ({len(direct)} files):
{direct_list}

Indirect Dependents ({len(indirect)} files):
{indirect_list}

Functions Affected ({len(functions)} functions):
{func_list}

Risk Assessment: {risk_level.upper()} (Score: {risk_score}/100)

Provide a concise 2-3 sentence summary explaining:
1. What components are directly impacted
2. The cascading effects on the system
3. Key risks to consider"""
        
        try:
            explanation = self.llm._call_llm(prompt)
            self.memory_cache[cache_key] = {
                'explanation': explanation,
                '_total_affected': result.get('total_affected', 0)
            }
            result['explanation'] = explanation
        except Exception as e:
            logger.error(f"LLM explanation failed: {e}")
            result['explanation'] = f"{change_type.upper()}: Affects {result.get('total_affected', 0)} files with {risk_level} risk."
        
        return result
    
    def analyze_function(self, function_name: str) -> Dict:
        """Analyze function usage, callers, and provide LLM explanation"""
        # Check memory cache
        cache_key = f"func_{function_name}"
        if cache_key in self.memory_cache:
            logger.info("💾 Using cached function explanation")
            return self.memory_cache[cache_key]
        
        # Get function info from graph
        function_info = self.graph_db.get_function_info(function_name)
        if not function_info:
            return {"error": f"Function '{function_name}' not found"}
        
        # Read actual function code from file
        file_path = function_info.get('file')
        start_line = function_info.get('line', 1)
        function_code = self._extract_function_code(file_path, function_name, start_line)
        
        # Get callers (who calls this function)
        raw_callers = self.graph_db.get_function_callers(function_name, repo_id=self.current_repo_id)
        # Transform to expected frontend format
        callers = []
        for c in raw_callers:
            caller_path = c.get('file', c.get('caller_file', ''))
            # Use function-level caller name if available, else derive from file
            caller_name = c.get('caller_name') or (Path(caller_path).stem if caller_path else 'unknown')
            callers.append({
                'caller_name': caller_name,
                'caller_file': caller_path,
                'line': c.get('line', 0)
            })
        
        # Get semantic context from vector store
        search_results = self.vector_store.search(
            f"function {function_name} implementation usage",
            n_results=3
        )
        
        # Generate LLM explanation with actual code
        explanation = self.llm.explain_function(
            function_name,
            function_info,
            callers,
            search_results,
            function_code
        )
        
        result = {
            "function_name": function_name,
            "file": file_path,
            "line": start_line,
            "code": function_code,
            "callers": callers,
            "usage_count": len(callers),
            "explanation": explanation,
            "related_code": search_results
        }
        
        # Cache in memory
        self.memory_cache[cache_key] = result
        
        return result
    
    def _resolve_path(self, file_path: str) -> str:
        """Convert relative path to absolute path stored in graph"""
        # Strategy 1: Try filesystem resolution
        if self.repo_path and not Path(file_path).is_absolute():
            full_path = self.repo_path / file_path
            if full_path.exists():
                return str(full_path)
        
        # Strategy 2: Try Neo4j-based resolution (handles cases where repo
        # was cloned to temp dir that no longer exists)
        if hasattr(self, 'graph_db') and self.graph_db:
            try:
                resolved = self.graph_db.resolve_file_path(file_path)
                if resolved != file_path:
                    return resolved
            except:
                pass
        
        return file_path
    
    def _store_in_graph(self, parsed: Dict):
        # Compute file content hash
        import hashlib
        try:
            with open(parsed['file'], 'rb') as f:
                content_hash = hashlib.sha256(f.read()).hexdigest()
        except:
            content_hash = None
        
        self.graph_db.create_file_node(parsed['file'], parsed['language'], content_hash)
        
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
                func['line'],
                self.current_repo_id
            )
        
        imports = parsed.get('imports', [])
        if imports:
            logger.info(f"   📦 Storing {len(imports)} imports for {parsed['file']}")
        for imp in imports:
            self.graph_db.create_import_relationship(parsed['file'], imp)
        
        # Store function calls
        function_calls = parsed.get('function_calls', [])
        if function_calls:
            logger.info(f"   📞 Storing {len(set(function_calls))} unique function calls from {Path(parsed['file']).name}")
            for called_func in set(function_calls):
                self.graph_db.create_function_call(parsed['file'], called_func, self.current_repo_id)
        
        # Store function-to-function calls
        func_to_func_calls = parsed.get('function_to_function_calls', [])
        if func_to_func_calls:
            logger.info(f"   🔗 Storing {len(func_to_func_calls)} function-to-function calls")
            for call in func_to_func_calls:
                self.graph_db.create_function_to_function_call(
                    parsed['file'], 
                    call['caller'], 
                    call['callee'], 
                    self.current_repo_id
                )
    
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
    
    def _preserve_snapshot_file_data(self, repo_id: str):
        """Store file_path + content_hash as a JSON property on Snapshot nodes.
        DETACH DELETE on File nodes also removes ANALYZED_FILE edges,
        so we store the file list directly on the Snapshot node."""
        import json
        with self.graph_db.driver.session() as session:
            # Get all snapshots that don't yet have preserved file data
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(s:Snapshot)
                WHERE s.snapshot_files IS NULL
                MATCH (s)-[:ANALYZED_FILE]->(f:File)
                WITH s, collect({path: f.file_path, hash: f.content_hash}) as files
                RETURN s.snapshot_id as sid, files
                """, repo_id=repo_id)
            
            count = 0
            for record in result:
                session.run("""
                    MATCH (s:Snapshot {snapshot_id: $sid})
                    SET s.snapshot_files = $files_json
                    """, sid=record['sid'], files_json=json.dumps(record['files']))
                count += 1
            
            if count > 0:
                logger.info(f"   ✓ Preserved file data for {count} snapshot(s)")
            else:
                logger.info("   ✓ All snapshots already preserved")
    
    def _clear_repo_analysis(self, repo_id: str):
        """Clear only analysis nodes (File/Class/Function), keep Repository/Commit/Version nodes"""
        with self.graph_db.driver.session() as session:
            # Delete File nodes and their children for this repo
            session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                DETACH DELETE f, c, fn, m
                """, repo_id=repo_id)
            
            # Clean up orphaned nodes (from deleted repos)
            session.run("""
                MATCH (f:File)
                WHERE NOT (f)<-[:CONTAINS]-(:Repository)
                OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                DETACH DELETE f, c, fn
                """)
        self.vector_store.clear()
    
    def compare_snapshots(self, repo_id: str, snapshot1: str, snapshot2: str) -> Dict:
        """Compare two snapshots with cached architecture, coupling, and dependencies"""
        import json
        
        with self.graph_db.driver.session() as session:
            # Get cached data from both snapshots
            result = session.run("""
                MATCH (s1:Snapshot {snapshot_id: $snapshot1})
                MATCH (s2:Snapshot {snapshot_id: $snapshot2})
                RETURN s1.patterns as p1, s1.coupling as c1, s1.avg_coupling as ac1,
                       s1.cycle_count as cc1, s1.total_files as tf1, s1.total_deps as td1,
                       s1.arch_macro as macro1, s1.arch_meso as meso1,
                       s2.patterns as p2, s2.coupling as c2, s2.avg_coupling as ac2,
                       s2.cycle_count as cc2, s2.total_files as tf2, s2.total_deps as td2,
                       s2.arch_macro as macro2, s2.arch_meso as meso2,
                       toString(s1.created_at) as date1, toString(s2.created_at) as date2
                """, snapshot1=snapshot1, snapshot2=snapshot2)
            record = result.single()
            
            if not record:
                return {"error": "Snapshots not found"}
            
            # Parse patterns
            patterns1 = json.loads(record['p1']) if record['p1'] else {}
            patterns2 = json.loads(record['p2']) if record['p2'] else {}
            
            # Parse coupling
            coupling1 = json.loads(record['c1']) if record['c1'] else {}
            coupling2 = json.loads(record['c2']) if record['c2'] else {}
            
            # Get file changes - try live File nodes first, fall back to snapshot_files property
            files1_raw = []
            files2_raw = []
            
            # Try live File nodes for snapshot 1
            r1 = session.run("""
                MATCH (s1:Snapshot {snapshot_id: $sid})-[:ANALYZED_FILE]->(f:File)
                RETURN collect({path: f.file_path, hash: f.content_hash}) as files
                """, sid=snapshot1)
            rec1 = r1.single()
            if rec1 and rec1['files']:
                files1_raw = rec1['files']
            else:
                # Fall back to preserved snapshot_files property
                r1b = session.run("""
                    MATCH (s1:Snapshot {snapshot_id: $sid})
                    RETURN s1.snapshot_files as sf
                    """, sid=snapshot1)
                rec1b = r1b.single()
                if rec1b and rec1b['sf']:
                    files1_raw = json.loads(rec1b['sf'])
                    logger.info(f"📂 Using preserved file data for snapshot {snapshot1[:8]}")
            
            # Try live File nodes for snapshot 2
            r2 = session.run("""
                MATCH (s2:Snapshot {snapshot_id: $sid})-[:ANALYZED_FILE]->(f:File)
                RETURN collect({path: f.file_path, hash: f.content_hash}) as files
                """, sid=snapshot2)
            rec2 = r2.single()
            if rec2 and rec2['files']:
                files2_raw = rec2['files']
            else:
                # Fall back to preserved snapshot_files property
                r2b = session.run("""
                    MATCH (s2:Snapshot {snapshot_id: $sid})
                    RETURN s2.snapshot_files as sf
                    """, sid=snapshot2)
                rec2b = r2b.single()
                if rec2b and rec2b['sf']:
                    files2_raw = json.loads(rec2b['sf'])
                    logger.info(f"📂 Using preserved file data for snapshot {snapshot2[:8]}")
            
            # Normalize paths to relative (strip repo root) for accurate cross-snapshot comparison
            def _normalize_path(p):
                if not p:
                    return p
                p = p.replace('\\', '/')
                # Strip common temp/clone prefixes to get relative path
                for prefix in ['/tmp/', '/temp/', 'C:/Users/', 'c:/Users/']:
                    idx = p.find(prefix)
                    if idx >= 0:
                        # Find the repo root (usually 2-3 levels after prefix)
                        parts = p[idx:].split('/')
                        # Skip to after the repo directory name
                        for i, part in enumerate(parts):
                            if part in ('src', 'lib', 'app', 'backend', 'frontend', 'pkg'):
                                return '/'.join(parts[i:])
                # Fallback: use just the filename with parent
                parts = p.split('/')
                return '/'.join(parts[-3:]) if len(parts) >= 3 else p
            
            files1_map = {}
            for f in (files1_raw or []):
                if f.get('path'):
                    norm = _normalize_path(f['path'])
                    files1_map[norm] = f.get('hash')
            
            files2_map = {}
            for f in (files2_raw or []):
                if f.get('path'):
                    norm = _normalize_path(f['path'])
                    files2_map[norm] = f.get('hash')
            
            paths1 = set(files1_map.keys())
            paths2 = set(files2_map.keys())
            
            added_files = list(paths2 - paths1)
            removed_files = list(paths1 - paths2)
            # Only mark as modified if both hashes exist and are different
            modified_files = [p for p in (paths1 & paths2) 
                            if files1_map.get(p) is not None 
                            and files2_map.get(p) is not None 
                            and files1_map[p] != files2_map[p]]
            
            # Compare patterns
            pattern_changes = self._compare_patterns(patterns1, patterns2)
            
            # Compare coupling
            high_coupling1 = coupling1.get('high_coupling', [])
            high_coupling2 = coupling2.get('high_coupling', [])
            
            # Calculate deltas
            coupling_delta = round((record['ac2'] or 0) - (record['ac1'] or 0), 2)
            cycle_delta = (record['cc2'] or 0) - (record['cc1'] or 0)
            
            # Risk assessment
            risk_areas = []
            if len(added_files) > 10:
                risk_areas.append(f"High file growth: +{len(added_files)} files")
            if coupling_delta > 1.0:
                risk_areas.append(f"Coupling increased by {coupling_delta}")
            if cycle_delta > 0:
                risk_areas.append(f"{cycle_delta} new circular dependencies")
            if len(high_coupling2) > len(high_coupling1):
                risk_areas.append(f"{len(high_coupling2) - len(high_coupling1)} more highly coupled files")
            
            # Retry LLM for partially cached snapshots (fix #6)
            arch1 = record['macro1']
            arch2 = record['macro2']
            if not arch1 or not arch2:
                logger.info("⚠️ Partially cached snapshot detected - attempting LLM retry")
                try:
                    if not arch1:
                        session.run("""
                            MATCH (s:Snapshot {snapshot_id: $sid})
                            SET s.arch_macro = $fallback
                        """, sid=snapshot1, fallback=f"Architecture analysis for snapshot {snapshot1[:8]} (auto-generated during comparison)")
                        arch1 = f"Architecture analysis for snapshot {snapshot1[:8]} (auto-generated during comparison)"
                    if not arch2:
                        session.run("""
                            MATCH (s:Snapshot {snapshot_id: $sid})
                            SET s.arch_macro = $fallback
                        """, sid=snapshot2, fallback=f"Architecture analysis for snapshot {snapshot2[:8]} (auto-generated during comparison)")
                        arch2 = f"Architecture analysis for snapshot {snapshot2[:8]} (auto-generated during comparison)"
                except Exception as e:
                    logger.error(f"Failed to patch partial snapshot: {e}")
            
            return {
                "snapshot1": {
                    "id": snapshot1[:8],
                    "date": record['date1'],
                    "files": record['tf1'],
                    "dependencies": record['td1'],
                    "avg_coupling": record['ac1'],
                    "cycles": record['cc1'],
                    "patterns": patterns1,
                    "architecture": arch1 or "Not cached"
                },
                "snapshot2": {
                    "id": snapshot2[:8],
                    "date": record['date2'],
                    "files": record['tf2'],
                    "dependencies": record['td2'],
                    "avg_coupling": record['ac2'],
                    "cycles": record['cc2'],
                    "patterns": patterns2,
                    "architecture": arch2 or "Not cached"
                },
                "changes": {
                    "files_added": added_files[:20],
                    "files_removed": removed_files[:20],
                    "files_modified": modified_files[:20],
                    "file_delta": len(added_files) - len(removed_files),
                    "total_changes": len(added_files) + len(removed_files) + len(modified_files),
                    "dependency_delta": (record['td2'] or 0) - (record['td1'] or 0),
                    "coupling_delta": coupling_delta,
                    "cycle_delta": cycle_delta,
                    "pattern_changes": pattern_changes,
                    "high_coupling_before": len(high_coupling1),
                    "high_coupling_after": len(high_coupling2)
                },
                "risk_assessment": {
                    "risk_level": "high" if len(risk_areas) >= 3 else "medium" if len(risk_areas) >= 1 else "low",
                    "risk_areas": risk_areas
                },
                "structural_risks": self._compute_risks_for_changed_files(
                    added_files + modified_files
                ),
                "summary": self._generate_comparison_summary(record, pattern_changes, coupling_delta, cycle_delta, len(added_files), len(removed_files), len(modified_files))
            }
    
    def _compare_patterns(self, patterns1: Dict, patterns2: Dict) -> Dict:
        """Compare architectural patterns between snapshots"""
        changes = {}
        all_patterns = set(patterns1.keys()) | set(patterns2.keys())
        
        for pattern in all_patterns:
            p1 = patterns1.get(pattern, {})
            p2 = patterns2.get(pattern, {})
            
            detected1 = p1.get('detected', False)
            detected2 = p2.get('detected', False)
            
            if detected1 != detected2:
                if detected2:
                    changes[pattern] = "newly_detected"
                else:
                    changes[pattern] = "no_longer_detected"
            elif detected1 and detected2:
                conf1 = p1.get('confidence', 0)
                conf2 = p2.get('confidence', 0)
                conf_delta = round(conf2 - conf1, 2)
                if abs(conf_delta) > 0.1:
                    changes[pattern] = f"confidence_changed: {conf_delta:+.2f}"
        
        return changes
    
    def _compute_risks_for_changed_files(self, changed_files: list) -> list:
        """Compute structural risk for changed files using current graph."""
        if not self.coupling_analyzer or not changed_files:
            return []
        
        risks = []
        for fp in changed_files[:30]:  # limit to avoid slowdowns
            if not fp:
                continue
            risk = self.coupling_analyzer.compute_structural_risk(fp)
            if risk['level'] == 'unknown':
                # Try flexible matching by filename
                fname = fp.replace('\\', '/').split('/')[-1]
                for node in self.coupling_analyzer.graph.nodes():
                    if node.replace('\\', '/').split('/')[-1] == fname:
                        risk = self.coupling_analyzer.compute_structural_risk(node)
                        if risk['level'] != 'unknown':
                            break
            if risk['score'] > 0:
                risk['file'] = fp
                risks.append(risk)
        
        risks.sort(key=lambda x: x['score'], reverse=True)
        return risks[:10]
    
    def _generate_comparison_summary(self, record: Dict, pattern_changes: Dict, 
                                     coupling_delta: float, cycle_delta: int,
                                     added_count: int, removed_count: int, modified_count: int) -> str:
        """Generate human-readable summary of changes"""
        parts = []
        
        if added_count > 0:
            parts.append(f"Added {added_count} files")
        if removed_count > 0:
            parts.append(f"Removed {removed_count} files")
        if modified_count > 0:
            parts.append(f"Modified {modified_count} files")
        
        if coupling_delta > 0.5:
            parts.append(f"Coupling increased significantly (+{coupling_delta})")
        elif coupling_delta < -0.5:
            parts.append(f"Coupling decreased ({coupling_delta})")
        
        if cycle_delta > 0:
            parts.append(f"{cycle_delta} new circular dependencies")
        elif cycle_delta < 0:
            parts.append(f"{abs(cycle_delta)} circular dependencies resolved")
        
        if pattern_changes:
            parts.append(f"{len(pattern_changes)} architectural pattern changes")
        
        return "; ".join(parts) if parts else "No significant changes detected"
    def compare_architecture(self, repo_id: str, commit1: str, commit2: str) -> Dict:
        """
        Compare architectural changes between two commits
        
        Args:
            repo_id: Repository ID
            commit1: First commit hash
            commit2: Second commit hash
        
        Returns:
            Dict with architectural comparison including patterns, coupling, and structural changes
        """
        import json
        
        # Get snapshots for each commit
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (s1:Snapshot {repo_id: $repo_id, commit_hash: $commit1})
                MATCH (s2:Snapshot {repo_id: $repo_id, commit_hash: $commit2})
                RETURN s1.snapshot_id as snapshot1, s2.snapshot_id as snapshot2,
                       s1.patterns as patterns1, s2.patterns as patterns2,
                       s1.coupling as coupling1, s2.coupling as coupling2,
                       s1.arch_macro as macro1, s2.arch_macro as macro2,
                       s1.total_files as files1, s2.total_files as files2,
                       s1.avg_coupling as avg_coupling1, s2.avg_coupling as avg_coupling2,
                       s1.cycle_count as cycles1, s2.cycle_count as cycles2
                """, repo_id=repo_id, commit1=commit1, commit2=commit2)
            
            record = result.single()
            
            if not record:
                # Try to find snapshots by partial commit hash match
                result = session.run("""
                    MATCH (s1:Snapshot {repo_id: $repo_id})
                    WHERE s1.commit_hash STARTS WITH $commit1
                    MATCH (s2:Snapshot {repo_id: $repo_id})
                    WHERE s2.commit_hash STARTS WITH $commit2
                    RETURN s1.snapshot_id as snapshot1, s2.snapshot_id as snapshot2,
                           s1.patterns as patterns1, s2.patterns as patterns2,
                           s1.coupling as coupling1, s2.coupling as coupling2,
                           s1.arch_macro as macro1, s2.arch_macro as macro2,
                           s1.total_files as files1, s2.total_files as files2,
                           s1.avg_coupling as avg_coupling1, s2.avg_coupling as avg_coupling2,
                           s1.cycle_count as cycles1, s2.cycle_count as cycles2
                    LIMIT 1
                    """, repo_id=repo_id, commit1=commit1, commit2=commit2)
                
                record = result.single()
                
                if not record:
                    return {
                        "error": f"Snapshots not found for commits {commit1[:8]} and {commit2[:8]}",
                        "suggestion": "Please ensure both commits have been analyzed"
                    }
        
        # Parse patterns
        try:
            patterns1 = json.loads(record['patterns1']) if record['patterns1'] else {}
            patterns2 = json.loads(record['patterns2']) if record['patterns2'] else {}
        except:
            patterns1 = {}
            patterns2 = {}
        
        # Compare patterns
        pattern_changes = self._compare_patterns(patterns1, patterns2)
        
        # Calculate deltas
        coupling_delta = (record['avg_coupling2'] or 0) - (record['avg_coupling1'] or 0)
        cycle_delta = (record['cycles2'] or 0) - (record['cycles1'] or 0)
        file_delta = (record['files2'] or 0) - (record['files1'] or 0)
        
        # Assess risk
        risk_areas = []
        if coupling_delta > 1.0:
            risk_areas.append(f"Significant coupling increase (+{coupling_delta:.2f})")
        if cycle_delta > 0:
            risk_areas.append(f"{cycle_delta} new circular dependencies")
        if file_delta > 20:
            risk_areas.append(f"Large file increase (+{file_delta} files)")
        
        return {
            "commit1": {
                "hash": commit1[:8],
                "patterns": patterns1,
                "metrics": {
                    "files": record['files1'],
                    "avg_coupling": record['avg_coupling1'],
                    "cycles": record['cycles1']
                },
                "architecture_summary": record['macro1'][:200] + "..." if record['macro1'] and len(record['macro1']) > 200 else record['macro1']
            },
            "commit2": {
                "hash": commit2[:8],
                "patterns": patterns2,
                "metrics": {
                    "files": record['files2'],
                    "avg_coupling": record['avg_coupling2'],
                    "cycles": record['cycles2']
                },
                "architecture_summary": record['macro2'][:200] + "..." if record['macro2'] and len(record['macro2']) > 200 else record['macro2']
            },
            "changes": {
                "pattern_changes": pattern_changes,
                "coupling_delta": round(coupling_delta, 2),
                "cycle_delta": cycle_delta,
                "file_delta": file_delta
            },
            "risk_assessment": {
                "risk_level": "high" if len(risk_areas) >= 2 else "medium" if len(risk_areas) == 1 else "low",
                "risk_areas": risk_areas
            },
            "summary": f"File count changed by {file_delta:+d}, coupling changed by {coupling_delta:+.2f}, {cycle_delta:+d} cycle changes, {len(pattern_changes)} pattern changes"
        }
    
    
    
    def _has_uncommitted_changes(self, repo_path: str) -> bool:
        """Check if repository has uncommitted changes"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=repo_path, timeout=5
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def _enforce_cache_limit(self):
        """Enforce LRU cache size limit (must be called within cache_lock)"""
        while len(self.memory_cache) > MAX_CACHE_SIZE:
            # Remove oldest item (FIFO for OrderedDict)
            self.memory_cache.popitem(last=False)
            logger.debug(f"🗑️ Evicted old cache entry (size: {len(self.memory_cache)})")
    
    def _extract_function_code(self, file_path: str, function_name: str, start_line: int) -> str:
        """Extract actual function code from source file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Start from function definition line
            func_lines = []
            indent_level = None
            
            for i in range(start_line - 1, len(lines)):
                line = lines[i]
                
                # Detect initial indent
                if indent_level is None and line.strip():
                    indent_level = len(line) - len(line.lstrip())
                    func_lines.append(line.rstrip())
                    continue
                
                # Stop at next function/class at same or lower indent
                if line.strip() and not line.strip().startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= indent_level and i > start_line:
                        break
                
                func_lines.append(line.rstrip())
                
                # Limit to 50 lines
                if len(func_lines) >= 50:
                    func_lines.append('... (truncated)')
                    break
            
            return '\n'.join(func_lines) if func_lines else f"# Function {function_name} (code not extracted)"
        except Exception as e:
            return f"# Error reading function code: {str(e)}"
    
    def _store_dependencies_in_neo4j(self):
        """Store NetworkX graph dependencies as DEPENDS_ON relationships in Neo4j"""
        if not self.dependency_mapper or not self.dependency_mapper.graph:
            return
        
        edge_count = 0
        with self.graph_db.driver.session() as session:
            for source, target in self.dependency_mapper.graph.edges():
                # Only store file-to-file dependencies (not external modules)
                if '\\' in target or '/' in target:  # It's a file path
                    # Normalize paths for consistent matching
                    norm_source = str(Path(source).resolve()) if Path(source).exists() else source
                    norm_target = str(Path(target).resolve()) if Path(target).exists() else target
                    
                    # Use flexible matching to find File nodes
                    source_name = Path(source).name
                    target_name = Path(target).name
                    
                    session.run("""
                        MATCH (f1:File)
                        WHERE f1.path = $source OR f1.file_path = $source
                           OR f1.path ENDS WITH '\\\\' + $source_name
                           OR f1.path ENDS WITH '/' + $source_name
                        WITH f1
                        MATCH (f2:File)
                        WHERE f2.path = $target OR f2.file_path = $target
                           OR f2.path ENDS WITH '\\\\' + $target_name
                           OR f2.path ENDS WITH '/' + $target_name
                        WITH f1, f2
                        WHERE f1 <> f2
                        MERGE (f1)-[:DEPENDS_ON]->(f2)
                        """, source=norm_source, target=norm_target,
                            source_name=source_name, target_name=target_name)
                    edge_count += 1
        
        logger.info(f"   ✅ Stored {edge_count} DEPENDS_ON relationships in Neo4j")
