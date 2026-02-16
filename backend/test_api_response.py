"""Test API endpoint response"""
import sys
sys.path.append('src')

from src.analysis_engine import AnalysisEngine

def test_api():
    engine = AnalysisEngine()
    
    # Load the current repo
    with engine.graph_db.driver.session() as session:
        repo = session.run("MATCH (r:Repository) RETURN r.repo_id as id, r.path as path LIMIT 1").single()
        if not repo:
            print("[ERROR] No repo!")
            return
        
        repo_id = repo['id']
        repo_path = repo['path']
    
    # Set current repo
    engine.current_repo_id = repo_id
    engine.repo_path = repo_path
    
    # Rebuild analyzers
    engine.load_repository_analysis(repo_id)
    
    print("=" * 80)
    print("TEST: API analyze_change_impact()")
    print("=" * 80)
    
    # Test with config.py (known to have 8 dependents)
    test_file = "workspace\\Repo-Analyzer-\\apps\\api\\app\\core\\config.py"
    
    print(f"\nTesting: {test_file}")
    print(f"Current repo_id: {engine.current_repo_id}")
    
    result = engine.analyze_change_impact(test_file, "modify")
    
    print(f"\n[RESULT]")
    print(f"  File: {result.get('file', 'N/A')}")
    print(f"  Change type: {result.get('change_type', 'N/A')}")
    print(f"  Direct dependents: {len(result.get('direct_dependents', []))}")
    print(f"  Indirect dependents: {len(result.get('indirect_dependents', []))}")
    print(f"  Total affected: {result.get('total_affected', 0)}")
    print(f"  Risk level: {result.get('risk_level', 'N/A')}")
    print(f"  Risk score: {result.get('risk_score', 0)}")
    
    if result.get('direct_dependents'):
        print(f"\n  Direct deps:")
        for d in result['direct_dependents'][:5]:
            print(f"    - {d.split('\\\\')[-1]}")
    
    # Test with relative path (what frontend might send)
    print(f"\n{'=' * 80}")
    print("TEST: With relative path")
    print(f"{'=' * 80}")
    
    relative_path = "apps/api/app/core/config.py"
    print(f"\nTesting: {relative_path}")
    
    result2 = engine.analyze_change_impact(relative_path, "modify")
    
    print(f"\n[RESULT]")
    print(f"  Direct dependents: {len(result2.get('direct_dependents', []))}")
    print(f"  Indirect dependents: {len(result2.get('indirect_dependents', []))}")
    print(f"  Total affected: {result2.get('total_affected', 0)}")

if __name__ == "__main__":
    test_api()
