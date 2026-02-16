from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12410946"))

with driver.session() as session:
    # Check Repository nodes
    result = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.name as name")
    print("Repositories:")
    for record in result:
        print(f"  - {record['name']} ({record['id']})")
    
    # Check File nodes with Repository relationship
    result = session.run("""
        MATCH (r:Repository)-[:CONTAINS]->(f:File)
        RETURN r.repo_id as repo_id, count(f) as file_count
    """)
    print("\nFiles linked to repositories:")
    for record in result:
        print(f"  - Repo {record['repo_id']}: {record['file_count']} files")
    
    # Check orphan files
    result = session.run("""
        MATCH (f:File)
        WHERE NOT (f)<-[:CONTAINS]-(:Repository)
        RETURN count(f) as orphan_count
    """)
    orphan_count = result.single()['orphan_count']
    print(f"\nOrphan files (not linked to repo): {orphan_count}")

driver.close()
