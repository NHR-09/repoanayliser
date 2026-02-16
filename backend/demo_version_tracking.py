"""
Demonstration: Git Commit History as Version Tracking
Shows how versions accumulate from git commits
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def analyze_repo(repo_url):
    """Analyze repository and wait for completion"""
    response = requests.post(f"{BASE_URL}/analyze", json={"repo_url": repo_url})
    job_id = response.json()['job_id']
    print(f"   Job ID: {job_id}")
    print("   Waiting for completion...")
    
    time.sleep(10)
    
    status = requests.get(f"{BASE_URL}/status/{job_id}").json()
    print(f"   Status: {status['status']}")
    return status

def main():
    print_section("VERSION TRACKING DEMONSTRATION")
    
    repo_url = "https://github.com/RajKale07/test-02"
    
    print("SCENARIO: Tracking Git commit history as versions")
    print(f"Repository: {repo_url}\n")
    
    # Analysis with git history import
    print_section("STEP 1: Analyze Repository with Git History")
    print("This imports git commits and creates versions for each file change")
    analyze_repo(repo_url)
    
    # Get stats
    repos = requests.get(f"{BASE_URL}/repositories").json()
    if repos['repositories']:
        repo = repos['repositories'][0]
        repo_id = repo['repo_id']
        print(f"\n   Repository: {repo['name']}")
        print(f"   Files: {repo['file_count']}")
        print(f"   Versions: {repo['version_count']}")
        ratio = repo['version_count'] / repo['file_count'] if repo['file_count'] > 0 else 0
        print(f"   Ratio: {ratio:.2f} versions per file")
        
        if repo['version_count'] > repo['file_count']:
            print(f"\n   ✅ SUCCESS! Versions ({repo['version_count']}) > Files ({repo['file_count']})")
            print(f"   Git commit history successfully imported!")
        else:
            print(f"\n   ⚠ Repository has no git history or only 1 commit per file")
    
    print_section("STEP 2: Version Details")
    versions = requests.get(f"{BASE_URL}/repository/{repo_id}/versions").json()
    print(f"Total versions: {len(versions['versions'])}\n")
    
    # Group by file to show version count per file
    file_versions = {}
    for v in versions['versions']:
        file_path = v['file']
        if file_path not in file_versions:
            file_versions[file_path] = []
        file_versions[file_path].append(v)
    
    print("Versions per file:")
    for file_path, versions_list in list(file_versions.items())[:5]:
        filename = file_path.split('\\')[-1]
        print(f"   {filename}: {len(versions_list)} version(s)")
    
    # Show file history example
    if file_versions:
        print("\n" + "="*70)
        print("  Example: File Version History")
        print("="*70 + "\n")
        
        sample_file = list(file_versions.keys())[0]
        history = requests.get(
            f"{BASE_URL}/repository/{repo_id}/file-history",
            params={"file_path": sample_file}
        ).json()
        
        if history.get('history'):
            filename = sample_file.split('\\')[-1]
            print(f"File: {filename}")
            print(f"Total versions: {len(history['history'])}\n")
            for i, v in enumerate(history['history'][:3], 1):
                print(f"  Version {i}:")
                print(f"    Hash: {v['hash'][:12]}...")
                print(f"    Author: {v.get('author', 'system')}")
                print(f"    Message: {v.get('message', 'N/A')}")
                print()
    
    print_section("SUMMARY")
    print("""
    Version Tracking System:
    
    ✓ Imports git commit history automatically
    ✓ Each commit creates versions for changed files
    ✓ Uses SHA-256 content hashing for integrity
    ✓ Tracks author and commit message
    ✓ Builds version lineage (PREVIOUS_VERSION links)
    
    Result:
    - Files with multiple commits = multiple versions
    - Versions > Files (proper commit tracking)
    - Complete history preserved across re-analysis
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
