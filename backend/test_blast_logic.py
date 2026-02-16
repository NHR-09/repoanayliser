"""
Test blast radius logic by examining actual graph structure
"""
from neo4j import GraphDatabase
from src.graph.blast_radius import BlastRadiusAnalyzer
from src.graph.dependency_mapper import DependencyMapper
from src.graph.graph_db import GraphDB
import json

# Connect to Neo4j
driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12410946"))
graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")

print("="*80)
print("BLAST RADIUS LOGIC VERIFICATION")
print("="*80)

# Get a sample file to test
with driver.session() as session:
    result = session.run("""
        MATCH (f:File)
        WHERE EXISTS((f)<-[:DEPENDS_ON]-())
        RETURN f.file_path as path, f.path as alt_path
        LIMIT 1
    """)
    record = result.single()
    
    if not record:
        print("\nNo files with dependents found in database")
        driver.close()
        exit(1)
    
    test_file = record['path'] or record['alt_path']
    print(f"\nTesting file: {test_file}")

# Test 1: Check DEPENDS_ON relationships
print("\n" + "="*80)
print("TEST 1: DEPENDS_ON Relationships (File-level)")
print("="*80)

with driver.session() as session:
    # Direct dependents
    result = session.run("""
        MATCH (target:File)
        WHERE target.file_path = $file_path OR target.path = $file_path
        MATCH (source:File)-[:DEPENDS_ON]->(target)
        RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
    """, file_path=test_file)
    
    direct_deps = [r['dependent'] for r in result if r['dependent']]
    print(f"\nDirect dependents: {len(direct_deps)}")
    for dep in direct_deps[:5]:
        print(f"   - {dep}")
    
    # Indirect dependents (2-3 hops)
    result = session.run("""
        MATCH (target:File)
        WHERE target.file_path = $file_path OR target.path = $file_path
        MATCH (source:File)
        WHERE COALESCE(source.file_path, source.path) <> $file_path
        MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
        RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
    """, file_path=test_file)
    
    indirect_deps = [r['dependent'] for r in result if r['dependent']]
    # Remove direct deps from indirect
    indirect_deps = [d for d in indirect_deps if d not in direct_deps]
    print(f"\nIndirect dependents (2-3 hops): {len(indirect_deps)}")
    for dep in indirect_deps[:5]:
        print(f"   - {dep}")

# Test 2: Check CALLS relationships (Function-level)
print("\n" + "="*80)
print("TEST 2: CALLS Relationships (Function-level)")
print("="*80)

with driver.session() as session:
    result = session.run("""
        MATCH (f:File)-[:CONTAINS]->(fn:Function)
        WHERE f.file_path = $file_path OR f.path = $file_path
        OPTIONAL MATCH (caller:File)-[:CALLS]->(fn)
        RETURN fn.name as function, 
               COLLECT(DISTINCT COALESCE(caller.file_path, caller.path)) as callers
    """, file_path=test_file)
    
    functions = []
    all_callers = set()
    for r in result:
        callers = [c for c in r['callers'] if c]
        functions.append({
            'name': r['function'],
            'callers': callers,
            'count': len(callers)
        })
        all_callers.update(callers)
    
    print(f"\nFunctions in file: {len(functions)}")
    for fn in functions[:5]:
        print(f"   - {fn['name']}: {fn['count']} callers")
    
    print(f"\nUnique files calling functions: {len(all_callers)}")
    for caller in list(all_callers)[:5]:
        print(f"   - {caller}")

# Test 3: Run actual blast radius analyzer
print("\n" + "="*80)
print("TEST 3: Blast Radius Analyzer Output")
print("="*80)

dependency_mapper = DependencyMapper()
analyzer = BlastRadiusAnalyzer(dependency_mapper, graph_db)

