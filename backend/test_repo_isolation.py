"""Test repository isolation - shows the actual problem"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB
from graph.function_graph import FunctionGraphBuilder

def test_isolation():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    function_graph = FunctionGraphBuilder(graph_db)
    
    print("=" * 80)
    print("TESTING: Do queries properly filter by repo_id?")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get all repos
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        print(f"\nTotal repositories in DB: {len(repos)}")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
        
        if not repos:
            print("\n[ERROR] No repositories found!")
            return
        
        repo_id = repos[0]['id']
        repo_name = repos[0]['name']
        
        print(f"\n{'=' * 80}")
        print(f"TEST 1: Query WITH repo_id filter")
        print(f"{'=' * 80}")
        
        # Query WITH repo_id (what function_graph does)
        result_with_filter = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(file:File)-[:CONTAINS]->(fn:Function)
            OPTIONAL MATCH (caller_file:File)-[:CALLS]->(fn)
            WHERE (r)-[:CONTAINS]->(caller_file)
            RETURN fn.name as func, file.file_path as file, caller_file.file_path as caller
            LIMIT 10
        """, repo_id=repo_id).data()
        
        print(f"\nResults: {len(result_with_filter)} records")
        for r in result_with_filter[:5]:
            print(f"  Function: {r['func']} in {r['file']}")
            print(f"    Caller: {r['caller']}")
        
        print(f"\n{'=' * 80}")
        print(f"TEST 2: Check if caller files belong to same repo")
        print(f"{'=' * 80}")
        
        # For each caller, verify it belongs to the repo
        for r in result_with_filter:
            if r['caller']:
                check = session.run("""
                    MATCH (r:Repository)-[:CONTAINS]->(f:File {file_path: $file_path})
                    RETURN r.repo_id as repo_id, r.name as repo_name
                """, file_path=r['caller']).data()
                
                if check:
                    caller_repo = check[0]['repo_id']
                    if caller_repo != repo_id:
                        print(f"  [FAIL] Caller {r['caller']} belongs to {check[0]['repo_name']} (not {repo_name})")
                    else:
                        print(f"  [OK] Caller {r['caller']} belongs to {repo_name}")
        
        print(f"\n{'=' * 80}")
        print(f"TEST 3: function_graph.get_function_graph_data()")
        print(f"{'=' * 80}")
        
        graph_data = function_graph.get_function_graph_data(repo_id=repo_id, limit=20)
        print(f"\nNodes: {len(graph_data['nodes'])}")
        print(f"Edges: {len(graph_data['edges'])}")
        
        # Check each function node
        contamination_found = False
        for node in graph_data['nodes']:
            if node['type'] == 'function':
                check = session.run("""
                    MATCH (r:Repository)-[:CONTAINS]->(f:File)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                    RETURN r.repo_id as repo_id, r.name as repo_name
                """, file_path=node['file']).data()
                
                if check:
                    node_repo = check[0]['repo_id']
                    if node_repo != repo_id:
                        print(f"  [FAIL] Function {node['label']} from {check[0]['repo_name']} (expected {repo_name})")
                        contamination_found = True
        
        if not contamination_found:
            print("  [OK] All functions belong to correct repository")
        
        print(f"\n{'=' * 80}")
        print("TEST COMPLETE")
        print(f"{'=' * 80}")

if __name__ == "__main__":
    test_isolation()
