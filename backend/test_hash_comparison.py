"""Check if files have hashes"""
import sys
sys.path.append('src')
from graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

with graph_db.driver.session() as session:
    # Get recent snapshots
    snapshots = session.run("""
        MATCH (s:Snapshot)
        RETURN s.snapshot_id as id, toString(s.created_at) as date
        ORDER BY s.created_at DESC
        LIMIT 2
    """).data()
    
    if len(snapshots) >= 2:
        s1 = snapshots[0]['id']
        s2 = snapshots[1]['id']
        
        print(f"Snapshot 1: {s1[:8]}")
        print(f"Snapshot 2: {s2[:8]}")
        
        # Check files in snapshot 1
        result = session.run("""
            MATCH (s:Snapshot {snapshot_id: $snap_id})-[:ANALYZED_FILE]->(f:File)
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)
            RETURN f.file_path as path, f.content_hash as file_hash, v.hash as version_hash
            LIMIT 5
        """, snap_id=s1).data()
        
        print(f"\nSnapshot 1 files:")
        for r in result:
            print(f"  {r['path']}")
            print(f"    file_hash: {r['file_hash']}")
            print(f"    version_hash: {r['version_hash']}")
        
        # Check files in snapshot 2
        result = session.run("""
            MATCH (s:Snapshot {snapshot_id: $snap_id})-[:ANALYZED_FILE]->(f:File)
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)
            RETURN f.file_path as path, f.content_hash as file_hash, v.hash as version_hash
            LIMIT 5
        """, snap_id=s2).data()
        
        print(f"\nSnapshot 2 files:")
        for r in result:
            print(f"  {r['path']}")
            print(f"    file_hash: {r['file_hash']}")
            print(f"    version_hash: {r['version_hash']}")
        
        # Test the actual comparison query
        print(f"\n\nTesting comparison query:")
        result = session.run("""
            MATCH (s1:Snapshot {snapshot_id: $snapshot1})-[:ANALYZED_FILE]->(f1:File)
            OPTIONAL MATCH (f1)-[:HAS_VERSION]->(v1:Version)
            WITH collect({path: f1.file_path, hash: COALESCE(v1.hash, f1.content_hash)}) as files1
            MATCH (s2:Snapshot {snapshot_id: $snapshot2})-[:ANALYZED_FILE]->(f2:File)
            OPTIONAL MATCH (f2)-[:HAS_VERSION]->(v2:Version)
            WITH files1, collect({path: f2.file_path, hash: COALESCE(v2.hash, f2.content_hash)}) as files2
            RETURN files1, files2
        """, snapshot1=s1, snapshot2=s2).single()
        
        files1 = result['files1']
        files2 = result['files2']
        
        print(f"\nFiles1 count: {len(files1)}")
        print(f"Files2 count: {len(files2)}")
        
        print(f"\nFiles1 sample:")
        for f in files1[:3]:
            print(f"  {f['path']}: {f['hash']}")
        
        print(f"\nFiles2 sample:")
        for f in files2[:3]:
            print(f"  {f['path']}: {f['hash']}")
