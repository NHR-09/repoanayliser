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
    
    def create_file_node(self, file_path: str, language: str):
        with self.driver.session() as session:
            session.run(
                "MERGE (f:File {path: $path}) SET f.language = $language",
                path=file_path, language=language
            )
    
    def create_class_node(self, file_path: str, class_name: str, line: int):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File {path: $file_path})
                MERGE (c:Class {name: $name, file: $file_path})
                SET c.line = $line
                MERGE (f)-[:CONTAINS]->(c)
                """,
                file_path=file_path, name=class_name, line=line
            )
    
    def create_function_node(self, file_path: str, func_name: str, line: int):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File {path: $file_path})
                MERGE (fn:Function {name: $name, file: $file_path})
                SET fn.line = $line
                MERGE (f)-[:CONTAINS]->(fn)
                """,
                file_path=file_path, name=func_name, line=line
            )
    
    def create_import_relationship(self, from_file: str, to_module: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File {path: $from_file})
                MERGE (m:Module {name: $to_module})
                MERGE (f)-[:IMPORTS]->(m)
                """,
                from_file=from_file, to_module=to_module
            )
            
            module_parts = to_module.replace('.', '\\\\')
            module_name = to_module.split('.')[-1]
            
            session.run(
                """
                MATCH (f:File {path: $from_file})
                MATCH (target:File)
                WHERE target.path ENDS WITH $module_parts + '.py' 
                   OR target.path ENDS WITH $module_parts + '.js'
                   OR target.path ENDS WITH '\\\\' + $module_name + '.py'
                   OR target.path ENDS WITH '\\\\' + $module_name + '.js'
                MERGE (f)-[:DEPENDS_ON]->(target)
                """,
                from_file=from_file, 
                module_parts=module_parts,
                module_name=module_name
            )
    
    def create_function_call(self, from_file: str, called_function: str):
        """Create CALLS relationship between file and function"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File {path: $from_file})
                MATCH (fn:Function {name: $called_function})
                MERGE (f)-[:CALLS]->(fn)
                """,
                from_file=from_file,
                called_function=called_function
            )
    
    def get_dependencies(self, file_path: str) -> List[str]:
        normalized = self._normalize_path(file_path)
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (f:File)
                WHERE f.path = $path OR f.path ENDS WITH $suffix
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:File)
                RETURN COLLECT(DISTINCT m.name) + COLLECT(DISTINCT dep.path) as dependencies
                """,
                path=normalized,
                suffix=self._get_path_suffix(file_path)
            )
            record = result.single()
            return [d for d in record["dependencies"] if d] if record else []
    
    def get_affected_files(self, file_path: str) -> List[str]:
        normalized = self._normalize_path(file_path)
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (target:File)
                WHERE target.path = $path OR target.path ENDS WITH $suffix
                MATCH (f:File)-[:DEPENDS_ON|IMPORTS*1..3]->(target)
                RETURN DISTINCT f.path as path
                """,
                path=normalized,
                suffix=self._get_path_suffix(file_path)
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
            result = session.run("MATCH (f:File) RETURN f.path as path ORDER BY f.path")
            return [record["path"] for record in result]
    
    def get_all_functions(self) -> List[Dict]:
        """Get all functions with their file and line info"""
        with self.driver.session() as session:
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
    
    def get_function_callers(self, function_name: str) -> List[Dict]:
        """Get all functions/files that call this function"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (target:Function {name: $name})
                MATCH (f:File)-[:CALLS]->(target)
                RETURN 'file' as caller_name, f.path as caller_file, 0 as line
                """,
                name=function_name
            )
            return [dict(record) for record in result]
    
    def get_graph_data(self, limit: int = 50) -> Dict:
        """Get nodes and edges for graph visualization"""
        with self.driver.session() as session:
            # Get file nodes and their relationships
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
            return str(Path(path).resolve())
        except:
            return path
    
    def _get_path_suffix(self, path: str) -> str:
        """Get path suffix for flexible matching"""
        parts = Path(path).parts
        if len(parts) >= 3:
            return str(Path(*parts[-3:]))
        return str(Path(path).name)
