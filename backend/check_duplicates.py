"""Check for duplicate File nodes"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))

with driver.session() as session:
    # Check File nodes with 'path' property
    result = session.run("""
        MATCH (f:File)
        WHERE f.path IS NOT NULL
        RETURN count(f) as count_with_path
    """)
    count_path = result.single()['count_with_path']
    
    # Check File nodes with 'file_path' property
    result = session.run("""
        MATCH (f:File)
        WHERE f.file_path IS NOT NULL
        RETURN count(f) as count_with_file_path
    """)
    count_file_path = result.single()['count_with_file_path']
    
    # Check total File nodes
    result = session.run("""
        MATCH (f:File)
        RETURN count(f) as total
    """)
    total = result.single()['total']
    
    print(f"Total File nodes: {total}")
    print(f"File nodes with 'path' property: {count_path}")
    print(f"File nodes with 'file_path' property: {count_file_path}")
    print()
    
    # Show sample of each type
    result = session.run("""
        MATCH (f:File)
        WHERE f.path IS NOT NULL AND f.file_path IS NULL
        RETURN f.path as path
        LIMIT 3
    """)
    print("Nodes with ONLY 'path':")
    for r in result:
        print(f"  - {r['path']}")
    
    result = session.run("""
        MATCH (f:File)
        WHERE f.file_path IS NOT NULL AND f.path IS NULL
        RETURN f.file_path as file_path
        LIMIT 3
    """)
    print("\nNodes with ONLY 'file_path':")
    for r in result:
        print(f"  - {r['file_path']}")
    
    result = session.run("""
        MATCH (f:File)
        WHERE f.path IS NOT NULL AND f.file_path IS NOT NULL
        RETURN f.path as path, f.file_path as file_path
        LIMIT 3
    """)
    print("\nNodes with BOTH properties:")
    for r in result:
        print(f"  - path: {r['path']}")
        print(f"    file_path: {r['file_path']}")

driver.close()
