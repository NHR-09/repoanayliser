"""Retroactively create CALLS relationships for existing functions"""
from neo4j import GraphDatabase
from src.parser.static_parser import StaticParser

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))
parser = StaticParser()

with driver.session() as session:
    # Get all files with functions
    result = session.run("""
        MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
        RETURN DISTINCT r.repo_id as repo_id, 
               COALESCE(f.path, f.file_path) as file_path,
               f.language as language
    """)
    files = [dict(r) for r in result]
    
    print(f"Found {len(files)} files with functions")
    
    calls_created = 0
    for file_info in files:
        file_path = file_info['file_path']
        repo_id = file_info['repo_id']
        language = file_info['language']
        
        try:
            # Re-parse the file to get function calls
            parsed = parser.parse_file(file_path, language)
            function_calls = parsed.get('function_calls', [])
            
            if function_calls:
                print(f"\n{file_path}: {len(set(function_calls))} unique calls")
                
                for called_func in set(function_calls):
                    # Create CALLS relationship
                    result = session.run("""
                        MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                        WHERE f.path = $file_path OR f.file_path = $file_path
                        MATCH (r)-[:CONTAINS]->(:File)-[:CONTAINS]->(fn:Function {name: $called_func})
                        MERGE (f)-[:CALLS]->(fn)
                        RETURN count(fn) as matched
                    """, repo_id=repo_id, file_path=file_path, called_func=called_func)
                    
                    record = result.single()
                    if record and record['matched'] > 0:
                        print(f"  ✓ {called_func}")
                        calls_created += 1
        except Exception as e:
            print(f"  Error parsing {file_path}: {e}")
    
    print(f"\n\nTotal CALLS relationships created: {calls_created}")
    
    # Verify
    result = session.run("""
        MATCH ()-[r:CALLS]->()
        RETURN count(r) as total
    """)
    total = result.single()['total']
    print(f"Total CALLS relationships in database: {total}")

driver.close()