for change_type in ['modify', 'delete', 'move']:
    print(f"\n--- Change Type: {change_type.upper()} ---")
    result = analyzer.analyze(test_file, change_type)
    
    print(f"Direct dependents: {len(result['direct_dependents'])}")
    print(f"Indirect dependents: {len(result['indirect_dependents'])}")
    print(f"Total affected: {result['total_affected']}")
    print(f"Functions affected: {result['functions_affected']['total_functions']}")
    print(f"Function callers: {len(result['functions_affected']['callers'])}")
    print(f"Risk level: {result['risk_level']} (score: {result['risk_score']})")

# Test 4: Check for logic flaws
print("\n" + "="*80)
print("TEST 4: Logic Flaw Detection")
print("="*80)

issues = []

# Issue 1: Are direct and indirect properly separated?
result = analyzer.analyze(test_file, 'modify')
overlap = set(result['direct_dependents']) & set(result['indirect_dependents'])
if overlap:
    issues.append(f"FLAW: {len(overlap)} files appear in both direct AND indirect dependents")
    for f in list(overlap)[:3]:
        issues.append(f"   - {f}")
else:
    print("No overlap between direct and indirect dependents")

# Issue 2: Are function callers counted correctly?
func_impact = result['functions_affected']
func_caller_files = set(func_impact['callers'])
direct_deps_set = set(result['direct_dependents'])

# Function callers should be a subset or superset of direct dependents
# (files that call functions should also depend on the file)
if func_caller_files and not func_caller_files.issubset(direct_deps_set):
    missing = func_caller_files - direct_deps_set
    if missing:
        issues.append(f"WARNING: {len(missing)} function callers not in direct dependents")
        issues.append(f"   This might be correct if CALLS doesn't imply DEPENDS_ON")
        for f in list(missing)[:3]:
            issues.append(f"   - {f}")
else:
    print("Function callers align with direct dependents")

# Issue 3: Risk scoring consistency
for change_type in ['modify', 'delete', 'move']:
    result = analyzer.analyze(test_file, change_type)
    
    # Check if risk level matches score
    score = result['risk_score']
    level = result['risk_level']
    
    if change_type == 'delete':
        expected = 'critical' if score >= 100 else 'high' if score >= 60 else 'medium' if score >= 30 else 'low'
    elif change_type == 'move':
        expected = 'high' if score > 80 else 'medium' if score > 40 else 'low'
    else:  # modify
        total = result['total_affected']
        expected = 'high' if total > 15 else 'medium' if total > 8 else 'low'
    
    if level != expected:
        issues.append(f"FLAW: {change_type} risk level '{level}' doesn't match expected '{expected}' (score: {score})")
    else:
        print(f"{change_type.capitalize()} risk scoring is consistent")

# Issue 4: Check if indirect deps include direct deps
result = analyzer.analyze(test_file, 'modify')
if set(result['direct_dependents']) & set(result['indirect_dependents']):
    issues.append("FLAW: Indirect dependents should NOT include direct dependents")
else:
    print("Indirect dependents properly exclude direct dependents")

# Issue 5: Verify graph traversal depth
with driver.session() as session:
    # Check if there are any 4+ hop dependencies that are missed
    result_4hop = session.run("""
        MATCH (target:File)
        WHERE target.file_path = $file_path OR target.path = $file_path
        MATCH path = (source:File)-[:DEPENDS_ON*4..5]->(target)
        WHERE COALESCE(source.file_path, source.path) <> $file_path
        RETURN COUNT(DISTINCT source) as count
    """, file_path=test_file)
    
    count_4hop = result_4hop.single()['count']
    if count_4hop > 0:
        issues.append(f"WARNING: {count_4hop} files depend on target via 4-5 hops (not captured)")
    else:
        print("No deep dependencies beyond 3 hops")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if issues:
    print(f"\nFound {len(issues)} potential issues:\n")
    for issue in issues:
        print(issue)
else:
    print("\nNo logic flaws detected! Blast radius analyzer working correctly.")

print("\n" + "="*80)

driver.close()
