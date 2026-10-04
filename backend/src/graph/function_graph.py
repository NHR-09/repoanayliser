from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class FunctionGraphBuilder:
    def __init__(self, graph_db):
        self.graph_db = graph_db
    
    def get_function_graph_data(self, repo_id: str = None) -> Dict:
        """Get function nodes and call relationships for visualization"""
        with self.graph_db.driver.session() as session:
            # 1. Fetch all functions in the repository/database
            if repo_id:
                func_records = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                    RETURN fn.name as name, 
                           COALESCE(f.path, f.file_path) as file, 
                           fn.line as line,
                           fn.parent_class as parent_class
                    """,
                    repo_id=repo_id
                )
            else:
                func_records = session.run(
                    """
                    MATCH (f:File)-[:CONTAINS]->(fn:Function)
                    RETURN fn.name as name, 
                           COALESCE(f.path, f.file_path) as file, 
                           fn.line as line,
                           fn.parent_class as parent_class
                    """
                )
            
            nodes = []
            seen_nodes = set()
            for r in func_records:
                name = r['name']
                file_path = r['file']
                if not name or not file_path:
                    continue
                node_id = f"{file_path}::{name}"
                if node_id not in seen_nodes:
                    nodes.append({
                        'id': node_id,
                        'label': name,
                        'file': file_path,
                        'line': r['line'],
                        'parent_class': r['parent_class'],
                        'type': 'function'
                    })
                    seen_nodes.add(node_id)
            
            # 2. Fetch all function-to-function calls
            if repo_id:
                call_records = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f1:File)-[:CONTAINS]->(caller:Function)
                    MATCH (caller)-[:CALLS]->(callee:Function)
                    MATCH (r)-[:CONTAINS]->(f2:File)-[:CONTAINS]->(callee)
                    RETURN caller.name as caller_name,
                           COALESCE(f1.path, f1.file_path) as caller_file,
                           callee.name as callee_name,
                           COALESCE(f2.path, f2.file_path) as callee_file
                    """,
                    repo_id=repo_id
                )
            else:
                call_records = session.run(
                    """
                    MATCH (f1:File)-[:CONTAINS]->(caller:Function)
                    MATCH (caller)-[:CALLS]->(callee:Function)
                    MATCH (f2:File)-[:CONTAINS]->(callee)
                    RETURN caller.name as caller_name,
                           COALESCE(f1.path, f1.file_path) as caller_file,
                           callee.name as callee_name,
                           COALESCE(f2.path, f2.file_path) as callee_file
                    """
                )
            
            edges = []
            seen_edges = set()
            for r in call_records:
                caller_id = f"{r['caller_file']}::{r['caller_name']}"
                callee_id = f"{r['callee_file']}::{r['callee_name']}"
                
                # Ensure both nodes exist
                if caller_id in seen_nodes and callee_id in seen_nodes:
                    edge_key = (caller_id, callee_id)
                    if edge_key not in seen_edges:
                        edges.append({
                            'source': caller_id,
                            'target': callee_id,
                            'type': 'calls'
                        })
                        seen_edges.add(edge_key)

            # 3. Optional fallback: If a function has no caller function and is called directly by a script file
            if repo_id:
                file_call_records = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(caller_file:File)-[:CALLS]->(callee:Function)
                    MATCH (r)-[:CONTAINS]->(target_file:File)-[:CONTAINS]->(callee)
                    WHERE NOT ()-[:CALLS]->(callee)
                    RETURN COALESCE(caller_file.path, caller_file.file_path) as caller_file,
                           callee.name as callee_name,
                           COALESCE(target_file.path, target_file.file_path) as target_file
                    """,
                    repo_id=repo_id
                )
            else:
                file_call_records = session.run(
                    """
                    MATCH (caller_file:File)-[:CALLS]->(callee:Function)
                    MATCH (target_file:File)-[:CONTAINS]->(callee)
                    WHERE NOT ()-[:CALLS]->(callee)
                    RETURN COALESCE(caller_file.path, caller_file.file_path) as caller_file,
                           callee.name as callee_name,
                           COALESCE(target_file.path, target_file.file_path) as target_file
                    """
                )
            
            for r in file_call_records:
                caller_path = r['caller_file']
                callee_id = f"{r['target_file']}::{r['callee_name']}"
                if caller_path and callee_id in seen_nodes:
                    if caller_path not in seen_nodes:
                        file_label = caller_path.replace('\\', '/').split('/')[-1]
                        nodes.append({
                            'id': caller_path,
                            'label': file_label,
                            'file': caller_path,
                            'type': 'file'
                        })
                        seen_nodes.add(caller_path)
                    edge_key = (caller_path, callee_id)
                    if edge_key not in seen_edges:
                        edges.append({
                            'source': caller_path,
                            'target': callee_id,
                            'type': 'calls'
                        })
                        seen_edges.add(edge_key)

            return {'nodes': nodes, 'edges': edges}
    
    def get_function_call_chain(self, function_name: str, repo_id: str = None, depth: int = 3) -> Dict:
        """Get call chain for a specific function up to depth hops (both callers and callees)."""
        with self.graph_db.driver.session() as session:
            # First find the target function and its file
            if repo_id:
                target_rec = session.run(
                    """
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function {name: $name})
                    RETURN fn.name as name, COALESCE(f.path, f.file_path) as file, fn.line as line
                    LIMIT 1
                    """,
                    repo_id=repo_id, name=function_name
                ).single()
            else:
                target_rec = session.run(
                    """
                    MATCH (f:File)-[:CONTAINS]->(fn:Function {name: $name})
                    RETURN fn.name as name, COALESCE(f.path, f.file_path) as file, fn.line as line
                    LIMIT 1
                    """,
                    name=function_name
                ).single()
            
            if not target_rec or not target_rec['file']:
                return {'nodes': [], 'edges': []}
            
            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()

            target_id = f"{target_rec['file']}::{target_rec['name']}"
            nodes.append({
                'id': target_id,
                'label': target_rec['name'],
                'file': target_rec['file'],
                'line': target_rec['line'],
                'type': 'function'
            })
            seen_nodes.add(target_id)

            # Query all paths of depth 1..depth incoming and outgoing
            if repo_id:
                chain_query = f"""
                MATCH (r:Repository {{repo_id: $repo_id}})-[:CONTAINS]->(tf:File)-[:CONTAINS]->(target:Function {{name: $name}})
                OPTIONAL MATCH p_out = (target)-[:CALLS*1..{depth}]->(out_f:Function)
                WHERE ALL(n IN nodes(p_out) WHERE (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(n))
                OPTIONAL MATCH p_in = (in_f:Function)-[:CALLS*1..{depth}]->(target)
                WHERE ALL(n IN nodes(p_in) WHERE (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(n))
                WITH [p IN (collect(DISTINCT p_out) + collect(DISTINCT p_in)) WHERE p IS NOT NULL] AS paths
                UNWIND paths AS p
                UNWIND relationships(p) AS rel
                WITH DISTINCT rel
                MATCH (r:Repository {{repo_id: $repo_id}})-[:CONTAINS]->(f1:File)-[:CONTAINS]->(caller:Function) WHERE id(caller) = id(startNode(rel))
                MATCH (r)-[:CONTAINS]->(f2:File)-[:CONTAINS]->(callee:Function) WHERE id(callee) = id(endNode(rel))
                RETURN caller.name as caller_name, COALESCE(f1.path, f1.file_path) as caller_file, caller.line as caller_line,
                       callee.name as callee_name, COALESCE(f2.path, f2.file_path) as callee_file, callee.line as callee_line
                """
                rels = session.run(chain_query, repo_id=repo_id, name=function_name)
            else:
                chain_query = f"""
                MATCH (tf:File)-[:CONTAINS]->(target:Function {{name: $name}})
                OPTIONAL MATCH p_out = (target)-[:CALLS*1..{depth}]->(out_f:Function)
                OPTIONAL MATCH p_in = (in_f:Function)-[:CALLS*1..{depth}]->(target)
                WITH [p IN (collect(DISTINCT p_out) + collect(DISTINCT p_in)) WHERE p IS NOT NULL] AS paths
                UNWIND paths AS p
                UNWIND relationships(p) AS rel
                WITH DISTINCT rel
                MATCH (f1:File)-[:CONTAINS]->(caller:Function) WHERE id(caller) = id(startNode(rel))
                MATCH (f2:File)-[:CONTAINS]->(callee:Function) WHERE id(callee) = id(endNode(rel))
                RETURN caller.name as caller_name, COALESCE(f1.path, f1.file_path) as caller_file, caller.line as caller_line,
                       callee.name as callee_name, COALESCE(f2.path, f2.file_path) as callee_file, callee.line as callee_line
                """
                rels = session.run(chain_query, name=function_name)
            
            for r in rels:
                c_id = f"{r['caller_file']}::{r['caller_name']}"
                ce_id = f"{r['callee_file']}::{r['callee_name']}"

                if c_id not in seen_nodes:
                    nodes.append({
                        'id': c_id,
                        'label': r['caller_name'],
                        'file': r['caller_file'],
                        'line': r['caller_line'],
                        'type': 'function'
                    })
                    seen_nodes.add(c_id)

                if ce_id not in seen_nodes:
                    nodes.append({
                        'id': ce_id,
                        'label': r['callee_name'],
                        'file': r['callee_file'],
                        'line': r['callee_line'],
                        'type': 'function'
                    })
                    seen_nodes.add(ce_id)

                edge_key = (c_id, ce_id)
                if edge_key not in seen_edges:
                    edges.append({
                        'source': c_id,
                        'target': ce_id,
                        'type': 'calls'
                    })
                    seen_edges.add(edge_key)

            return {'nodes': nodes, 'edges': edges}
