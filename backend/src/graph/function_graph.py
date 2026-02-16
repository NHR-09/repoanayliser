from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class FunctionGraphBuilder:
    def __init__(self, graph_db):
        self.graph_db = graph_db
    
    def get_function_graph_data(self, repo_id: str = None, limit: int = 100) -> Dict:
        """Get function nodes and call relationships for visualization"""
        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(file:File)-[:CONTAINS]->(fn:Function)
                    OPTIONAL MATCH (caller_file:File)-[:CALLS]->(fn)
                    WHERE (r)-[:CONTAINS]->(caller_file)
                    OPTIONAL MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(caller_fn:Function)-[:CALLS]->(fn)
                    WITH fn, file, COLLECT(DISTINCT caller_file) as caller_files, COLLECT(DISTINCT caller_fn) as caller_functions
                    RETURN fn.name as name, 
                           COALESCE(file.path, file.file_path) as file, 
                           fn.line as line,
                           [cf IN caller_files WHERE cf IS NOT NULL | COALESCE(cf.path, cf.file_path)] as file_callers,
                           [cfn IN caller_functions WHERE cfn IS NOT NULL | {name: cfn.name, file: COALESCE(cfn.file, 'unknown')}] as function_callers
                    LIMIT $limit
                    """,
                    repo_id=repo_id,
                    limit=limit
                )
            else:
                result = session.run(
                    """
                    MATCH (file:File)-[:CONTAINS]->(fn:Function)
                    OPTIONAL MATCH (caller_file:File)-[:CALLS]->(fn)
                    OPTIONAL MATCH (:File)-[:CONTAINS]->(caller_fn:Function)-[:CALLS]->(fn)
                    WITH fn, file, COLLECT(DISTINCT caller_file) as caller_files, COLLECT(DISTINCT caller_fn) as caller_functions
                    RETURN fn.name as name, 
                           COALESCE(file.path, file.file_path) as file, 
                           fn.line as line,
                           [cf IN caller_files WHERE cf IS NOT NULL | COALESCE(cf.path, cf.file_path)] as file_callers,
                           [cfn IN caller_functions WHERE cfn IS NOT NULL | {name: cfn.name, file: COALESCE(cfn.file, 'unknown')}] as function_callers
                    LIMIT $limit
                    """,
                    limit=limit
                )
            
            nodes = []
            edges = []
            seen_nodes = set()
            
            for record in result:
                func_name = record['name']
                file_path = record['file']
                
                # Skip if function has no file (orphaned)
                if not func_name or not file_path:
                    logger.warning(f"Skipping orphaned function: {func_name} (no file)")
                    continue
                
                node_id = f"{file_path}::{func_name}"
                
                if node_id not in seen_nodes:
                    nodes.append({
                        'id': node_id,
                        'label': func_name,
                        'file': file_path,
                        'line': record['line'],
                        'type': 'function'
                    })
                    seen_nodes.add(node_id)
                
                # File-to-function calls
                for caller_file in record['file_callers']:
                    if caller_file:
                        caller_id = caller_file
                        if caller_id not in seen_nodes:
                            file_label = caller_file.replace('\\', '/').split('/')[-1]
                            nodes.append({
                                'id': caller_id,
                                'label': file_label,
                                'file': caller_file,
                                'type': 'file'
                            })
                            seen_nodes.add(caller_id)
                        
                        edges.append({
                            'source': caller_id,
                            'target': node_id,
                            'type': 'calls'
                        })
                
                # Function-to-function calls
                for caller_fn in record['function_callers']:
                    if caller_fn and caller_fn.get('name') and caller_fn.get('file'):
                        caller_id = f"{caller_fn['file']}::{caller_fn['name']}"
                        if caller_id not in seen_nodes:
                            nodes.append({
                                'id': caller_id,
                                'label': caller_fn['name'],
                                'file': caller_fn['file'],
                                'type': 'function'
                            })
                            seen_nodes.add(caller_id)
                        
                        edges.append({
                            'source': caller_id,
                            'target': node_id,
                            'type': 'calls'
                        })
            
            return {'nodes': nodes, 'edges': edges}
    
    def get_function_call_chain(self, function_name: str, repo_id: str = None, depth: int = 3) -> Dict:
        """Get call chain for a specific function"""
        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(file:File)-[:CONTAINS]->(target:Function {name: $name})
                    OPTIONAL MATCH (r)-[:CONTAINS]->(caller:File)-[:CALLS]->(target)
                    WITH target, file, COLLECT(DISTINCT caller) as callers
                    RETURN target.name as name, 
                           COALESCE(file.path, file.file_path) as file,
                           [c IN callers WHERE c IS NOT NULL | COALESCE(c.path, c.file_path)] as caller_paths
                    """,
                    repo_id=repo_id,
                    name=function_name
                )
            else:
                result = session.run(
                    """
                    MATCH (file:File)-[:CONTAINS]->(target:Function {name: $name})
                    OPTIONAL MATCH (caller:File)-[:CALLS]->(target)
                    WITH target, file, COLLECT(DISTINCT caller) as callers
                    RETURN target.name as name, 
                           COALESCE(file.path, file.file_path) as file,
                           [c IN callers WHERE c IS NOT NULL | COALESCE(c.path, c.file_path)] as caller_paths
                    """,
                    name=function_name
                )
            
            record = result.single()
            if not record or not record['file']:
                return {'nodes': [], 'edges': []}
            
            nodes = []
            edges = []
            seen = set()
            
            func_id = f"{record['file']}::{record['name']}"
            nodes.append({
                'id': func_id,
                'label': record['name'],
                'file': record['file'],
                'type': 'function'
            })
            seen.add(func_id)
            
            for caller_path in record['caller_paths']:
                if caller_path:
                    if caller_path not in seen:
                        file_label = caller_path.replace('\\', '/').split('/')[-1]
                        nodes.append({
                            'id': caller_path,
                            'label': file_label,
                            'file': caller_path,
                            'type': 'file'
                        })
                        seen.add(caller_path)
                    
                    edges.append({
                        'source': caller_path,
                        'target': func_id,
                        'type': 'calls'
                    })
            
            return {'nodes': nodes, 'edges': edges}
