from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12410946"))

with driver.session() as session:
    # Check functions
    result = session.run("MATCH (fn:Function) RETURN count(fn) as count")
    func_count = result.single()['count']
    print(f"Total Function nodes: {func_count}")
    
    # Check files
    result = session.run("MATCH (f:File) RETURN count(f) as count")
    file_count = result.single()['count']
    print(f"Total File nodes: {file_count}")
    
    # Check CALLS relationships
    result = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) as count")
    calls_count = result.single()['count']
    print(f"Total CALLS relationships: {calls_count}")
    
    # Check CONTAINS relationships to functions
    result = session.run("MATCH ()-[r:CONTAINS]->(fn:Function) RETURN count(r) as count")
    contains_count = result.single()['count']
    print(f"Total CONTAINS->Function relationships: {contains_count}")
    
    # Sample functions
    result = session.run("MATCH (fn:Function) RETURN fn.name as name, fn.file as file LIMIT 5")
    print("\nSample functions:")
    for record in result:
        print(f"  - {record['name']} in {record['file']}")

driver.close()
