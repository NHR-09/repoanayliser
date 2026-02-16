"""Test file graph and function graph for repo isolation"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB

def test_graph_isolation():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("TEST: File Graph and Function Graph Isolation")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get all repos
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        print(f"\nRepositories: {len(repos)}")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
        
        if not repos:
            print("\n[ERROR] No repositories!")
            return
        
        repo_id = repos[0]['id']
        repo_name = repos[0]['name']
        
        # Count total files and functions
        total_files = session.run("MATCH (f:File) RETURN count(f) as count").single()['count']
        total_funcs = session.run("MATCH (fn:Function) RETURN count(fn) as count").single()['count']
        
        print(f"\n[TOTALS]")
        print(f"  Total Files in DB: {total_files}")
        print(f"  Total Functions in DB: {total_funcs}")
        
        # Count for current repo
        repo_files = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            RETURN count(f) as count
        """, repo_id=repo_id).single()['count']
        
        repo_funcs = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
            RETURN count(fn) as count
        """, repo_id=repo_id).single()['count']
        
        print(f"\n[REPO: {repo_name}]")
        print(f"  Files: {repo_files}")
        print(f"  Functions: {repo_funcs}")
        
        # TEST 1: File Graph (get_graph_data)
        print(f"\n{'=' * 80}")
        print("TEST 1: File Graph (get_graph_data)")
        print(f"{'=' * 80}")
        
        graph_data = graph_db.get_graph_data(limit=100)
        print(f"\nFile graph nodes: {len(graph_data['nodes'])}")
        print(f"File graph edges: {len(graph_data['edges'])}")
        
        # Check if nodes belong to current repo
        contamination = []
        for node in graph_data['nodes'][:20]:
            check = session.run("""
                MATCH (r:Repository)-[:CONTAINS]->(f:File)
                WHERE f.file_path = $file_path OR f.path = $file_path
                RETURN r.repo_id as repo_id, r.name as repo_name
            """, file_path=node['id']).data()
            
            if check:
                node_repo = check[0]['repo_id']
                if node_repo != repo_id:
                    contamination.append(f"{node['label']} from {check[0]['repo_name']}")
        
        if contamination:
            print(f"\n[FAIL] File graph has cross-repo contamination:")
            for c in contamination[:5]:
                print(f"  - {c}")
        else:
            print(f"[OK] File graph properly filtered")
        
        # TEST 2: Function Graph
        print(f"\n{'=' * 80}")
        print("TEST 2: Function Graph (get_function_graph_data)")
        print(f"{'=' * 80}")
        
        from graph.function_graph import FunctionGraphBuilder
        builder = FunctionGraphBuilder(graph_db)
        
        # Without repo_id
        func_graph_all = builder.get_function_graph_data(repo_id=None, limit=100)
        print(f"\nFunction graph (no filter):")
        print(f"  Nodes: {len(func_graph_all['nodes'])}")
        print(f"  Edges: {len(func_graph_all['edges'])}")
        
        # With repo_id
        func_graph_filtered = builder.get_function_graph_data(repo_id=repo_id, limit=100)
        print(f"\nFunction graph (repo_id={repo_id[:8]}):")
        print(f"  Nodes: {len(func_graph_filtered['nodes'])}")
        print(f"  Edges: {len(func_graph_filtered['edges'])}")
        
        # Check contamination
        func_contamination = []
        for node in func_graph_filtered['nodes']:
            if node['type'] == 'function':
                check = session.run("""
                    MATCH (r:Repository)-[:CONTAINS]->(f:File)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                    RETURN r.repo_id as repo_id, r.name as repo_name
                """, file_path=node['file']).data()
                
                if check:
                    node_repo = check[0]['repo_id']
                    if node_repo != repo_id:
                        func_contamination.append(f"{node['label']} from {check[0]['repo_name']}")
        
        if func_contamination:
            print(f"\n[FAIL] Function graph has cross-repo contamination:")
            for c in func_contamination[:5]:
                print(f"  - {c}")
        else:
            print(f"[OK] Function graph properly filtered")
        
        # TEST 3: Check API endpoint behavior
        print(f"\n{'=' * 80}")
        print("TEST 3: API Endpoint Defaults")
        print(f"{'=' * 80}")
        
        # Simulate what happens when frontend doesn't pass repo_id
        print(f"\nIf frontend calls /graph/data without repo_id:")
        print(f"  Returns {len(graph_data['nodes'])} file nodes")
        print(f"  Expected: {repo_files} (current repo only)")
        
        if len(graph_data['nodes']) > repo_files:
            print(f"  [WARN] File graph returns ALL repos (no default filtering)")
        else:
            print(f"  [OK] File graph filtered correctly")
        
        print(f"\nIf frontend calls /graph/functions without repo_id:")
        print(f"  Returns {len(func_graph_all['nodes'])} nodes")
        print(f"  With repo_id: {len(func_graph_filtered['nodes'])} nodes")
        
        if len(func_graph_all['nodes']) > len(func_graph_filtered['nodes']):
            print(f"  [WARN] Function graph returns ALL repos when repo_id=None")
        else:
            print(f"  [OK] Function graph filtered correctly")
        
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"File Graph Contamination: {'YES' if contamination else 'NO'}")
        print(f"Function Graph Contamination: {'YES' if func_contamination else 'NO'}")
        print(f"Total Issues: {len(contamination) + len(func_contamination)}")

if __name__ == "__main__":
    test_graph_isolation()
