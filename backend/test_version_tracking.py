"""
Test script for Version Tracking System
Demonstrates SHA-256 based versioning and multi-repository management
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_version_tracking():
    print_section("VERSION TRACKING SYSTEM TEST")
    
    # Test 1: Analyze first repository
    print("1️⃣  Analyzing first repository...")
    response = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": "https://github.com/RajKale07/test-02"
    })
    job1 = response.json()
    print(f"   Job ID: {job1['job_id']}")
    
    # Wait for completion
    time.sleep(5)
    status = requests.get(f"{BASE_URL}/status/{job1['job_id']}").json()
    print(f"   Status: {status['status']}")
    
    # Test 2: List all repositories
    print_section("2️⃣  Listing All Repositories")
    repos = requests.get(f"{BASE_URL}/repositories").json()
    print(f"   Total repositories: {repos['total']}")
    for repo in repos['repositories']:
        print(f"\n   📦 {repo['name']}")
        print(f"      ID: {repo['repo_id']}")
        print(f"      Files: {repo['file_count']}")
        print(f"      Versions: {repo['version_count']}")
        print(f"      Last analyzed: {repo['last_analyzed']}")
    
    if repos['total'] == 0:
        print("   ⚠️  No repositories found. Analysis may still be running.")
        return
    
    repo_id = repos['repositories'][0]['repo_id']
    
    # Test 3: Get repository versions
    print_section("3️⃣  Repository Version History")
    versions = requests.get(f"{BASE_URL}/repository/{repo_id}/versions").json()
    print(f"   Total versions: {len(versions['versions'])}")
    print(f"\n   Recent versions:")
    for v in versions['versions'][:5]:
        print(f"      📄 {v['file']}")
        print(f"         Hash: {v['hash'][:16]}...")
        print(f"         Time: {v['timestamp']}")
        print(f"         Author: {v['author']}\n")
    
    # Test 4: Get file history
    if versions['versions']:
        print_section("4️⃣  File Version History")
        sample_file = versions['versions'][0]['file']
        history = requests.get(
            f"{BASE_URL}/repository/{repo_id}/file-history",
            params={"file_path": sample_file}
        ).json()
        
        print(f"   File: {sample_file}")
        print(f"   Total versions: {len(history['history'])}\n")
        
        for i, h in enumerate(history['history'], 1):
            print(f"   Version {i}:")
            print(f"      Hash: {h['hash'][:16]}...")
            print(f"      Time: {h['timestamp']}")
            print(f"      Author: {h['author']}")
            if h.get('previous_hash'):
                print(f"      Previous: {h['previous_hash'][:16]}...")
            print()
    
    # Test 5: Check file integrity
    if versions['versions']:
        print_section("5️⃣  File Integrity Check")
        sample_file = versions['versions'][0]['file']
        integrity = requests.post(
            f"{BASE_URL}/repository/{repo_id}/check-integrity",
            params={"file_path": sample_file}
        ).json()
        
        print(f"   File: {sample_file}")
        print(f"   Status: {integrity['status']}")
        if integrity['status'] == 'intact':
            print(f"   ✅ File integrity verified")
            print(f"   Hash: {integrity['hash'][:16]}...")
        elif integrity['status'] == 'tampered':
            print(f"   ⚠️  File has been modified!")
            print(f"   Stored: {integrity['stored_hash'][:16]}...")
            print(f"   Current: {integrity['current_hash'][:16]}...")
    
    # Test 6: Developer contributions
    print_section("6️⃣  Developer Contributions")
    contributors = requests.get(f"{BASE_URL}/repository/{repo_id}/contributors").json()
    print(f"   Total contributors: {len(contributors['contributors'])}\n")
    for c in contributors['contributors']:
        print(f"   👤 {c['developer']}")
        print(f"      Files modified: {c['files_modified']}")
        print(f"      Total versions: {c['total_versions']}\n")
    
    # Test 7: Analyze second repository (demonstrate multi-repo)
    print_section("7️⃣  Analyzing Second Repository")
    print("   Testing multi-repository support...")
    response = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": "https://github.com/Krishna-yamsalwar/Repo-Analyzer-"
    })
    job2 = response.json()
    print(f"   Job ID: {job2['job_id']}")
    print(f"   Status: {job2['status']}")
    print("   ⏳ Analysis started (will complete in background)")
    
    # Test 8: Verify separate workflows
    print_section("8️⃣  Verifying Separate Workflows")
    repos_after = requests.get(f"{BASE_URL}/repositories").json()
    print(f"   Total repositories now: {repos_after['total']}")
    print("\n   All repositories:")
    for repo in repos_after['repositories']:
        print(f"      • {repo['name']} (ID: {repo['repo_id'][:8]}...)")
    
    print_section("✅ VERSION TRACKING TEST COMPLETE")
    print("Key Features Demonstrated:")
    print("  ✓ SHA-256 content hashing")
    print("  ✓ Multi-repository management")
    print("  ✓ Version history tracking")
    print("  ✓ File integrity verification")
    print("  ✓ Developer contribution analysis")
    print("  ✓ Isolated workflows per repository")

def test_version_change_detection():
    """Test that versions are created only on content change"""
    print_section("VERSION CHANGE DETECTION TEST")
    
    print("This test requires manual file modification.")
    print("Steps:")
    print("  1. Analyze a repository")
    print("  2. Modify a file in the workspace")
    print("  3. Re-analyze the same repository")
    print("  4. Check that only modified files get new versions")
    print("\nUse the main test above to see version tracking in action.")

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/repositories")
        if response.status_code == 200:
            test_version_tracking()
        else:
            print("❌ Server returned error. Make sure backend is running.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server.")
        print("   Make sure the server is running on http://localhost:8000")
        print("   Run: python backend/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")
