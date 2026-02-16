from src.graph.graph_db import GraphDB

graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

# Test creating a function
test_file = "workspace\\test-02\\TestRepo4_TightlyCoupled\\main.py"
test_repo = "ac2832c1f452c2d8"

print(f"Creating function for file: {test_file}")
print(f"Repo ID: {test_repo}")

try:
    graph_db.create_function_node(test_file, "test_func", 1, test_repo)
    print("Function created successfully")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Check if it was created
from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12410946"))
with driver.session() as session:
    result = session.run("MATCH (fn:Function) RETURN count(fn) as count")
    count = result.single()['count']
    print(f"\nTotal functions after test: {count}")
    
    if count > 0:
        result = session.run("MATCH (fn:Function) RETURN fn.name as name, fn.file as file LIMIT 5")
        for record in result:
            print(f"  - {record['name']} in {record['file']}")

driver.close()
graph_db.close()
