"""Test file graph for cross-repo contamination"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB

def test_file_graph():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("FILE GRAPH ISOLATION TEST")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get repos
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        print(f"\nRepositories: {len(repos)}")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
        
        if not repos:
            print("\n[ERROR] No repos!")
            return
        
        repo_id = repos[0]['id']
        repo_name = repos[0]['name']
        
        # Count files
        total_files = session.run("MATCH (f:File) RETURN count(f) as count").single()['count']
        repo_files = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            RETURN count(f) as count
        """, repo_id=repo_id).single()['count']
        
        print(f"\n[COUNTS]")
        print(f"  Total Files in DB: {total_files}")
        print(f"  Files in {repo_name}: {repo_files}")
        
        if total_files > repo_files:
            print(f"  [WARN] {total_files - repo_files} orphaned files exist!")
        
        # Test get_graph_data() - uses Neo4j query
        print(f"\n{'=' * 80}")
        print("TEST 1: graph_db.get_graph_data() - Neo4j Query")
        print(f"{'=' * 80}")
        
        graph_data = graph_db.get_graph_data(limit=100)
        print(f"\nReturned {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
        
        # Check each node
        contamination = []
        for node in graph_data['nodes']:
            check = session.run("""
                MATCH (r:Repository)-[:CONTAINS]->(f:File)
                WHERE f.file_path = $file_path OR f.path = $file_path
                RETURN r.repo_id as repo_id, r.name as repo_name
            """, file_path=node['id']).data()
            
            if check:
                node_repo = check[0]['repo_id']
                if node_repo != repo_id:
                    contamination.append({
                        'file': node['label'],
                        'repo': check[0]['repo_name']
                    })
            else:
                # File has no Repository relationship (orphan)
                contamination.append({
                    'file': node['label'],
                    'repo': 'ORPHAN (no repo)'
                })
        
        if contamination:
            print(f"\n[FAIL] Found {len(contamination)} contaminated nodes:")
            for c in contamination[:10]:
                print(f"  - {c['file']} from {c['repo']}")
        else:
            print(f"[OK] All nodes belong to {repo_name}")
        
        # Test the Cypher query directly
        print(f"\n{'=' * 80}")
        print("TEST 2: Direct Cypher Query (what get_graph_data uses)")
        print(f"{'=' * 80}")
        
        result = session.run("""
            MATCH (f:File)
            OPTIONAL MATCH (f)-[r:DEPENDS_ON|IMPORTS]->(target:File)
            WITH f, COLLECT({target: target.path, type: type(r)}) as relationships
            RETURN f.path as id, f.path as label, relationships
            LIMIT 50
        """).data()
        
        print(f"\nQuery returned {len(result)} files")
        
        # Check if these files have Repository relationships
        orphans = []
        for record in result:
            file_path = record['id']
            if not file_path:
                continue
            
            check = session.run("""
                MATCH (r:Repository)-[:CONTAINS]->(f:File)
                WHERE f.file_path = $file_path OR f.path = $file_path
                RETURN r.repo_id as repo_id
            """, file_path=file_path).data()
            
            if not check:
                orphans.append(file_path)
        
        if orphans:
            print(f"\n[FAIL] Query returns {len(orphans)} orphaned files:")
            for o in orphans[:5]:
                print(f"  - {o}")
        else:
            print(f"[OK] All files have Repository relationships")
        
        # Test with repo filter
        print(f"\n{'=' * 80}")
        print("TEST 3: Query WITH Repository Filter")
        print(f"{'=' * 80}")
        
        filtered = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[rel:DEPENDS_ON|IMPORTS]->(target:File)
            WHERE (r)-[:CONTAINS]->(target)
            WITH f, COLLECT({target: target.path, type: type(rel)}) as relationships
            RETURN f.path as id, f.path as label, relationships
            LIMIT 50
        """, repo_id=repo_id).data()
        
        print(f"\nFiltered query returned {len(filtered)} files")
        print(f"Expected: {min(50, repo_files)} files")
        
        if len(filtered) == min(50, repo_files):
            print(f"[OK] Filtered query returns correct count")
        else:
            print(f"[WARN] Count mismatch")
        
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Files: {total_files}")
        print(f"Repo Files: {repo_files}")
        print(f"Orphaned: {total_files - repo_files}")
        print(f"get_graph_data() contamination: {len(contamination)} nodes")
        print(f"Direct query orphans: {len(orphans)} files")
        
        if contamination or orphans:
            print(f"\n[FAIL] File graph has isolation issues!")
            print(f"\nRECOMMENDATION: get_graph_data() needs Repository filter")
        else:
            print(f"\n[OK] File graph properly isolated")

if __name__ == "__main__":
    test_file_graph()
