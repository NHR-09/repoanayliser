"""
Deep dive into CALLS vs DEPENDS_ON relationship logic
"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12410946"))

print("="*80)
print("INVESTIGATING: CALLS vs DEPENDS_ON Relationship")
print("="*80)

with driver.session() as session:
    # Find files that CALL functions but don't DEPEND_ON the file
    result = session.run("""
        MATCH (caller_file:File)-[:CALLS]->(fn:Function)<-[:CONTAINS]-(target_file:File)
        WHERE caller_file <> target_file
        AND NOT (caller_file)-[:DEPENDS_ON]->(target_file)
        RETURN DISTINCT 
            COALESCE(caller_file.file_path, caller_file.path) as caller,
            COALESCE(target_file.file_path, target_file.path) as target,
            fn.name as function
        LIMIT 10
    """)
    
    records = list(result)
    
    if records:
        print(f"\nFOUND ISSUE: {len(records)} cases where CALLS exists but DEPENDS_ON is missing\n")
        print("This is a LOGIC FLAW in the graph structure!")
        print("\nExamples:")
        for r in records[:5]:
            print(f"\n  Caller: {r['caller']}")
            print(f"  Target: {r['target']}")
            print(f"  Function: {r['function']}")
            print(f"  -> Caller CALLS function but doesn't DEPEND_ON the file")
    else:
        print("\nNo issues found - all CALLS relationships have corresponding DEPENDS_ON")

# Check self-calls (file calling its own functions)
with driver.session() as session:
    result = session.run("""
        MATCH (file:File)-[:CALLS]->(fn:Function)<-[:CONTAINS]-(file)
        RETURN DISTINCT COALESCE(file.file_path, file.path) as file,
               COUNT(fn) as self_calls
    """)
    
    records = list(result)
    if records:
        print(f"\n\nSELF-CALLS DETECTED: {len(records)} files call their own functions")
        print("This is EXPECTED behavior (internal function calls)")
        for r in records[:5]:
            print(f"  - {r['file']}: {r['self_calls']} self-calls")

# Check if DEPENDS_ON is properly created during parsing
print("\n" + "="*80)
print("CHECKING: File Import -> DEPENDS_ON mapping")
print("="*80)

with driver.session() as session:
    # Files with IMPORTS but no DEPENDS_ON
    result = session.run("""
        MATCH (file:File)-[:IMPORTS]->(module:Module)
        WHERE NOT EXISTS((file)-[:DEPENDS_ON]->(:File))
        RETURN DISTINCT COALESCE(file.file_path, file.path) as file,
               COUNT(module) as import_count
        LIMIT 10
    """)
    
    records = list(result)
    if records:
        print(f"\nPOTENTIAL ISSUE: {len(records)} files have IMPORTS but no DEPENDS_ON")
        print("This might be expected if imports are external modules")
        for r in records[:5]:
            print(f"  - {r['file']}: {r['import_count']} imports")
    else:
        print("\nAll files with imports have DEPENDS_ON relationships")

# Check dependency mapper logic
print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

print("""
FINDINGS:

1. SELF-CALLS: Files calling their own functions is EXPECTED and CORRECT
   - These should NOT be counted in blast radius
   - Current code filters by 'caller_file <> target_file' - CORRECT

2. CALLS without DEPENDS_ON: If this exists, it's a graph construction issue
   - When a file calls a function from another file, it should:
     a) Have CALLS relationship to the function
     b) Have DEPENDS_ON relationship to the file containing the function
   
3. BLAST RADIUS LOGIC:
   - Direct dependents: Files with DEPENDS_ON -> target (CORRECT)
   - Function callers: Files with CALLS -> target's functions (CORRECT)
   - These should be COMBINED, not separate
   
RECOMMENDED FIX:
- Function callers should be ADDED to direct dependents, not separate
- Or: Ensure DEPENDS_ON is created whenever CALLS is created
""")

driver.close()
