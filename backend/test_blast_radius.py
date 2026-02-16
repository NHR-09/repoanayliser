"""Test blast radius calculation"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB
from graph.dependency_mapper import DependencyMapper
from graph.blast_radius import BlastRadiusAnalyzer

def test_blast_radius():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("BLAST RADIUS TEST")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Get repo
        repos = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name").data()
        if not repos:
            print("[ERROR] No repos!")
            return
        
        repo_id = repos[0]['id']
        
        # Get sample files
        files = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            RETURN f.file_path as path
            LIMIT 5
        """, repo_id=repo_id).data()
        
        print(f"\nTesting {len(files)} files:")
        for f in files:
            print(f"  - {f['path']}")
        
        # Check if dependency_mapper has data
        print(f"\n{'=' * 80}")
        print("TEST 1: Check DependencyMapper")
        print(f"{'=' * 80}")
        
        dep_mapper = DependencyMapper()
        print(f"  Graph nodes: {dep_mapper.graph.number_of_nodes()}")
        print(f"  Graph edges: {dep_mapper.graph.number_of_edges()}")
        
        if dep_mapper.graph.number_of_nodes() == 0:
            print("  [WARN] DependencyMapper is empty! Need to rebuild from DB")
            
            # Rebuild from DB
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(target:File)
                RETURN f.file_path as file, COLLECT(target.file_path) as deps
            """, repo_id=repo_id).data()
            
            parsed_files = []
            for r in result:
                parsed_files.append({
                    'file': r['file'],
                    'dependencies': [d for d in r['deps'] if d]
                })
            
            dep_mapper.build_graph(parsed_files)
            print(f"\n  Rebuilt graph:")
            print(f"    Nodes: {dep_mapper.graph.number_of_nodes()}")
            print(f"    Edges: {dep_mapper.graph.number_of_edges()}")
        
        # Test blast radius
        print(f"\n{'=' * 80}")
        print("TEST 2: Blast Radius Analysis")
        print(f"{'=' * 80}")
        
        analyzer = BlastRadiusAnalyzer(dep_mapper, graph_db)
        
        for f in files[:3]:
            file_path = f['path']
            print(f"\n[FILE] {file_path.split('\\\\')[-1]}")
            
            result = analyzer.analyze(file_path, "modify", repo_id)
            
            print(f"  Direct dependents: {len(result['direct_dependents'])}")
            print(f"  Indirect dependents: {len(result['indirect_dependents'])}")
            print(f"  Functions affected: {result['functions_affected']['total_functions']}")
            print(f"  Risk: {result['risk_level']} ({result['risk_score']}/100)")
            
            if result['direct_dependents']:
                print(f"  Direct deps:")
                for d in result['direct_dependents'][:3]:
                    print(f"    - {d.split('\\\\')[-1]}")
        
        # Check Neo4j relationships
        print(f"\n{'=' * 80}")
        print("TEST 3: Check Neo4j DEPENDS_ON relationships")
        print(f"{'=' * 80}")
        
        dep_count = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
            MATCH (f)-[:DEPENDS_ON]->(target:File)
            RETURN count(*) as count
        """, repo_id=repo_id).single()['count']
        
        print(f"  DEPENDS_ON relationships: {dep_count}")
        
        if dep_count > 0:
            sample = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                MATCH (f)-[:DEPENDS_ON]->(target:File)
                RETURN f.file_path as source, target.file_path as target
                LIMIT 5
            """, repo_id=repo_id).data()
            
            print(f"  Sample dependencies:")
            for s in sample:
                print(f"    {s['source'].split('\\\\')[-1]} -> {s['target'].split('\\\\')[-1]}")

if __name__ == "__main__":
    test_blast_radius()
