"""Check existing function calls in database"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))

with driver.session() as session:
    # Get a sample file that has functions
    result = session.run("""
        MATCH (f:File)-[:CONTAINS]->(fn:Function)
        RETURN f.path as file, collect(fn.name) as functions
        LIMIT 1
    """)
    record = result.single()
    if record:
        sample_file = record['file']
        functions_in_file = record['functions']
        print(f"Sample file: {sample_file}")
        print(f"Functions in file: {functions_in_file}")
        
        # Check if this file has any CALLS relationships
        result = session.run("""
            MATCH (f:File {path: $file})-[r:CALLS]->(fn:Function)
            RETURN fn.name as called_function
        """, file=sample_file)
        calls = [r['called_function'] for r in result]
        print(f"CALLS from this file: {calls}")
        
        # Check what function calls were extracted (if stored somewhere)
        # Let's check if the file calls any of its own functions
        result = session.run("""
            MATCH (f:File {path: $file})
            MATCH (f)-[:CONTAINS]->(fn:Function)
            OPTIONAL MATCH (f)-[:CALLS]->(fn)
            RETURN fn.name as function, count(f) as is_called
        """, file=sample_file)
        print("\nFunctions and whether they're called:")
        for r in result:
            print(f"  - {r['function']}: {'YES' if r['is_called'] > 0 else 'NO'}")

driver.close()
