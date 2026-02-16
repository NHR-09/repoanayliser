"""Test architectural comparison between commits"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_architecture_comparison():
    # List repositories
    print("📋 Fetching repositories...")
    repos = requests.get(f"{BASE_URL}/repositories").json()
    
    if not repos['repositories']:
        print("❌ No repositories found. Analyze a repository first.")
        return
    
    repo = repos['repositories'][0]
    repo_id = repo['repo_id']
    print(f"✓ Using repository: {repo['name']} ({repo_id})")
    
    # Get commits
    print(f"\n📜 Fetching commits for {repo_id}...")
    commits = requests.get(f"{BASE_URL}/repository/{repo_id}/commits").json()
    
    if len(commits) < 2:
        print(f"❌ Need at least 2 commits, found {len(commits)}")
        return
    
    commit1 = commits[-1]['hash']  # Oldest
    commit2 = commits[0]['hash']   # Newest
    
    print(f"✓ Comparing commits:")
    print(f"  Commit 1: {commit1[:8]} - {commits[-1]['message'][:50]}")
    print(f"  Commit 2: {commit2[:8]} - {commits[0]['message'][:50]}")
    
    # Compare architecture
    print(f"\n🔍 Comparing architectural changes...")
    result = requests.get(
        f"{BASE_URL}/repository/{repo_id}/compare-architecture/{commit1}/{commit2}"
    ).json()
    
    print(f"\n{'='*60}")
    print("📊 ARCHITECTURAL COMPARISON RESULTS")
    print(f"{'='*60}")
    print(f"Commits: {result['commit1']} → {result['commit2']}")
    print(f"\n📈 Dependency Changes:")
    print(f"  Added: {len(result['added_dependencies'])} dependencies")
    print(f"  Removed: {len(result['removed_dependencies'])} dependencies")
    print(f"  Net change: {result['dependency_delta']:+d}")
    
    print(f"\n🔗 Coupling Metrics:")
    print(f"  Before: {result['coupling_before']:.2f}")
    print(f"  After: {result['coupling_after']:.2f}")
    print(f"  Delta: {result['coupling_delta']:+.2f}")
    
    print(f"\n🔄 Circular Dependencies:")
    print(f"  Before: {result['cycles_before']}")
    print(f"  After: {result['cycles_after']}")
    
    if result['risk_areas']:
        print(f"\n⚠️  Risk Areas:")
        for risk in result['risk_areas']:
            print(f"  • {risk}")
    else:
        print(f"\n✅ No significant risks detected")
    
    if result['added_dependencies']:
        print(f"\n➕ Sample Added Dependencies (showing first 5):")
        for src, tgt in result['added_dependencies'][:5]:
            print(f"  {src.split('/')[-1]} → {tgt.split('/')[-1]}")
    
    if result['removed_dependencies']:
        print(f"\n➖ Sample Removed Dependencies (showing first 5):")
        for src, tgt in result['removed_dependencies'][:5]:
            print(f"  {src.split('/')[-1]} → {tgt.split('/')[-1]}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    try:
        test_architecture_comparison()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")
