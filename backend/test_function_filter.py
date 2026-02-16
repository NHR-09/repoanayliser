"""Test that functions are properly filtered by current repo"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB

def test_function_filtering():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("TEST: Function filtering by repo_id")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get all repos
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        print(f"\nRepositories in DB: {len(repos)}")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
        
        # Count total functions (no filter)
        total_funcs = session.run("MATCH (fn:Function) RETURN count(fn) as count").single()['count']
        print(f"\nTotal functions (all repos): {total_funcs}")
        
        # Count functions per repo
        for repo in repos:
            repo_id = repo['id']
            repo_name = repo['name']
            
            # Count using Repository relationship
            count = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                RETURN count(fn) as count
            """, repo_id=repo_id).single()['count']
            
            print(f"\nFunctions in {repo_name}: {count}")
            
            # Get sample functions
            funcs = graph_db.get_all_functions(repo_id)
            print(f"  get_all_functions({repo_id}): {len(funcs)} functions")
            if funcs:
                print(f"  Sample: {funcs[0]['name']} in {funcs[0]['file']}")
        
        # Test without repo_id (should return ALL)
        all_funcs = graph_db.get_all_functions(None)
        print(f"\nget_all_functions(None): {len(all_funcs)} functions (should be {total_funcs})")
        
        if len(all_funcs) == total_funcs:
            print("[OK] Without repo_id, returns all functions")
        else:
            print(f"[FAIL] Expected {total_funcs}, got {len(all_funcs)}")

if __name__ == "__main__":
    test_function_filtering()
