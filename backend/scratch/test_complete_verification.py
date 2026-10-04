import os
import sys
from pathlib import Path
from src.config import settings
from src.graph.graph_db import GraphDB
from src.analysis_engine import AnalysisEngine
from src.graph.blast_radius import BlastRadiusAnalyzer

sample_dir = r"C:\Users\user\Desktop\STUDY\PPROJECTS\repoanayliser-main\backend\workspace\benchmark_sample"

# 1. Clean up old benchmark_sample repository from Neo4j so fresh analysis runs without old cross-repo edges
db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
with db.driver.session() as s:
    s.run("""
        MATCH (r:Repository)
        WHERE r.url CONTAINS 'benchmark_sample' OR r.path CONTAINS 'benchmark_sample'
        OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
        OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
        OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
        DETACH DELETE fn, c, f, r
    """)
    s.run("""
        MATCH (s:Snapshot)
        WHERE s.repo_id = '9ee777922cb26dbe'
        DETACH DELETE s
    """)
print("Cleared old benchmark_sample data from Neo4j.")

# 2. Run fresh analysis
engine = AnalysisEngine()
res = engine.analyze_local_path(sample_dir)
repo_id = engine.current_repo_id
print(f"Analysis complete! Repo ID: {repo_id}")

# 3. Check NetworkX File Dependency Graph
nx_graph = engine.dependency_mapper.graph
nx_file_nodes = [n for n in nx_graph.nodes() if '\\' in n or '/' in n]
print(f"\n--- NetworkX File Graph ---")
print(f"Total file nodes: {len(nx_file_nodes)}")
for n in sorted(nx_file_nodes):
    rel = os.path.relpath(n, sample_dir).replace('\\', '/')
    succs = [os.path.relpath(s, sample_dir).replace('\\', '/') for s in nx_graph.successors(n) if ('\\' in s or '/' in s)]
    print(f"  {rel} -> {succs}")

# 4. Check Neo4j File Graph Data
neo4j_graph = engine.graph_db.get_graph_data(repo_id=repo_id)
print(f"\n--- Neo4j File Graph (repo_id={repo_id}) ---")
print(f"Total nodes: {len(neo4j_graph['nodes'])}")
print(f"Total edges: {len(neo4j_graph['edges'])}")
for e in neo4j_graph['edges']:
    src_rel = os.path.relpath(e['source'], sample_dir).replace('\\', '/')
    tgt_rel = os.path.relpath(e['target'], sample_dir).replace('\\', '/')
    print(f"  {src_rel} --DEPENDS_ON--> {tgt_rel}")

# 5. Check Blast Radius on all 5 files
analyzer = BlastRadiusAnalyzer(engine.dependency_mapper, engine.graph_db)
files = [
    "database/db.py",
    "auth/crypto.py",
    "auth/user_service.py",
    "api/tokens.py",
    "api/routes.py",
]

print(f"\n--- Blast Radius Results (After Fixes) ---")
for rel_p in files:
    full_p = os.path.join(sample_dir, rel_p.replace('/', os.sep))
    blast = analyzer.analyze(full_p, "modify", repo_id=repo_id)
    direct = [os.path.relpath(p, sample_dir).replace('\\', '/') for p in blast['direct_dependents']]
    indirect = [os.path.relpath(p, sample_dir).replace('\\', '/') for p in blast['indirect_dependents']]
    callers = [os.path.relpath(p, sample_dir).replace('\\', '/') for p in blast['impact_breakdown']['function_callers'] if isinstance(p, str)] if isinstance(blast['impact_breakdown']['function_callers'], list) else blast['impact_breakdown']['function_callers']
    
    fn_details = []
    for fn in blast['functions_affected'].get('functions', []):
        cls = [os.path.relpath(c, sample_dir).replace('\\', '/') for c in fn.get('callers', [])]
        if cls:
            fn_details.append(f"{fn.get('name')} (called by {cls})")
            
    print(f"\nFile: {rel_p}")
    print(f"  Direct Dependents ({len(direct)}): {sorted(direct)}")
    print(f"  Indirect Dependents ({len(indirect)}): {sorted(indirect)}")
    print(f"  Total Affected: {blast['total_affected']}")
    print(f"  Risk Level: {blast['risk_level']} (score: {blast['risk_score']})")
    print(f"  Affected Functions with Callers: {fn_details}")

db.close()
