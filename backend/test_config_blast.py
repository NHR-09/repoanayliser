"""Test blast radius with config.py"""
import sys
sys.path.append('src')

from graph.graph_db import GraphDB
from graph.dependency_mapper import DependencyMapper
from graph.blast_radius import BlastRadiusAnalyzer

def test():
    graph_db = GraphDB("neo4j://127.0.0.1:7687", "neo4j", "12410946")
    
    with graph_db.driver.session() as session:
        repo_id = session.run("MATCH (r:Repository) RETURN r.repo_id as id LIMIT 1").single()['id']
        
        # Test with config.py (has 8 dependents)
        test_file = "workspace\\Repo-Analyzer-\\apps\\api\\app\\core\\config.py"
        
        print(f"Testing: {test_file.split('\\\\')[-1]}")
        print("=" * 80)
        
        dep_mapper = DependencyMapper()
        analyzer = BlastRadiusAnalyzer(dep_mapper, graph_db)
        
        result = analyzer.analyze(test_file, "modify", repo_id)
        
        print(f"\nDirect dependents: {len(result['direct_dependents'])}")
        for d in result['direct_dependents']:
            print(f"  - {d.split('\\\\')[-1]}")
        
        print(f"\nIndirect dependents: {len(result['indirect_dependents'])}")
        for d in result['indirect_dependents'][:5]:
            print(f"  - {d.split('\\\\')[-1]}")
        
        print(f"\nRisk: {result['risk_level']} ({result['risk_score']}/100)")

if __name__ == "__main__":
    test()
