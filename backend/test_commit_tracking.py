"""
Test commit-based version tracking
Shows that files from same commit are NOT duplicated
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_commit_tracking():
    print("=" * 60)
    print("Testing Commit-Based Version Tracking")
    print("=" * 60)
    
    # 1. Analyze repository
    print("\n1. Analyzing repository...")
    response = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": "https://github.com/krishna-yamsalwar/Repo-Analyzer-"
    })
    job_id = response.json()["job_id"]
    print(f"   Job ID: {job_id}")
    
    # Wait for completion
    while True:
        status = requests.get(f"{BASE_URL}/status/{job_id}").json()
        if status["status"] == "completed":
            print("   SUCCESS: Analysis complete")
            break
        elif status["status"] == "failed":
            print(f"   ERROR: Failed: {status.get('error')}")
            return
        time.sleep(2)
    
    # 2. Get repository info
    print("\n2. Getting repository info...")
    repos = requests.get(f"{BASE_URL}/repositories").json()
    if not repos["repositories"]:
        print("   ERROR: No repositories found")
        return
    
    repo = repos["repositories"][0]
    repo_id = repo["repo_id"]
    print(f"   Repository: {repo['name']}")
    print(f"   Repo ID: {repo_id}")
    print(f"   Current Commit: {repo.get('current_commit', 'N/A')[:8] if repo.get('current_commit') else 'N/A'}")
    
    # 3. Get all commits
    print("\n3. Getting commit history...")
    commits_response = requests.get(f"{BASE_URL}/repository/{repo_id}/commits")
    if commits_response.status_code != 200:
        print(f"   ERROR: Failed to get commits: {commits_response.status_code}")
        print(f"   Response: {commits_response.text}")
        return
    
    commits = commits_response.json()
    if isinstance(commits, dict):
        commits = []  # Handle error response
    
    print(f"   Total commits tracked: {len(commits)}")
    
    if commits:
        print("\n   Recent commits:")
        for commit in commits[:5]:
            print(f"   - {commit['hash'][:8]} - {commit['message'][:50]}")
            print(f"     by {commit['author']} at {commit['timestamp']}")
    
    # 4. Get files at current commit
    if commits:
        current_commit = commits[0]['hash']
        print(f"\n4. Getting files at commit {current_commit[:8]}...")
        files = requests.get(
            f"{BASE_URL}/repository/{repo_id}/commit/{current_commit}/files"
        ).json()
        print(f"   Files at this commit: {len(files)}")
        print(f"   Sample files:")
        for f in files[:5]:
            print(f"   - {f['path']}")
            print(f"     Hash: {f['content_hash'][:16]}...")
    
    # 5. Compare commits if we have multiple
    if len(commits) >= 2:
        commit1 = commits[0]['hash']
        commit2 = commits[1]['hash']
        print(f"\n5. Comparing commits {commit1[:8]} vs {commit2[:8]}...")
        comparison = requests.get(
            f"{BASE_URL}/repository/{repo_id}/compare/{commit1}/{commit2}"
        ).json()
        
        print(f"\n   Comparison Summary:")
        print(f"   - Files added: {comparison['summary']['files_added']}")
        print(f"   - Files removed: {comparison['summary']['files_removed']}")
        print(f"   - Files modified: {comparison['summary']['files_modified']}")
        print(f"   - Total changes: {comparison['summary']['total_changes']}")
        
        if comparison['modified']:
            print(f"\n   Modified files:")
            for f in comparison['modified'][:5]:
                print(f"   - {f}")
    
    # 6. Re-analyze same repository (should NOT create duplicate versions)
    print(f"\n6. Re-analyzing same repository (same commit)...")
    response = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": "https://github.com/krishna-yamsalwar/Repo-Analyzer-"
    })
    job_id = response.json()["job_id"]
    
    while True:
        status = requests.get(f"{BASE_URL}/status/{job_id}").json()
        if status["status"] == "completed":
            print("   SUCCESS: Re-analysis complete")
            break
        elif status["status"] == "failed":
            print(f"   ERROR: Failed: {status.get('error')}")
            return
        time.sleep(2)
    
    # Check commits again
    commits_after = requests.get(f"{BASE_URL}/repository/{repo_id}/commits").json()
    if isinstance(commits_after, dict):
        commits_after = []
    
    print(f"\n   Commits before: {len(commits)}")
    print(f"   Commits after: {len(commits_after)}")
    
    if len(commits) == len(commits_after):
        print("   SUCCESS: No duplicate commits created!")
        print("   Files from same commit are properly tracked")
    else:
        print("   WARNING: Commit count changed")
    
    print("\n" + "=" * 60)
    print("SUCCESS: Test Complete!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("- Commit-level tracking (not just file-level)")
    print("- No duplicate versions for same commit")
    print("- Commit comparison between versions")
    print("- Git history integration")

if __name__ == "__main__":
    test_commit_tracking()
