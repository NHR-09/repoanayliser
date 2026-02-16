"""Clear all repositories from Neo4j database"""
import sys
sys.path.append('src')
from graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

print("Clearing all repositories from database...")

with graph_db.driver.session() as session:
    # Get count before
    result = session.run("MATCH (r:Repository) RETURN count(r) as count").single()
    repo_count = result['count']
    
    print(f"Found {repo_count} repositories")
    
    if repo_count == 0:
        print("Database is already empty")
    else:
        # Delete everything
        session.run("""
            MATCH (n)
            DETACH DELETE n
        """)
        
        print(f"Deleted all {repo_count} repositories and related data")
        
        # Verify
        result = session.run("MATCH (n) RETURN count(n) as count").single()
        remaining = result['count']
        
        if remaining == 0:
            print("Database cleared successfully!")
        else:
            print(f"Warning: {remaining} nodes still remain")
    
    # Check for orphan nodes
    print("\nChecking for orphan nodes...")
    orphans = session.run("""
        MATCH (n)
        WHERE NOT (n)--() 
        RETURN labels(n) as labels, count(n) as count
    """).data()
    
    if orphans:
        print("Found orphan nodes:")
        for o in orphans:
            print(f"  {o['labels']}: {o['count']} nodes")
        
        # Delete orphans
        session.run("""
            MATCH (n)
            WHERE NOT (n)--()
            DELETE n
        """)
        print("Orphan nodes deleted")
    else:
        print("No orphan nodes found")

print("\nDone. You can now analyze repositories with content_hash support.")
