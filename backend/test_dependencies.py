"""Check if DEPENDS_ON relationships exist"""
import sys
sys.path.append('src')
from graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

with graph_db.driver.session() as session:
    # Check DEPENDS_ON relationships
    result = session.run("""
        MATCH ()-[r:DEPENDS_ON]->()
        RETURN count(r) as count
    """).single()
    
    print(f"DEPENDS_ON relationships: {result['count']}")
    
    if result['count'] == 0:
        print("\n❌ NO DEPENDS_ON RELATIONSHIPS FOUND!")
        print("This is why blast radius returns 0.")
        
        # Check what relationships DO exist
        print("\nRelationships that DO exist:")
        rels = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as count
            ORDER BY count DESC
        """).data()
        
        for rel in rels:
            print(f"  {rel['rel_type']}: {rel['count']}")
        
        # Check if IMPORTS relationships exist (old schema)
        imports = session.run("""
            MATCH ()-[r:IMPORTS]->()
            RETURN count(r) as count
        """).single()
        
        if imports['count'] > 0:
            print(f"\n⚠️ Found {imports['count']} IMPORTS relationships")
            print("Your code uses DEPENDS_ON but DB has IMPORTS!")
    else:
        print(f"\n✅ Found {result['count']} DEPENDS_ON relationships")
        
        # Show sample
        sample = session.run("""
            MATCH (source:File)-[:DEPENDS_ON]->(target:File)
            RETURN source.path as source, target.path as target
            LIMIT 5
        """).data()
        
        print("\nSample dependencies:")
        for s in sample:
            print(f"  {s['source']} -> {s['target']}")
