"""Check path format in database"""
import sys
sys.path.append('src')
from graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

with graph_db.driver.session() as session:
    # Get sample file paths
    files = session.run("""
        MATCH (f:File)
        RETURN f.path as path, f.file_path as file_path
        LIMIT 10
    """).data()
    
    print("Sample file paths in DB:")
    for f in files:
        print(f"  path: {f['path']}")
        print(f"  file_path: {f['file_path']}")
        print()
    
    # Check DEPENDS_ON relationships
    deps = session.run("""
        MATCH (source:File)-[:DEPENDS_ON]->(target:File)
        RETURN source.path as source, target.path as target
        LIMIT 5
    """).data()
    
    print("\nSample DEPENDS_ON relationships:")
    for d in deps:
        print(f"  {d['source']} -> {d['target']}")
    
    # Test query with actual path
    if files:
        test_path = files[0]['path'] or files[0]['file_path']
        print(f"\n\nTesting blast radius query with: {test_path}")
        
        result = session.run("""
            MATCH (target:File)
            WHERE target.file_path = $file_path OR target.path = $file_path
            MATCH (source:File)-[:DEPENDS_ON]->(target)
            RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
        """, file_path=test_path).data()
        
        print(f"Direct dependents found: {len(result)}")
        for r in result:
            print(f"  - {r['dependent']}")
