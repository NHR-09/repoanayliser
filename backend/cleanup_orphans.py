"""Cleanup orphaned Function/Class/File nodes from deleted repos"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB

def cleanup_orphans():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    print("=" * 80)
    print("CLEANUP: Removing orphaned nodes")
    print("=" * 80)
    
    with graph_db.driver.session() as session:
        # Count orphaned nodes
        orphan_files = session.run("""
            MATCH (f:File)
            WHERE NOT (f)<-[:CONTAINS]-(:Repository)
            RETURN count(f) as count
        """).single()['count']
        
        orphan_funcs = session.run("""
            MATCH (fn:Function)
            WHERE NOT EXISTS((fn)<-[:CONTAINS]-(:File)<-[:CONTAINS]-(:Repository))
            RETURN count(fn) as count
        """).single()['count']
        
        print(f"\nOrphaned Files: {orphan_files}")
        print(f"Orphaned Functions: {orphan_funcs}")
        
        if orphan_files == 0 and orphan_funcs == 0:
            print("\n[OK] No orphaned nodes found!")
            return
        
        # Delete orphaned nodes
        print("\n[CLEANUP] Deleting orphaned nodes...")
        
        result = session.run("""
            MATCH (f:File)
            WHERE NOT (f)<-[:CONTAINS]-(:Repository)
            OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
            OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
            DETACH DELETE f, c, fn
            RETURN count(f) as deleted_files
        """)
        
        deleted = result.single()['deleted_files']
        print(f"[OK] Deleted {deleted} orphaned files and their children")
        
        # Verify cleanup
        remaining_funcs = session.run("""
            MATCH (fn:Function)
            WHERE NOT EXISTS((fn)<-[:CONTAINS]-(:File)<-[:CONTAINS]-(:Repository))
            RETURN count(fn) as count
        """).single()['count']
        
        print(f"\n[VERIFY] Remaining orphaned functions: {remaining_funcs}")
        
        if remaining_funcs == 0:
            print("[OK] All orphaned nodes cleaned up!")
        else:
            print("[WARN] Some orphaned functions still exist")

if __name__ == "__main__":
    cleanup_orphans()
