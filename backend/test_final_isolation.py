"""FINAL COMPREHENSIVE ISOLATION TEST"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB
from graph.function_graph import FunctionGraphBuilder

def final_test():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("FINAL COMPREHENSIVE REPOSITORY ISOLATION TEST")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get repos
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        print(f"\nRepositories: {len(repos)}")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
        
        if not repos:
            print("\n[ERROR] No repositories!")
            return
        
        repo_id = repos[0]['id']
        repo_name = repos[0]['name']
        
        # Count everything
        total_files = session.run("MATCH (f:File) RETURN count(f) as count").single()['count']
        total_funcs = session.run("MATCH (fn:Function) RETURN count(fn) as count").single()['count']
        
        repo_files = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            RETURN count(f) as count
        """, repo_id=repo_id).single()['count']
        
        repo_funcs = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
            RETURN count(fn) as count
        """, repo_id=repo_id).single()['count']
        
        print(f"\n[DATABASE TOTALS]")
        print(f"  Total Files: {total_files}")
        print(f"  Total Functions: {total_funcs}")
        print(f"\n[CURRENT REPO: {repo_name}]")
        print(f"  Files: {repo_files}")
        print(f"  Functions: {repo_funcs}")
        print(f"\n[ORPHANS]")
        print(f"  Orphaned Files: {total_files - repo_files}")
        print(f"  Orphaned Functions: {total_funcs - repo_funcs}")
        
        # TEST 1: File Graph
        print(f"\n{'=' * 80}")
        print("TEST 1: File Graph (get_graph_data)")
        print(f"{'=' * 80}")
        
        file_graph = graph_db.get_graph_data(repo_id=repo_id, limit=100)
        print(f"  Nodes: {len(file_graph['nodes'])}")
        print(f"  Edges: {len(file_graph['edges'])}")
        
        file_contamination = 0
        for node in file_graph['nodes']:
            check = session.run("""
                MATCH (r:Repository)-[:CONTAINS]->(f:File)
                WHERE f.file_path = $file_path OR f.path = $file_path
                RETURN r.repo_id as repo_id
            """, file_path=node['id']).data()
            
            if not check or check[0]['repo_id'] != repo_id:
                file_contamination += 1
        
        print(f"  Contamination: {file_contamination} nodes")
        print(f"  Status: {'[FAIL]' if file_contamination > 0 else '[OK]'}")
        
        # TEST 2: Function Graph
        print(f"\n{'=' * 80}")
        print("TEST 2: Function Graph (get_function_graph_data)")
        print(f"{'=' * 80}")
        
        builder = FunctionGraphBuilder(graph_db)
        func_graph = builder.get_function_graph_data(repo_id=repo_id, limit=100)
        print(f"  Nodes: {len(func_graph['nodes'])}")
        print(f"  Edges: {len(func_graph['edges'])}")
        
        func_contamination = 0
        for node in func_graph['nodes']:
            if node['type'] == 'function':
                check = session.run("""
                    MATCH (r:Repository)-[:CONTAINS]->(f:File)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                    RETURN r.repo_id as repo_id
                """, file_path=node['file']).data()
                
                if not check or check[0]['repo_id'] != repo_id:
                    func_contamination += 1
        
        print(f"  Contamination: {func_contamination} nodes")
        print(f"  Status: {'[FAIL]' if func_contamination > 0 else '[OK]'}")
        
        # TEST 3: Functions List
        print(f"\n{'=' * 80}")
        print("TEST 3: Functions List (get_all_functions)")
        print(f"{'=' * 80}")
        
        all_funcs = graph_db.get_all_functions(repo_id=repo_id)
        print(f"  Functions returned: {len(all_funcs)}")
        print(f"  Expected: {repo_funcs}")
        print(f"  Status: {'[OK]' if len(all_funcs) == repo_funcs else '[FAIL]'}")
        
        # FINAL VERDICT
        print(f"\n{'=' * 80}")
        print("FINAL VERDICT")
        print(f"{'=' * 80}")
        
        total_issues = file_contamination + func_contamination + (len(all_funcs) != repo_funcs)
        orphan_issues = (total_files - repo_files) + (total_funcs - repo_funcs)
        
        print(f"\nCross-Repo Contamination: {total_issues} issues")
        print(f"Orphaned Nodes: {orphan_issues} nodes")
        
        if total_issues == 0 and orphan_issues == 0:
            print(f"\n{'*' * 80}")
            print("ALL TESTS PASSED - REPOSITORY ISOLATION COMPLETE!")
            print(f"{'*' * 80}")
        else:
            print(f"\n[FAIL] Issues found:")
            if file_contamination > 0:
                print(f"  - File graph: {file_contamination} contaminated nodes")
            if func_contamination > 0:
                print(f"  - Function graph: {func_contamination} contaminated nodes")
            if len(all_funcs) != repo_funcs:
                print(f"  - Functions list: {len(all_funcs)} returned, expected {repo_funcs}")
            if orphan_issues > 0:
                print(f"  - Orphaned nodes: {orphan_issues} nodes without Repository")

if __name__ == "__main__":
    final_test()
