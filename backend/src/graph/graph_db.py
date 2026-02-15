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
