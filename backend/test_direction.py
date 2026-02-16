"""Test dependency direction"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB

def test_direction():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    with graph_db.driver.session() as session:
        # Get a file that is depended upon
        result = session.run("""
            MATCH (source:File)-[:DEPENDS_ON]->(target:File)
            RETURN target.file_path as target, COLLECT(source.file_path) as dependents
            ORDER BY size(COLLECT(source.file_path)) DESC
            LIMIT 3
        """).data()
        
        print("Files that are DEPENDED UPON (changing these affects others):")
        for r in result:
            target = r['target'].split('\\\\')[-1]
            dependents = [d.split('\\\\')[-1] for d in r['dependents']]
            print(f"\n{target} is used by {len(dependents)} files:")
            for d in dependents[:5]:
                print(f"  - {d}")
        
        # Test query
        if result:
            test_file = result[0]['target']
            print(f"\n{'=' * 80}")
            print(f"TEST: Blast radius for {test_file.split('\\\\')[-1]}")
            print(f"{'=' * 80}")
            
            # Direct dependents (files that import this file)
            direct = session.run("""
                MATCH (source:File)-[:DEPENDS_ON]->(target:File {file_path: $file_path})
                RETURN source.file_path as dependent
            """, file_path=test_file).data()
            
            print(f"\nDirect dependents: {len(direct)}")
            for d in direct[:5]:
                print(f"  - {d['dependent'].split('\\\\')[-1]}")

if __name__ == "__main__":
    test_direction()
