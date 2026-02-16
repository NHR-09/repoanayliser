"""Test snapshot comparison with cached data"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_snapshot_comparison():
    print("🧪 Testing Snapshot Comparison System\n")
    
    # 1. List repositories
    print("1️⃣ Fetching repositories...")
    repos = requests.get(f"{BASE_URL}/repositories").json()
    
    if not repos['repositories']:
        print("❌ No repositories found. Please analyze a repository first.")
        return
    
    repo = repos['repositories'][0]
    repo_id = repo['repo_id']
    print(f"✅ Using repository: {repo['name']} (ID: {repo_id[:8]}...)\n")
    
    # 2. List snapshots
    print("2️⃣ Fetching snapshots...")
    snapshots_resp = requests.get(f"{BASE_URL}/repository/{repo_id}/snapshots").json()
    snapshots = snapshots_resp['snapshots']
    
    if len(snapshots) < 2:
        print(f"⚠️  Only {len(snapshots)} snapshot(s) found. Need at least 2 for comparison.")
        print("   Run analysis twice to create multiple snapshots.\n")
        
        if len(snapshots) == 1:
            print("📊 Snapshot Details:")
            s = snapshots[0]
            print(f"   ID: {s['snapshot_id'][:8]}...")
            print(f"   Date: {s['created_at']}")
            print(f"   Files: {s['total_files']}")
            print(f"   Dependencies: {s['total_deps']}")
            print(f"   Avg Coupling: {s['avg_coupling']}")
            print(f"   Cycles: {s['cycle_count']}")
        return
    
    print(f"✅ Found {len(snapshots)} snapshots\n")
    
    # Display snapshots
    print("📸 Available Snapshots:")
    for i, s in enumerate(snapshots[:5], 1):
        print(f"   {i}. {s['snapshot_id'][:8]}... | {s['created_at']} | "
              f"Files: {s['total_files']} | Deps: {s['total_deps']} | "
              f"Coupling: {s['avg_coupling']:.2f}")
    print()
    
    # 3. Compare first two snapshots
    snapshot1 = snapshots[0]['snapshot_id']
    snapshot2 = snapshots[1]['snapshot_id']
    
    print(f"3️⃣ Comparing snapshots:")
    print(f"   Snapshot 1: {snapshot1[:8]}...")
    print(f"   Snapshot 2: {snapshot2[:8]}...\n")
    
    comparison = requests.get(
        f"{BASE_URL}/repository/{repo_id}/compare-snapshots/{snapshot1}/{snapshot2}"
    ).json()
    
    if 'error' in comparison:
        print(f"❌ Error: {comparison['error']}")
        return
    
    # 4. Display comparison results
    print("=" * 70)
    print("📊 SNAPSHOT COMPARISON RESULTS")
    print("=" * 70)
    
    s1 = comparison['snapshot1']
    s2 = comparison['snapshot2']
    changes = comparison['changes']
    risk = comparison['risk_assessment']
    
    print(f"\n📸 Snapshot 1 ({s1['id']}...) - {s1['date']}")
    print(f"   Files: {s1['files']} | Dependencies: {s1['dependencies']}")
    print(f"   Avg Coupling: {s1['avg_coupling']:.2f} | Cycles: {s1['cycles']}")
    print(f"   Patterns: {list(s1['patterns'].keys())}")
    
    print(f"\n📸 Snapshot 2 ({s2['id']}...) - {s2['date']}")
    print(f"   Files: {s2['files']} | Dependencies: {s2['dependencies']}")
    print(f"   Avg Coupling: {s2['avg_coupling']:.2f} | Cycles: {s2['cycles']}")
    print(f"   Patterns: {list(s2['patterns'].keys())}")
    
    print(f"\n🔄 CHANGES:")
    print(f"   File Delta: {changes['file_delta']:+d}")
    print(f"   Dependency Delta: {changes['dependency_delta']:+d}")
    print(f"   Coupling Delta: {changes['coupling_delta']:+.2f}")
    print(f"   Cycle Delta: {changes['cycle_delta']:+d}")
    
    if changes['files_added']:
        print(f"\n   ➕ Added Files ({len(changes['files_added'])}):")
        for f in changes['files_added'][:5]:
            print(f"      • {f}")
        if len(changes['files_added']) > 5:
            print(f"      ... and {len(changes['files_added']) - 5} more")
    
    if changes['files_removed']:
        print(f"\n   ➖ Removed Files ({len(changes['files_removed'])}):")
        for f in changes['files_removed'][:5]:
            print(f"      • {f}")
    
    if changes['pattern_changes']:
        print(f"\n   🏗️  Pattern Changes:")
        for pattern, change in changes['pattern_changes'].items():
            print(f"      • {pattern}: {change}")
    
    print(f"\n   📈 Coupling Analysis:")
    print(f"      Before: {changes['high_coupling_before']} highly coupled files")
    print(f"      After: {changes['high_coupling_after']} highly coupled files")
    
    print(f"\n⚠️  RISK ASSESSMENT: {risk['risk_level'].upper()}")
    if risk['risk_areas']:
        for area in risk['risk_areas']:
            print(f"   • {area}")
    else:
        print("   ✅ No significant risks detected")
    
    print(f"\n📝 Summary: {comparison['summary']}")
    
    print("\n" + "=" * 70)
    print("✅ Comparison completed successfully!")
    print("=" * 70)
    
    # 5. Test architecture comparison (if available)
    print("\n4️⃣ Testing architecture text comparison...")
    if s1['architecture'] != "Not cached" and s2['architecture'] != "Not cached":
        print("✅ Both snapshots have cached architecture explanations")
        print(f"\n   Snapshot 1 Architecture (first 200 chars):")
        print(f"   {s1['architecture'][:200]}...")
        print(f"\n   Snapshot 2 Architecture (first 200 chars):")
        print(f"   {s2['architecture'][:200]}...")
    else:
        print("⚠️  Architecture explanations not fully cached")
        print("   This is normal for older snapshots")

if __name__ == "__main__":
    try:
        test_snapshot_comparison()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
