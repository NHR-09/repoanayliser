"""Test full flow of function call storage"""
from neo4j import GraphDatabase
import os
import tempfile
import shutil

# Create a test repository
test_dir = tempfile.mkdtemp()
print(f"Test directory: {test_dir}")

# Create test files
file1 = os.path.join(test_dir, "module_a.py")
file2 = os.path.join(test_dir, "module_b.py")

with open(file1, 'w') as f:
    f.write("""
def helper():
    return "helper"

def process():
    result = helper()
    return result
""")

with open(file2, 'w') as f:
    f.write("""
from module_a import helper

def main():
    helper()
    process_data()
    
def process_data():
    return "data"
""")

# Initialize git repo
os.system(f'cd {test_dir} && git init && git add . && git commit -m "initial"')

# Now analyze it
from src.analysis_engine import AnalysisEngine

engine = AnalysisEngine()
result = engine.analyze_repository(test_dir)

print("\n=== ANALYSIS RESULT ===")
print(f"Status: {result['status']}")
print(f"Total files: {result['total_files']}")

# Check database
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12410946"))

print("\n=== CHECKING DATABASE ===")
with driver.session() as session:
    # Check functions
    result = session.run("""
        MATCH (fn:Function)
        WHERE fn.file CONTAINS $test_dir
        RETURN fn.name as name, fn.file as file
    """, test_dir=test_dir.replace('\\', '\\\\'))
    functions = [dict(r) for r in result]
    print(f"Functions found: {len(functions)}")
    for f in functions:
        print(f"  - {f['name']} in {f['file']}")
    
    # Check CALLS relationships
    result = session.run("""
        MATCH (f:File)-[r:CALLS]->(fn:Function)
        WHERE f.path CONTAINS $test_dir
        RETURN f.path as caller, fn.name as callee
    """, test_dir=test_dir.replace('\\', '\\\\'))
    calls = [dict(r) for r in result]
    print(f"\nCALLS relationships: {len(calls)}")
    for c in calls:
        print(f"  - {c['caller']} -> {c['callee']}")

driver.close()

# Cleanup
shutil.rmtree(test_dir)
print(f"\nCleaned up {test_dir}")
