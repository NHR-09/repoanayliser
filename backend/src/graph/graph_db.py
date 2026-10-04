from neo4j import GraphDatabase
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GraphDB:
    BULK_BATCH_SIZE = 2000

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
    
    def cleanup_orphaned_nodes(self):
        """Delete Function/Class nodes not connected to any File via [:CONTAINS].
        These are stale leftovers from previous analyses or failed writes.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (fn:Function)
                WHERE NOT (:File)-[:CONTAINS]->(fn)
                DETACH DELETE fn
                RETURN count(fn) as deleted
            """)
            fn_deleted = result.single()['deleted']
            
            result = session.run("""
                MATCH (c:Class)
                WHERE NOT (:File)-[:CONTAINS]->(c)
                DETACH DELETE c
                RETURN count(c) as deleted
            """)
            cls_deleted = result.single()['deleted']
            
            if fn_deleted > 0 or cls_deleted > 0:
                logger.info(f"🧹 Cleaned up {fn_deleted} orphaned Functions, {cls_deleted} orphaned Classes")
            return fn_deleted + cls_deleted
    
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
            # Create function ONLY if the parent File exists
            # Using a single statement ensures no orphaned Function nodes
            result = session.run(
                """
                MATCH (f:File)
                WHERE f.path = $file_path OR f.file_path = $file_path
                WITH f LIMIT 1
                MERGE (fn:Function {name: $name, file: $file_path})
                SET fn.line = $line
                MERGE (f)-[:CONTAINS]->(fn)
                RETURN fn.name as created
                """,
                file_path=normalized_path, name=func_name, line=line
            )
            record = result.single()
            if not record:
                logger.warning(f"⚠️  Skipped orphan function '{func_name}' — no File node for {normalized_path}")
    
    def set_function_parent_class(self, file_path: str, func_name: str, class_name: str, line: int, repo_id: str = None):
        """Set parent_class property on a Function node.
        Uses line number for disambiguation when multiple classes have same method name."""
        normalized = self._normalize_path(file_path)
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File)-[:CONTAINS]->(fn:Function {name: $func_name})
                WHERE (f.path = $file_path OR f.file_path = $file_path)
                  AND fn.line = $line
                SET fn.parent_class = $class_name
                """,
                file_path=normalized, func_name=func_name,
                class_name=class_name, line=line
            )
    
    def create_resolved_method_call(self, from_file: str, caller_class: str, caller_method: str,
                                     target_class: str, target_method: str, repo_id: str = None):
        """Create a CALLS edge between two class methods, resolved via self.X attribute types.
        
        Example: Kernel.request_seat -> ProcessManager.get_process
        This creates the edge: (Function{name:request_seat, parent_class:Kernel})
                              -[:CALLS {source: 'oop_resolution'}]->
                               (Function{name:get_process, parent_class:ProcessManager})
        """
        normalized_from = self._normalize_path(from_file)
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f1:File)-[:CONTAINS]->(caller:Function)
                    WHERE (f1.path = $from_file OR f1.file_path = $from_file)
                      AND caller.name = $caller_method
                      AND caller.parent_class = $caller_class
                    MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(callee:Function)
                    WHERE callee.name = $target_method
                      AND callee.parent_class = $target_class
                    MERGE (caller)-[:CALLS {source: 'oop_resolution'}]->(callee)
                    RETURN count(callee) as matched
                    """,
                    repo_id=repo_id,
                    from_file=normalized_from,
                    caller_class=caller_class,
                    caller_method=caller_method,
                    target_class=target_class,
                    target_method=target_method
                )
            else:
                result = session.run(
                    """
                    MATCH (f1:File)-[:CONTAINS]->(caller:Function)
                    WHERE (f1.path = $from_file OR f1.file_path = $from_file)
                      AND caller.name = $caller_method
                      AND caller.parent_class = $caller_class
                    MATCH (:File)-[:CONTAINS]->(callee:Function)
                    WHERE callee.name = $target_method
                      AND callee.parent_class = $target_class
                    MERGE (caller)-[:CALLS {source: 'oop_resolution'}]->(callee)
                    RETURN count(callee) as matched
                    """,
                    from_file=normalized_from,
                    caller_class=caller_class,
                    caller_method=caller_method,
                    target_class=target_class,
                    target_method=target_method
                )
            record = result.single()
            if record and record['matched'] > 0:
                logger.debug(f"✓ OOP CALLS: {caller_class}.{caller_method} -> {target_class}.{target_method}")
    
    def create_import_relationship(self, from_file: str, to_module: str, repo_id: str = None):
        # Normalize from_file path for matching
        normalized_from = self._normalize_path(from_file)
        
        # Build module path with both separators for cross-platform matching
        module_parts_backslash = to_module.replace('.', '\\\\')
        module_parts_forward = to_module.replace('.', '/')
        module_name = to_module.split('.')[-1]

        with self.driver.session() as session:
            if repo_id:
                session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MERGE (m:Module {name: $to_module})
                    MERGE (f)-[:IMPORTS]->(m)
                    """,
                    repo_id=repo_id, from_file=normalized_from, to_module=to_module
                )
                
                session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (r)-[:CONTAINS]->(target:File)
                    WHERE target <> f AND (
                          target.path ENDS WITH $module_bs + '.py' 
                       OR target.path ENDS WITH $module_bs + '.js'
                       OR target.path ENDS WITH $module_fs + '.py'
                       OR target.path ENDS WITH $module_fs + '.js'
                       OR target.file_path ENDS WITH $module_bs + '.py' 
                       OR target.file_path ENDS WITH $module_bs + '.js'
                       OR target.file_path ENDS WITH $module_fs + '.py'
                       OR target.file_path ENDS WITH $module_fs + '.js'
                       OR target.path_normalized ENDS WITH '/' + $module_fs + '.py'
                       OR target.path_normalized ENDS WITH '/' + $module_fs + '.js'
                       OR target.path_normalized ENDS WITH '/' + $module_name + '.py'
                       OR target.path_normalized ENDS WITH '/' + $module_name + '.js'
                    )
                    WITH f, target,
                         CASE 
                            WHEN target.path_normalized ENDS WITH '/' + $module_fs + '.py' THEN 1
                            WHEN target.path_normalized ENDS WITH '/' + $module_fs + '.js' THEN 1
                            WHEN target.path ENDS WITH $module_fs + '.py' THEN 2
                            WHEN target.path ENDS WITH $module_fs + '.js' THEN 2
                            ELSE 3
                         END AS priority
                    ORDER BY priority ASC
                    WITH f, head(collect(target)) AS best_target
                    WHERE best_target IS NOT NULL
                    MERGE (f)-[:DEPENDS_ON]->(best_target)
                    """,
                    repo_id=repo_id,
                    from_file=normalized_from, 
                    module_bs=module_parts_backslash,
                    module_fs=module_parts_forward,
                    module_name=module_name
                )
            else:
                session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MERGE (m:Module {name: $to_module})
                    MERGE (f)-[:IMPORTS]->(m)
                    """,
                    from_file=normalized_from, to_module=to_module
                )
                session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (target:File)
                    WHERE target <> f AND (
                          target.path ENDS WITH $module_bs + '.py' 
                       OR target.path ENDS WITH $module_bs + '.js'
                       OR target.path ENDS WITH $module_fs + '.py'
                       OR target.path ENDS WITH $module_fs + '.js'
                       OR target.file_path ENDS WITH $module_bs + '.py' 
                       OR target.file_path ENDS WITH $module_bs + '.js'
                       OR target.file_path ENDS WITH $module_fs + '.py'
                       OR target.file_path ENDS WITH $module_fs + '.js'
                       OR target.path_normalized ENDS WITH '/' + $module_fs + '.py'
                       OR target.path_normalized ENDS WITH '/' + $module_fs + '.js'
                       OR target.path_normalized ENDS WITH '/' + $module_name + '.py'
                       OR target.path_normalized ENDS WITH '/' + $module_name + '.js'
                    )
                    WITH f, target,
                         CASE 
                            WHEN target.path_normalized ENDS WITH '/' + $module_fs + '.py' THEN 1
                            WHEN target.path_normalized ENDS WITH '/' + $module_fs + '.js' THEN 1
                            WHEN target.path ENDS WITH $module_fs + '.py' THEN 2
                            WHEN target.path ENDS WITH $module_fs + '.js' THEN 2
                            ELSE 3
                         END AS priority
                    ORDER BY priority ASC
                    WITH f, head(collect(target)) AS best_target
                    WHERE best_target IS NOT NULL
                    MERGE (f)-[:DEPENDS_ON]->(best_target)
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
    
    def create_function_to_function_call(self, from_file: str, caller_func: str, callee_func: str, repo_id: str = None, caller_class: str = None, line: int = None):
        """Create CALLS relationship between two functions.
        Prioritizes callee resolution in order:
        1. Same file (local function)
        2. Dependent/imported file (imported function)
        3. Repository-wide function
        """
        normalized_from = self._normalize_path(from_file)
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $from_file OR f.file_path = $from_file
                    MATCH (f)-[:CONTAINS]->(caller:Function {name: $caller_func})
                    WHERE ($caller_class IS NULL OR caller.parent_class = $caller_class OR caller.parent_class IS NULL)
                    
                    OPTIONAL MATCH (f)-[:CONTAINS]->(same_callee:Function {name: $callee_func})
                    OPTIONAL MATCH (f)-[:DEPENDS_ON]->(:File)-[:CONTAINS]->(dep_callee:Function {name: $callee_func})
                    OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(repo_callee:Function {name: $callee_func})
                    
                    WITH caller, COALESCE(same_callee, dep_callee, repo_callee) AS chosen_callee
                    WHERE chosen_callee IS NOT NULL
                    WITH caller, head(collect(DISTINCT chosen_callee)) AS target_callee
                    MERGE (caller)-[rel:CALLS]->(target_callee)
                    SET rel.line = COALESCE($line, caller.line, 0)
                    RETURN count(target_callee) as matched
                    """,
                    repo_id=repo_id,
                    from_file=normalized_from,
                    caller_func=caller_func,
                    callee_func=callee_func,
                    caller_class=caller_class,
                    line=line
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
                    WHERE ($caller_class IS NULL OR caller.parent_class = $caller_class OR caller.parent_class IS NULL)
                    
                    OPTIONAL MATCH (f)-[:CONTAINS]->(same_callee:Function {name: $callee_func})
                    OPTIONAL MATCH (f)-[:DEPENDS_ON]->(:File)-[:CONTAINS]->(dep_callee:Function {name: $callee_func})
                    OPTIONAL MATCH (:File)-[:CONTAINS]->(repo_callee:Function {name: $callee_func})
                    
                    WITH caller, COALESCE(same_callee, dep_callee, repo_callee) AS chosen_callee
                    WHERE chosen_callee IS NOT NULL
                    WITH caller, head(collect(DISTINCT chosen_callee)) AS target_callee
                    MERGE (caller)-[rel:CALLS]->(target_callee)
                    SET rel.line = COALESCE($line, caller.line, 0)
                    RETURN count(target_callee) as matched
                    """,
                    from_file=normalized_from,
                    caller_func=caller_func,
                    callee_func=callee_func,
                    caller_class=caller_class,
                    line=line
                )
                record = result.single()
                if record and record['matched'] > 0:
                    logger.debug(f"✓ {caller_func} -> {callee_func}")
    
    @staticmethod
    def _chunks(items: List[Dict], size: int):
        """Yield bounded parameter batches so very large repositories stay safe."""
        for start in range(0, len(items), size):
            yield items[start:start + size]

    def bulk_store_analysis(self, parsed_files: List[Dict], repo_id: str,
                            snapshot_id: str, batch_size: int = None) -> Dict[str, int]:
        """Persist a complete parse with a fixed number of Aura round trips."""
        batch_size = batch_size or self.BULK_BATCH_SIZE
        files, classes, functions, imports = [], [], [], []
        file_calls, function_calls, resolved_method_calls = [], [], []

        for parsed in parsed_files:
            if not parsed or not parsed.get('file'):
                continue
            file_path = self._normalize_path(parsed['file'])
            files.append({
                'path': file_path,
                'path_normalized': file_path.replace('\\', '/'),
                'language': parsed.get('language', 'unknown'),
                'hash': parsed.get('file_hash')
            })
            classes.extend({
                'file': file_path, 'name': item['name'], 'line': item.get('line', 0)
            } for item in parsed.get('classes', []) if item.get('name'))
            method_parents = {
                (item.get('method'), item.get('line')): item.get('class')
                for item in parsed.get('class_methods', [])
            }
            functions.extend({
                'file': file_path,
                'name': item['name'],
                'line': item.get('line', 0),
                'parent_class': method_parents.get(
                    (item['name'], item.get('line', 0))
                )
            } for item in parsed.get('functions', []) if item.get('name'))
            imports.extend({
                'file': file_path, 'module': module
            } for module in set(parsed.get('imports', [])) if module)
            file_calls.extend({
                'file': file_path, 'callee': callee
            } for callee in set(parsed.get('function_calls', [])) if callee)
            function_calls.extend({
                'file': file_path,
                'caller': call.get('caller'),
                'callee': call.get('callee'),
                'caller_class': call.get('caller_class')
            } for call in parsed.get('function_to_function_calls', [])
              if call.get('caller') and call.get('callee'))
            attribute_types = {
                (item.get('class'), item.get('attr')): item.get('type')
                for item in parsed.get('self_attributes', [])
            }
            for call in parsed.get('method_calls', []):
                target_class = attribute_types.get(
                    (call.get('caller_class'), call.get('target_attr'))
                )
                if target_class and call.get('caller_method') and call.get('target_method'):
                    resolved_method_calls.append({
                        'file': file_path,
                        'caller_class': call.get('caller_class'),
                        'caller': call.get('caller_method'),
                        'target_class': target_class,
                        'callee': call.get('target_method')
                    })

        queries = [
            (files, """
                MATCH (r:Repository {repo_id: $repo_id})
                MATCH (s:Snapshot {snapshot_id: $snapshot_id})
                UNWIND $rows AS item
                MERGE (f:File {path: item.path})
                SET f.file_path = item.path,
                    f.language = item.language,
                    f.content_hash = item.hash,
                    f.path_normalized = item.path_normalized
                MERGE (r)-[:CONTAINS]->(f)
                MERGE (s)-[:ANALYZED_FILE]->(f)
            """),
            (classes, """
                UNWIND $rows AS item
                MATCH (f:File {path: item.file})
                MERGE (c:Class {name: item.name, file: item.file})
                SET c.line = item.line
                MERGE (f)-[:CONTAINS]->(c)
            """),
            (functions, """
                UNWIND $rows AS item
                MATCH (f:File {path: item.file})
                MERGE (fn:Function {name: item.name, file: item.file})
                SET fn.line = item.line,
                    fn.parent_class = item.parent_class
                MERGE (f)-[:CONTAINS]->(fn)
            """),
            (imports, """
                UNWIND $rows AS item
                MATCH (f:File {path: item.file})
                MERGE (m:Module {name: item.module})
                MERGE (f)-[:IMPORTS]->(m)
            """),
            (file_calls, """
                MATCH (r:Repository {repo_id: $repo_id})
                UNWIND $rows AS item
                MATCH (r)-[:CONTAINS]->(source:File {path: item.file})
                OPTIONAL MATCH (source)-[:CONTAINS]->(same:Function {name: item.callee})
                OPTIONAL MATCH (source)-[:DEPENDS_ON]->(:File)-[:CONTAINS]->(dep:Function {name: item.callee})
                OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(fallback:Function {name: item.callee})
                WITH source, item,
                     head(collect(DISTINCT same)) AS same_callee,
                     head(collect(DISTINCT dep)) AS dep_callee,
                     head(collect(DISTINCT fallback)) AS repo_callee
                WITH source, COALESCE(same_callee, dep_callee, repo_callee) AS callee
                WHERE callee IS NOT NULL
                MERGE (source)-[:CALLS]->(callee)
            """),
            (function_calls, """
                MATCH (r:Repository {repo_id: $repo_id})
                UNWIND $rows AS item
                MATCH (r)-[:CONTAINS]->(source:File {path: item.file})
                MATCH (source)-[:CONTAINS]->(caller:Function {name: item.caller})
                WHERE item.caller_class IS NULL
                   OR caller.parent_class = item.caller_class
                   OR caller.parent_class IS NULL
                OPTIONAL MATCH (source)-[:CONTAINS]->(same:Function {name: item.callee})
                OPTIONAL MATCH (source)-[:DEPENDS_ON]->(:File)-[:CONTAINS]->(dep:Function {name: item.callee})
                OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(fallback:Function {name: item.callee})
                WITH caller, item,
                     head(collect(DISTINCT same)) AS same_callee,
                     head(collect(DISTINCT dep)) AS dep_callee,
                     head(collect(DISTINCT fallback)) AS repo_callee
                WITH caller, COALESCE(same_callee, dep_callee, repo_callee) AS callee
                WHERE callee IS NOT NULL
                MERGE (caller)-[:CALLS]->(callee)
            """),
            (resolved_method_calls, """
                MATCH (r:Repository {repo_id: $repo_id})
                UNWIND $rows AS item
                MATCH (r)-[:CONTAINS]->(source:File {path: item.file})
                MATCH (source)-[:CONTAINS]->(caller:Function {
                    name: item.caller,
                    parent_class: item.caller_class
                })
                MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(callee:Function {
                    name: item.callee,
                    parent_class: item.target_class
                })
                MERGE (caller)-[:CALLS {resolution: 'oop'}]->(callee)
            """)
        ]

        def write_all(tx):
            for rows, query in queries:
                for chunk in self._chunks(rows, batch_size):
                    tx.run(query, rows=chunk, repo_id=repo_id,
                           snapshot_id=snapshot_id).consume()

        with self.driver.session() as session:
            session.execute_write(write_all)

        return {
            'files': len(files), 'classes': len(classes),
            'functions': len(functions), 'imports': len(imports),
            'file_calls': len(file_calls), 'function_calls': len(function_calls),
            'resolved_method_calls': len(resolved_method_calls)
        }

    def bulk_create_dependencies(self, edges, source: str = None,
                                 repo_id: str = None,
                                 batch_size: int = None) -> int:
        """Create file dependency edges with batched UNWIND queries."""
        batch_size = batch_size or self.BULK_BATCH_SIZE
        rows, seen = [], set()
        for edge_source, edge_target in edges:
            normalized_source = self._normalize_path(edge_source)
            normalized_target = self._normalize_path(edge_target)
            key = (normalized_source, normalized_target)
            if key in seen or normalized_source == normalized_target:
                continue
            seen.add(key)
            rows.append({
                'source': normalized_source,
                'target': normalized_target,
                'source_name': Path(edge_source).name,
                'target_name': Path(edge_target).name,
                'source_tag': source
            })

        scoped_query = """
            MATCH (r:Repository {repo_id: $repo_id})
            UNWIND $rows AS item
            MATCH (r)-[:CONTAINS]->(f1:File)
            WHERE f1.path = item.source OR f1.file_path = item.source
               OR f1.path ENDS WITH '\\\\' + item.source_name
               OR f1.path ENDS WITH '/' + item.source_name
            WITH item, r, f1
            MATCH (r)-[:CONTAINS]->(f2:File)
            WHERE f2.path = item.target OR f2.file_path = item.target
               OR f2.path ENDS WITH '\\\\' + item.target_name
               OR f2.path ENDS WITH '/' + item.target_name
            WITH item, f1, f2
            WHERE f1 <> f2
            MERGE (f1)-[rel:DEPENDS_ON]->(f2)
            FOREACH (_ IN CASE WHEN item.source_tag IS NOT NULL THEN [1] ELSE [] END |
                SET rel.source = item.source_tag
            )
        """
        unscoped_query = scoped_query.replace(
            "MATCH (r:Repository {repo_id: $repo_id})\n", ""
        ).replace("(r)-[:CONTAINS]->", "").replace("WITH item, r, f1", "WITH item, f1")
        query = scoped_query if repo_id else unscoped_query
        with self.driver.session() as session:
            for chunk in self._chunks(rows, batch_size):
                session.run(query, rows=chunk, repo_id=repo_id).consume()
        return len(rows)

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
    
    def get_dependencies(self, file_path: str, repo_id: str = None) -> List[str]:
        normalized = self._normalize_path(file_path)
        suffix = self._get_path_suffix(file_path)
        suffix_fwd = suffix.replace('\\', '/')
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $path OR f.file_path = $path
                       OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                       OR f.path_normalized ENDS WITH $suffix_fwd
                    OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                    OPTIONAL MATCH (r)-[:CONTAINS]->(dep:File)<-[:DEPENDS_ON]-(f)
                    RETURN COLLECT(DISTINCT m.name) + COLLECT(DISTINCT COALESCE(dep.file_path, dep.path)) as dependencies
                    """,
                    repo_id=repo_id,
                    path=normalized,
                    suffix=suffix,
                    suffix_fwd=suffix_fwd
                )
            else:
                result = session.run(
                    """
                    MATCH (f:File)
                    WHERE f.path = $path OR f.file_path = $path
                       OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                       OR f.path_normalized ENDS WITH $suffix_fwd
                    OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                    OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:File)
                    RETURN COLLECT(DISTINCT m.name) + COLLECT(DISTINCT COALESCE(dep.file_path, dep.path)) as dependencies
                    """,
                    path=normalized,
                    suffix=suffix,
                    suffix_fwd=suffix_fwd
                )
            record = result.single()
            return [d for d in record["dependencies"] if d] if record else []
    
    def get_affected_files(self, file_path: str, repo_id: str = None) -> List[str]:
        normalized = self._normalize_path(file_path)
        suffix = self._get_path_suffix(file_path)
        suffix_fwd = suffix.replace('\\', '/')
        with self.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(target:File)
                    WHERE target.path = $path OR target.file_path = $path
                       OR target.path ENDS WITH $suffix OR target.path ENDS WITH $suffix_fwd
                       OR target.path_normalized ENDS WITH $suffix_fwd
                    MATCH (r)-[:CONTAINS]->(f:File)-[:DEPENDS_ON|IMPORTS*1..3]->(target)
                    RETURN DISTINCT COALESCE(f.file_path, f.path) as path
                    """,
                    repo_id=repo_id,
                    path=normalized,
                    suffix=suffix,
                    suffix_fwd=suffix_fwd
                )
            else:
                result = session.run(
                    """
                    MATCH (target:File)
                    WHERE target.path = $path OR target.file_path = $path
                       OR target.path ENDS WITH $suffix OR target.path ENDS WITH $suffix_fwd
                       OR target.path_normalized ENDS WITH $suffix_fwd
                    MATCH (f:File)-[:DEPENDS_ON|IMPORTS*1..3]->(target)
                    RETURN DISTINCT COALESCE(f.file_path, f.path) as path
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
    
    def get_all_files(self, repo_id: str = None) -> List[str]:
        """Get all file paths stored in graph, optionally filtered by repo"""
        with self.driver.session() as session:
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File) 
                    WHERE f.path IS NOT NULL
                    RETURN f.path as path 
                    ORDER BY f.path
                """, repo_id=repo_id)
            else:
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
    
    def find_repo_for_function(self, function_name: str, file_path: str = None) -> Optional[str]:
        """Auto-detect repo_id for a function by name and optional file_path"""
        norm_file = self._normalize_path(file_path) if file_path else None
        suffix_bs = ('\\' + Path(file_path).name) if file_path else ''
        suffix_fs = ('/' + Path(file_path).name) if file_path else ''
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function {name: $name})
                WHERE ($file_path IS NULL 
                       OR f.path = $file_path 
                       OR f.file_path = $file_path 
                       OR f.path ENDS WITH $suffix_bs 
                       OR f.file_path ENDS WITH $suffix_bs
                       OR f.path_normalized ENDS WITH $suffix_fs)
                RETURN r.repo_id as repo_id
                LIMIT 1
                """,
                name=function_name,
                file_path=norm_file,
                suffix_bs=suffix_bs,
                suffix_fs=suffix_fs
            )
            record = result.single()
            return record['repo_id'] if record else None

    def get_function_info(self, function_name: str, repo_id: str = None, file_path: str = None) -> Dict:
        """Get detailed info about a specific function, scoped by repository and file if given"""
        norm_file = self._normalize_path(file_path) if file_path else None
        suffix_bs = ('\\' + Path(file_path).name) if file_path else ''
        suffix_fs = ('/' + Path(file_path).name) if file_path else ''
        
        with self.driver.session() as session:
            # If repo_id not given, try to detect it
            if not repo_id and file_path:
                repo_id = self.find_repo_for_function(function_name, file_path)

            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR f.path = $file_path 
                           OR f.file_path = $file_path 
                           OR f.path ENDS WITH $suffix_bs 
                           OR f.file_path ENDS WITH $suffix_bs
                           OR f.path_normalized ENDS WITH $suffix_fs)
                    RETURN fn.name as name, COALESCE(fn.file, f.file_path, f.path) as file, fn.line as line
                    LIMIT 1
                    """,
                    repo_id=repo_id,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
            else:
                result = session.run(
                    """
                    MATCH (f:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR f.path = $file_path 
                           OR f.file_path = $file_path 
                           OR f.path ENDS WITH $suffix_bs 
                           OR f.file_path ENDS WITH $suffix_bs
                           OR f.path_normalized ENDS WITH $suffix_fs)
                    RETURN fn.name as name, COALESCE(fn.file, f.file_path, f.path) as file, fn.line as line
                    LIMIT 1
                    """,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
            record = result.single()
            return dict(record) if record else None

    def get_function_callers(self, function_name: str, repo_id: str = None, file_path: str = None) -> List[Dict]:
        """Get all files and functions that call this function"""
        norm_file = self._normalize_path(file_path) if file_path else None
        suffix_bs = ('\\' + Path(file_path).name) if file_path else ''
        suffix_fs = ('/' + Path(file_path).name) if file_path else ''

        # Auto-detect repo_id if missing but file_path exists in a known repo
        if not repo_id and file_path:
            repo_id = self.find_repo_for_function(function_name, file_path)

        with self.driver.session() as session:
            func_callers = []
            file_callers = []

            if repo_id:
                # 1. Function-to-function callers within repository
                func_result = session.run(
                    """
                    MATCH (callee_file:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR callee_file.path = $file_path 
                           OR callee_file.file_path = $file_path 
                           OR callee_file.path ENDS WITH $suffix_bs 
                           OR callee_file.file_path ENDS WITH $suffix_bs
                           OR callee_file.path_normalized ENDS WITH $suffix_fs)
                      AND EXISTS { MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(callee_file) }
                    MATCH (caller_file:File)-[:CONTAINS]->(caller:Function)-[rel:CALLS]->(fn)
                    WHERE EXISTS { MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(caller_file) }
                    RETURN DISTINCT 
                        COALESCE(caller_file.file_path, caller_file.path) as file, 
                        caller.name as caller_name, 
                        COALESCE(rel.line, caller.line, 0) as line
                    """,
                    repo_id=repo_id,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
                )
                func_callers = [dict(record) for record in func_result]

                # 2. File-to-function callers within repository
                file_result = session.run(
                    """
                    MATCH (callee_file:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR callee_file.path = $file_path 
                           OR callee_file.file_path = $file_path 
                           OR callee_file.path ENDS WITH $suffix_bs 
                           OR callee_file.file_path ENDS WITH $suffix_bs
                           OR callee_file.path_normalized ENDS WITH $suffix_fs)
                      AND EXISTS { MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(callee_file) }
                    MATCH (caller_file:File)-[rel:CALLS]->(fn)
                    WHERE EXISTS { MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(caller_file) }
                    RETURN DISTINCT 
                        COALESCE(caller_file.file_path, caller_file.path) as file,
                        COALESCE(rel.line, 0) as line
                    """,
                    repo_id=repo_id,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
                file_callers = [dict(record) for record in file_result]

            # Fallback if no callers found with repo_id filter or if repo_id wasn't provided:
            if not func_callers and not file_callers:
                func_result = session.run(
                    """
                    MATCH (callee_file:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR callee_file.path = $file_path 
                           OR callee_file.file_path = $file_path 
                           OR callee_file.path ENDS WITH $suffix_bs 
                           OR callee_file.file_path ENDS WITH $suffix_bs
                           OR callee_file.path_normalized ENDS WITH $suffix_fs)
                    MATCH (caller_file:File)-[:CONTAINS]->(caller:Function)-[rel:CALLS]->(fn)
                    RETURN DISTINCT 
                        COALESCE(caller_file.file_path, caller_file.path) as file, 
                        caller.name as caller_name, 
                        COALESCE(rel.line, caller.line, 0) as line
                    """,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
                func_callers = [dict(record) for record in func_result]

                file_result = session.run(
                    """
                    MATCH (callee_file:File)-[:CONTAINS]->(fn:Function {name: $name})
                    WHERE ($file_path IS NULL 
                           OR callee_file.path = $file_path 
                           OR callee_file.file_path = $file_path 
                           OR callee_file.path ENDS WITH $suffix_bs 
                           OR callee_file.file_path ENDS WITH $suffix_bs
                           OR callee_file.path_normalized ENDS WITH $suffix_fs)
                    MATCH (caller_file:File)-[rel:CALLS]->(fn)
                    RETURN DISTINCT 
                        COALESCE(caller_file.file_path, caller_file.path) as file,
                        COALESCE(rel.line, 0) as line
                    """,
                    name=function_name,
                    file_path=norm_file,
                    suffix_bs=suffix_bs,
                    suffix_fs=suffix_fs
                )
                file_callers = [dict(record) for record in file_result]

            # Merge results: function-level callers are prioritized
            seen_entries = set()
            merged = []
            for fc in func_callers:
                f_path = fc.get('file') or ''
                c_name = fc.get('caller_name') or ''
                key = (f_path, c_name)
                if key not in seen_entries:
                    seen_entries.add(key)
                    merged.append(fc)

            for fc in file_callers:
                file_key = fc.get('file') or ''
                if not any(m.get('file') == file_key for m in merged):
                    fc['caller_name'] = f"(module) {Path(file_key).name if file_key else 'unknown'}"
                    merged.append(fc)

            return merged
    
    def get_graph_data(self, repo_id: str = None) -> Dict:
        """Get nodes and edges for graph visualization"""
        with self.driver.session() as session:
            # Get file nodes and their relationships
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[rel:DEPENDS_ON]->(target:File)
                    WHERE (r)-[:CONTAINS]->(target)
                    WITH f, COLLECT(DISTINCT {target: COALESCE(target.file_path, target.path), type: type(rel)}) as relationships
                    RETURN COALESCE(f.file_path, f.path) as id, 
                           COALESCE(f.file_path, f.path) as label, 
                           relationships
                    """,
                    repo_id=repo_id
                )
            else:
                result = session.run(
                    """
                    MATCH (f:File)
                    OPTIONAL MATCH (f)-[rel:DEPENDS_ON]->(target:File)
                    WITH f, COLLECT(DISTINCT {target: COALESCE(target.file_path, target.path), type: type(rel)}) as relationships
                    RETURN COALESCE(f.file_path, f.path) as id, 
                           COALESCE(f.file_path, f.path) as label, 
                           relationships
                    """
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
                        'label': label,
                        'type': 'file'
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
                                'label': label,
                                'type': 'file'
                            })
                            seen_nodes.add(target_id)
                        
                        edges.append({
                            'source': node_id,
                            'target': target_id,
                            'type': 'imports'
                        })
            
            return {'nodes': nodes, 'edges': edges}

    def get_code_health_candidates(self, repo_id: str) -> Dict:
        """Return static-analysis candidates that deserve a manual redundancy review.

        An absent graph edge is evidence, not proof: framework entry points, reflection,
        configuration files, and dynamically dispatched functions can appear unused.
        The API therefore uses candidate language and includes confidence per item.
        """
        if not repo_id:
            return {
                'summary': {'files': 0, 'functions': 0, 'duplicate_files': 0, 'duplicate_groups': 0},
                'file_candidates': [],
                'function_candidates': [],
                'duplicate_file_groups': [],
                'duplicate_function_groups': [],
                'caveat': 'Select a repository before running the code-health review.'
            }

        with self.driver.session() as session:
            file_rows = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (r)-[:CONTAINS]->(incoming:File)-[:DEPENDS_ON]->(f)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(outgoing:File)<-[:CONTAINS]-(r)
                WITH f, count(DISTINCT incoming) AS fan_in, count(DISTINCT outgoing) AS fan_out
                WHERE fan_in = 0
                RETURN COALESCE(f.file_path, f.path) AS file, fan_in, fan_out
                ORDER BY fan_out ASC, file
                LIMIT 250
                """,
                repo_id=repo_id
            )

            function_rows = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(caller_fn:Function)-[:CALLS]->(fn)
                OPTIONAL MATCH (r)-[:CONTAINS]->(caller_file:File)-[:CALLS]->(fn)
                WITH f, fn, count(DISTINCT caller_fn) + count(DISTINCT caller_file) AS caller_count
                WHERE caller_count = 0
                RETURN fn.name AS name, COALESCE(fn.file, f.file_path, f.path) AS file,
                       fn.line AS line, caller_count
                ORDER BY file, line
                LIMIT 500
                """,
                repo_id=repo_id
            )

            duplicate_rows = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                WITH fn.name AS name,
                     collect(DISTINCT {file: COALESCE(fn.file, f.file_path, f.path), line: fn.line}) AS occurrences
                WHERE size(occurrences) > 1
                RETURN name, occurrences
                ORDER BY size(occurrences) DESC, name
                LIMIT 100
                """,
                repo_id=repo_id
            )

            duplicate_file_rows = session.run(
                """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE f.content_hash IS NOT NULL AND f.content_hash <> ''
                WITH f.content_hash AS content_hash,
                     collect(DISTINCT COALESCE(f.file_path, f.path)) AS files
                WHERE size(files) > 1
                RETURN content_hash, files
                ORDER BY size(files) DESC
                LIMIT 100
                """,
                repo_id=repo_id
            )

            file_candidates = []
            for row in file_rows:
                path = row['file']
                if not path:
                    continue
                isolated = row['fan_out'] == 0
                file_candidates.append({
                    'file': path,
                    'fan_in': row['fan_in'],
                    'fan_out': row['fan_out'],
                    'kind': 'isolated' if isolated else 'unreferenced',
                    'confidence': 0.72 if isolated else 0.52,
                    'reason': (
                        'No internal file imports this file, and it has no internal dependencies.'
                        if isolated else
                        'No internal file imports this file; it may be an entry point or dead module.'
                    )
                })

            lifecycle_names = {
                'main', 'run', 'start', 'setup', 'teardown', 'setUp', 'tearDown',
                'render', 'register', 'configure', 'initialize', 'init'
            }
            function_candidates = []
            for row in function_rows:
                name = row['name'] or ''
                if not name or name.startswith('__') or name.startswith('test') or name in lifecycle_names:
                    continue
                dynamic_shape = name.startswith(('on_', 'handle_', 'get_', 'post_', 'put_', 'delete_'))
                function_candidates.append({
                    'name': name,
                    'file': row['file'],
                    'line': row['line'],
                    'confidence': 0.46 if dynamic_shape else 0.66,
                    'reason': 'No statically resolved file or function call reaches this function.'
                })
                if len(function_candidates) >= 250:
                    break

            duplicate_groups = [dict(row) for row in duplicate_rows]
            duplicate_file_groups = [dict(row) for row in duplicate_file_rows]

        return {
            'summary': {
                'files': len(file_candidates),
                'functions': len(function_candidates),
                'duplicate_files': len(duplicate_file_groups),
                'duplicate_groups': len(duplicate_groups)
            },
            'file_candidates': file_candidates,
            'function_candidates': function_candidates,
            'duplicate_file_groups': duplicate_file_groups,
            'duplicate_function_groups': duplicate_groups,
            'caveat': (
                'These are review candidates from static dependency and call edges. '
                'Framework routes, reflection, configuration entry points, and dynamic calls can create false positives.'
            )
        }
    
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
    
    def resolve_file_path(self, file_path: str, repo_id: str = None) -> str:
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
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE f.path = $path OR f.file_path = $path
                       OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                       OR f.path_normalized ENDS WITH $suffix_fwd
                       OR f.path ENDS WITH '\\\\' + $filename
                       OR f.path ENDS WITH '/' + $filename
                    RETURN COALESCE(f.file_path, f.path) as resolved_path
                    LIMIT 1
                """, repo_id=repo_id, path=file_path, suffix=suffix, suffix_fwd=suffix_fwd, filename=filename)
            else:
                result = session.run("""
                    MATCH (f:File)
                    WHERE f.path = $path OR f.file_path = $path
                       OR f.path ENDS WITH $suffix OR f.path ENDS WITH $suffix_fwd
                       OR f.path_normalized ENDS WITH $suffix_fwd
                       OR f.path ENDS WITH '\\\\' + $filename
                       OR f.path ENDS WITH '/' + $filename
                    RETURN COALESCE(f.file_path, f.path) as resolved_path
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
