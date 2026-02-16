"""Debug script to check function graph relationships"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))

print("\n=== CHECKING FUNCTION NODES ===")
with driver.session() as session:
    result = session.run("""
        MATCH (fn:Function)
        RETURN count(fn) as total
    """)
    record = result.single()
    print(f"Total Function nodes: {record['total']}")
    
    result = session.run("""
        MATCH (fn:Function)
        RETURN fn.name as name, fn.file as file
        LIMIT 10
    """)
    print("\nSample functions:")
    for r in result:
        print(f"  - {r['name']} in {r['file']}")

print("\n=== CHECKING CALLS RELATIONSHIPS ===")
with driver.session() as session:
    result = session.run("""
        MATCH ()-[r:CALLS]->()
        RETURN count(r) as total
    """)
    record = result.single()
    print(f"Total CALLS relationships: {record['total']}")
    
    result = session.run("""
        MATCH (f:File)-[r:CALLS]->(fn:Function)
        RETURN f.path as caller, fn.name as callee
        LIMIT 10
    """)
    print("\nSample CALLS relationships:")
    for r in result:
        print(f"  - {r['caller']} -> {r['callee']}")

print("\n=== CHECKING FILE->CONTAINS->FUNCTION ===")
with driver.session() as session:
    result = session.run("""
        MATCH (f:File)-[:CONTAINS]->(fn:Function)
        RETURN count(fn) as total
    """)
    record = result.single()
    print(f"Total File->CONTAINS->Function: {record['total']}")

print("\n=== CHECKING REPOSITORY STRUCTURE ===")
with driver.session() as session:
    result = session.run("""
        MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
        RETURN count(fn) as total
    """)
    record = result.single()
    print(f"Total Repository->File->Function: {record['total']}")

driver.close()
