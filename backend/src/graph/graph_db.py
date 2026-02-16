from neo4j import GraphDatabase
from typing import Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GraphDB:
    def __init__(self, uri: str, user: str, password: str):
        logger.info(f"🔌 Attempting to connect to Neo4j at {uri}")
        logger.info(f"   User: {user}")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Neo4j connected successfully!")
            logger.info(f"   Connection URI: {uri}")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            logger.error("   Make sure Neo4j Desktop is running and database is started")
            raise
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def create_file_node(self, file_path: str, language: str, content_hash: str = None):
        if not file_path:
            logger.warning("Attempted to create File node with empty path, skipping")
            return
        # Normalize path for consistency
        normalized_path = str(Path(file_path).resolve())
        # Store a forward-slash suffix for cross-platform matching
        path_suffix = normalized_path.replace('\\', '/')
        with self.driver.session() as session:
            session.run(
                """MERGE (f:File {path: $path}) 
                   SET f.language = $language, 
                       f.file_path = $path, 
                       f.content_hash = $hash,
                       f.path_normalized = $path_suffix""",
                path=normalized_path, language=language, hash=content_hash,
                path_suffix=path_suffix
            )
    
    def create_class_node(self, file_path: str, class_name: str, line: int):
        # Normalize path for consistent matching
        normalized_path = str(Path(file_path).resolve())
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File)
                WHERE f.path = $file_path OR f.file_path = $file_path
                MERGE (c:Class {name: $name, file: $file_path})
                SET c.line = $line
                MERGE (f)-[:CONTAINS]->(c)
                """,
                file_path=normalized_path, name=class_name, line=line
            )
    
    def create_function_node(self, file_path: str, func_name: str, line: int, repo_id: str = None):
        # Normalize path
        normalized_path = str(Path(file_path).resolve())
        with self.driver.session() as session:
            if repo_id:
                # First ensure File is linked to Repository
                session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})
                    MATCH (f:File)
                    WHERE f.path = $file_path OR f.file_path = $file_path
                    MERGE (r)-[:CONTAINS]->(f)
                    """,
                    repo_id=repo_id, file_path=normalized_path
                )
                # Then create function and link to file
                session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $file_path OR f.file_path = $file_path
                    MERGE (fn:Function {name: $name, file: $file_path})
                    SET fn.line = $line
                    MERGE (f)-[:CONTAINS]->(fn)
                    """,
                    file_path=normalized_path, name=func_name, line=line
                )
            else:
                session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $file_path OR f.file_path = $file_path
                    MERGE (fn:Function {name: $name, file: $file_path})
                    SET fn.line = $line
                    MERGE (f)-[:CONTAINS]->(fn)
                    """,
                    file_path=normalized_path, name=func_name, line=line
                )
    
    def create_import_relationship(self, from_file: str, to_module: str):
        # Normalize from_file path for matching
        normalized_from = self._normalize_path(from_file)
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File)
                WHERE f.path = $from_file OR f.file_path = $from_file
                MERGE (m:Module {name: $to_module})
                MERGE (f)-[:IMPORTS]->(m)
                """,
                from_file=normalized_from, to_module=to_module
            )
            
            # Build module path with both separators for cross-platform matching
            module_parts_backslash = to_module.replace('.', '\\\\')
            module_parts_forward = to_module.replace('.', '/')
            module_name = to_module.split('.')[-1]
            
            session.run(
                """
                MATCH (f:File)
                WHERE f.path = $from_file OR f.file_path = $from_file
                MATCH (target:File)
                WHERE target.path ENDS WITH $module_bs + '.py' 
                   OR target.path ENDS WITH $module_bs + '.js'
                   OR target.path ENDS WITH $module_fs + '.py'
                   OR target.path ENDS WITH $module_fs + '.js'
                   OR target.path ENDS WITH '\\\\' + $module_name + '.py'
                   OR target.path ENDS WITH '\\\\' + $module_name + '.js'
                   OR target.path ENDS WITH '/' + $module_name + '.py'
                   OR target.path ENDS WITH '/' + $module_name + '.js'
                MERGE (f)-[:DEPENDS_ON]->(target)
                """,
                from_file=normalized_from, 
                module_bs=module_parts_backslash,
                module_fs=module_parts_forward,
                module_name=module_name
            )
    
    def create_function_call(self, from_file: str, called_function: str, repo_id: str = None):
        """Create CALLS relationship between file and function within same repository"""
        normalized_from = self._normalize_path(from_file)
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(fn:Function {name: $called_function})
                    MERGE (f)-[:CALLS]->(fn)
                    RETURN count(fn) as matched
                    """,
                    repo_id=repo_id,
                    from_file=normalized_from,
                    called_function=called_function
                )
                record = result.single()
                if record and record['matched'] > 0:
                    logger.debug(f"✓ CALLS: {Path(from_file).name} -> {called_function}")
            else:
                result = session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (fn:Function {name: $called_function})
                    MERGE (f)-[:CALLS]->(fn)
                    RETURN count(fn) as matched
                    """,
                    from_file=normalized_from,
                    called_function=called_function
                )
                record = result.single()
                if record and record['matched'] > 0:
                    logger.debug(f"✓ CALLS: {Path(from_file).name} -> {called_function}")
    
    def create_function_to_function_call(self, from_file: str, caller_func: str, callee_func: str, repo_id: str = None):
        """Create CALLS relationship between two functions"""
        normalized_from = self._normalize_path(from_file)
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (f)-[:CONTAINS]->(caller:Function {name: $caller_func})
                    MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(callee:Function {name: $callee_func})
                    MERGE (caller)-[:CALLS]->(callee)
                    RETURN count(callee) as matched
                    """,
                    repo_id=repo_id,
                    from_file=normalized_from,
                    caller_func=caller_func,
                    callee_func=callee_func
                )
                record = result.single()
                if record and record['matched'] > 0:
                    logger.debug(f"✓ {caller_func} -> {callee_func}")
            else:
                result = session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (f)-[:CONTAINS]->(caller:Function {name: $caller_func})
                    MATCH (callee:Function {name: $callee_func})
                    MERGE (caller)-[:CALLS]->(callee)
                    RETURN count(callee) as matched
                    """,
                    from_file=normalized_from,
                    caller_func=caller_func,
                    callee_func=callee_func
                )
                record = result.single()
                if record and record['matched'] > 0:
                    logger.debug(f"✓ {caller_func} -> {callee_func}")
    
    def create_transitive_function_calls(self, repo_id: str = None):
        """Create transitive CALLS_TRANSITIVE relationships for function call chains"""
        with self.driver.session() as session:
            if repo_id:
                # Create transitive relationships (depth 2-5)
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(:File)-[:CONTAINS]->(a:Function)
                    MATCH (a)-[:CALLS*2..5]->(c:Function)
                    WHERE (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(c)
                    MERGE (a)-[:CALLS_TRANSITIVE]->(c)
                    RETURN count(*) as created
                    """,
                    repo_id=repo_id
                )
                record = result.single()
                return record['created'] if record else 0
            else:
                result = session.run(
                    """
                    MATCH (a:Function)-[:CALLS*2..5]->(c:Function)
                    MERGE (a)-[:CALLS_TRANSITIVE]->(c)
                    RETURN count(*) as created
                    """
                )
                record = result.single()
                return record['created'] if record else 0
    
    def get_dependencies(self, file_path: str) -> List[str]:
        normalized = self._normalize_path(file_path)
        suffix = self._get_path_suffix(file_path)
        suffix_fwd = suffix.replace('\\', '/')
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (f:File)
                WHERE f.path = $path OR f.file_path = $path
                   OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                   OR f.path_normalized ENDS WITH $suffix_fwd
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:File)
                RETURN COLLECT(DISTINCT m.name) + COLLECT(DISTINCT dep.path) as dependencies
                """,
                path=normalized,
                suffix=suffix,
                suffix_fwd=suffix_fwd
            )
            record = result.single()
            return [d for d in record["dependencies"] if d] if record else []
    
    def get_affected_files(self, file_path: str) -> List[str]:
        normalized = self._normalize_path(file_path)
        suffix = self._get_path_suffix(file_path)
        suffix_fwd = suffix.replace('\\', '/')
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (target:File)
                WHERE target.path = $path OR target.file_path = $path
                   OR target.path ENDS WITH $suffix OR target.path ENDS WITH $suffix_fwd
                   OR target.path_normalized ENDS WITH $suffix_fwd
                MATCH (f:File)-[:DEPENDS_ON|IMPORTS*1..3]->(target)
                RETURN DISTINCT f.path as path
                """,
                path=normalized,
                suffix=suffix,
                suffix_fwd=suffix_fwd
            )
            return [record["path"] for record in result]
    
    def debug_file(self, file_path: str) -> Dict:
        """Debug method to see what's stored for a file"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (f:File)
                WHERE f.path CONTAINS $path
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:File)
                RETURN f.path as file_path, 
                       COLLECT(DISTINCT m.name) as modules,
                       COLLECT(DISTINCT dep.path) as files,
                       [(f)-[r]->() | type(r)] as rel_types
                LIMIT 5
                """,
                path=file_path.split('\\')[-1]  # Just filename
            )
            return [dict(record) for record in result]
    
    def get_all_files(self) -> List[str]:
        """Get all file paths stored in graph"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:File) 
                WHERE f.path IS NOT NULL
                RETURN f.path as path 
                ORDER BY f.path
            """)
            return [record["path"] for record in result if record["path"]]
    
    def get_all_functions(self, repo_id: str = None) -> List[Dict]:
        """Get all functions with their file and line info, optionally filtered by repo"""
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                    RETURN fn.name as name, fn.file as file, fn.line as line
                    ORDER BY fn.name
                    """,
                    repo_id=repo_id
                )
            else:
                result = session.run(
                    """
                    MATCH (fn:Function)
                    RETURN fn.name as name, fn.file as file, fn.line as line
                    ORDER BY fn.name
                    """
                )
            return [dict(record) for record in result]
    
    def get_function_info(self, function_name: str) -> Dict:
        """Get detailed info about a specific function"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (fn:Function {name: $name})
                RETURN fn.name as name, fn.file as file, fn.line as line
                LIMIT 1
                """,
                name=function_name
            )
            record = result.single()
            return dict(record) if record else None
    
    def get_function_callers(self, function_name: str, repo_id: str = None) -> List[Dict]:
        """Get all files and functions that call this function"""
        with self.driver.session() as session:
            if repo_id:
                # Get file-level callers
                file_result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(:File)-[:CONTAINS]->(fn:Function {name: $name})
                    MATCH (r)-[:CONTAINS]->(caller:File)-[:CALLS]->(fn)
                    RETURN DISTINCT caller.path as file
                    """,
                    repo_id=repo_id,
                    name=function_name
                )
                file_callers = [dict(record) for record in file_result]
                
                # Also get function-to-function callers
                func_result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(:File)-[:CONTAINS]->(fn:Function {name: $name})
                    MATCH (r)-[:CONTAINS]->(f:File)-[:CONTAINS]->(caller:Function)-[:CALLS]->(fn)
                    RETURN DISTINCT f.path as file, caller.name as caller_name, caller.line as line
                    """,
                    repo_id=repo_id,
                    name=function_name
                )
                func_callers = [dict(record) for record in func_result]
            else:
                file_result = session.run(
                    """
                    MATCH (fn:Function {name: $name})
                    MATCH (caller:File)-[:CALLS]->(fn)
                    RETURN DISTINCT caller.path as file
                    """,
                    name=function_name
                )
                file_callers = [dict(record) for record in file_result]
                
                func_result = session.run(
                    """
                    MATCH (fn:Function {name: $name})
                    MATCH (f:File)-[:CONTAINS]->(caller:Function)-[:CALLS]->(fn)
                    RETURN DISTINCT f.path as file, caller.name as caller_name, caller.line as line
                    """,
                    name=function_name
                )
                func_callers = [dict(record) for record in func_result]
            
            # Merge results: function-level callers are more specific
            # Deduplicate by file path, preferring function-level info
            seen_files = set()
            merged = []
            for fc in func_callers:
                key = (fc.get('file', ''), fc.get('caller_name', ''))
                if key not in seen_files:
                    seen_files.add(key)
                    merged.append(fc)
            for fc in file_callers:
                file_key = fc.get('file', '')
                if not any(file_key == m.get('file', '') for m in merged):
                    merged.append(fc)
            
            return merged
    
    def get_graph_data(self, repo_id: str = None, limit: int = 50) -> Dict:
        """Get nodes and edges for graph visualization"""
        with self.driver.session() as session:
            # Get file nodes and their relationships
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[rel:DEPENDS_ON|IMPORTS]->(target:File)
                    WHERE (r)-[:CONTAINS]->(target)
                    WITH f, COLLECT({target: target.path, type: type(rel)}) as relationships
                    RETURN f.path as id, f.path as label, relationships
                    LIMIT $limit
                    """,
                    repo_id=repo_id,
                    limit=limit
                )
            else:
                result = session.run(
                    """
                    MATCH (f:File)
                    OPTIONAL MATCH (f)-[r:DEPENDS_ON|IMPORTS]->(target:File)
                    WITH f, COLLECT({target: target.path, type: type(r)}) as relationships
                    RETURN f.path as id, f.path as label, relationships
                    LIMIT $limit
                    """,
                    limit=limit
                )
            
            nodes = []
            edges = []
            seen_nodes = set()
            
            for record in result:
                node_id = record['id']
                if not node_id:  # Skip if node_id is None
                    continue
                    
                if node_id not in seen_nodes:
                    # Show last 2 path parts for better context
                    parts = node_id.replace('\\', '/').split('/')
                    label = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]
                    nodes.append({
                        'id': node_id,
                        'label': label
                    })
                    seen_nodes.add(node_id)
                
                for rel in record['relationships']:
                    if rel['target']:
                        target_id = rel['target']
                        if target_id not in seen_nodes:
                            parts = target_id.replace('\\', '/').split('/')
                            label = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]
                            nodes.append({
                                'id': target_id,
                                'label': label
                            })
                            seen_nodes.add(target_id)
                        
                        edges.append({
                            'source': node_id,
                            'target': target_id,
                            'type': rel['type']
                        })
            
            return {'nodes': nodes, 'edges': edges}
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent matching"""
        try:
            resolved = str(Path(path).resolve())
            return resolved
        except:
            return path
    
    def _get_path_suffix(self, path: str) -> str:
        """Get path suffix for flexible matching (returns backslash-separated)"""
        # Normalize separators first
        normalized = path.replace('/', '\\')
        parts = Path(normalized).parts
        if len(parts) >= 3:
            return str(Path(*parts[-3:]))
        return str(Path(normalized).name)
    
    def resolve_file_path(self, file_path: str) -> str:
        """Resolve a user-provided path to the actual path stored in Neo4j.
        
        Tries multiple matching strategies:
        1. Exact match on path or file_path
        2. ENDS WITH on the path suffix (backslash)
        3. ENDS WITH on the path suffix (forward slash)
        4. Filename-only match as last resort
        
        Returns the stored path or the original if no match found.
        """
        suffix = self._get_path_suffix(file_path)
        suffix_fwd = suffix.replace('\\', '/')
        filename = Path(file_path).name
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:File)
                WHERE f.path = $path OR f.file_path = $path
                   OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                   OR f.path_normalized ENDS WITH $suffix_fwd
                   OR f.path ENDS WITH '\\\\' + $filename
                   OR f.path ENDS WITH '/' + $filename
                RETURN f.path as resolved_path
                LIMIT 1
            """, path=file_path, suffix=suffix, suffix_fwd=suffix_fwd, filename=filename)
            
            record = result.single()
            if record and record['resolved_path']:
                return record['resolved_path']
        
        # Fallback: try normalizing
        try:
            return str(Path(file_path).resolve())
        except:
            return file_path
    
    def store_dependency_snapshot(self, repo_id: str, commit_hash: str, edges: List[tuple]):
        """Store dependency edges for a commit"""
        with self.driver.session() as session:
            for source, target in edges:
                session.run("""
                    MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                    MERGE (f1:File {path: $source})
                    SET f1.file_path = $source
                    MERGE (f2:File {path: $target})
                    SET f2.file_path = $target
                    MERGE (f1)-[:DEPENDS_ON_AT {commit: $commit_hash}]->(f2)
                    """, repo_id=repo_id, commit_hash=commit_hash, source=source, target=target)
    
    def store_coupling_snapshot(self, repo_id: str, commit_hash: str, metrics: Dict):
        """Store coupling metrics for a commit"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                SET c.total_files = $total_files,
                    c.total_deps = $total_deps,
                    c.avg_coupling = $avg_coupling,
                    c.cycle_count = $cycle_count
                """, repo_id=repo_id, commit_hash=commit_hash, **metrics)
    
    def get_dependencies_at_commit(self, repo_id: str, commit_hash: str) -> List[tuple]:
        """Get dependency edges at specific commit"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f1:File)-[r:DEPENDS_ON_AT {commit: $commit_hash}]->(f2:File)
                RETURN COALESCE(f1.file_path, f1.path) as source, 
                       COALESCE(f2.file_path, f2.path) as target
                """, commit_hash=commit_hash)
            return [(r['source'], r['target']) for r in result]
    
    def get_coupling_at_commit(self, repo_id: str, commit_hash: str) -> Dict:
        """Get coupling metrics at specific commit"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                RETURN c.total_files as total_files, c.total_deps as total_deps,
                       c.avg_coupling as avg_coupling, c.cycle_count as cycle_count
                """, repo_id=repo_id, commit_hash=commit_hash)
            record = result.single()
            return dict(record) if record else {}
