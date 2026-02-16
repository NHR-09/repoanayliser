"""Check path formats in database"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))

with driver.session() as session:
    # Check File node paths
    result = session.run("""
        MATCH (f:File)-[:CONTAINS]->(fn:Function)
        RETURN f.path as file_path, fn.file as function_file_attr, fn.name as func_name
        LIMIT 5
    """)
    print("=== FILE PATHS IN DATABASE ===")
    for r in result:
        print(f"File.path: {r['file_path']}")
        print(f"Function.file: {r['function_file_attr']}")
        print(f"Function.name: {r['func_name']}")
        print(f"Match: {r['file_path'] == r['function_file_attr']}")
        print()

driver.close()
