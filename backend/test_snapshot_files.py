"""Test snapshot file relationships"""
import sys
sys.path.append('src')
from graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

with graph_db.driver.session() as session:
    # Get snapshots
    snapshots = session.run("""
        MATCH (s:Snapshot)
        RETURN s.snapshot_id as id, toString(s.created_at) as date, s.total_files as files
        ORDER BY s.created_at DESC
        LIMIT 5
    """).data()
    
    print("Recent snapshots:")
    for s in snapshots:
        print(f"  {s['id'][:8]} - {s['date']} - {s['files']} files")
    
    if len(snapshots) >= 2:
        s1 = snapshots[0]['id']
        s2 = snapshots[1]['id']
        
        print(f"\nChecking ANALYZED_FILE relationships:")
        print(f"Snapshot 1: {s1[:8]}")
        print(f"Snapshot 2: {s2[:8]}")
        
        # Check relationships
        for snap_id, label in [(s1, "Snapshot 1"), (s2, "Snapshot 2")]:
            result = session.run("""
                MATCH (s:Snapshot {snapshot_id: $snap_id})-[:ANALYZED_FILE]->(f:File)
                RETURN count(f) as count
            """, snap_id=snap_id).single()
            
            print(f"\n{label}: {result['count']} ANALYZED_FILE relationships")
            
            if result['count'] == 0:
                print(f"  ❌ NO ANALYZED_FILE RELATIONSHIPS!")
                
                # Check if files exist at all
                files = session.run("""
                    MATCH (r:Repository)-[:HAS_SNAPSHOT]->(s:Snapshot {snapshot_id: $snap_id})
                    MATCH (r)-[:CONTAINS]->(f:File)
                    RETURN count(f) as count
                """, snap_id=snap_id).single()
                
                print(f"  Files in repository: {files['count']}")
