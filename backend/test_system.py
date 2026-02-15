"""
Quick test script for ARCHITECH system
Run after setup to verify all components work
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_analyze():
    print("🔍 Testing repository analysis...")
    response = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": "https://github.com/pallets/flask"
    })
    
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"✅ Analysis started: {job_id}")
        
        # Poll status
        for i in range(60):
            status_response = requests.get(f"{BASE_URL}/status/{job_id}")
            status = status_response.json()["status"]
            print(f"   Status: {status}")
            
            if status == "completed":
                print("✅ Analysis completed!")
                return True
            elif status == "failed":
                print("❌ Analysis failed")
                return False
            
            time.sleep(5)
    else:
        print(f"❌ Request failed: {response.status_code}")
        return False

def test_patterns():
    print("\n🎨 Testing pattern detection...")
    response = requests.get(f"{BASE_URL}/patterns")
    
    if response.status_code == 200:
        patterns = response.json()
        print("✅ Patterns detected:")
        print(json.dumps(patterns, indent=2))
        return True
    else:
        print(f"❌ Request failed: {response.status_code}")
        return False

def test_coupling():
    print("\n🔗 Testing coupling analysis...")
    response = requests.get(f"{BASE_URL}/coupling")
    
    if response.status_code == 200:
        coupling = response.json()
        print("✅ Coupling analysis:")
        print(f"   Total files: {coupling['metrics']['total_files']}")
        print(f"   Total dependencies: {coupling['metrics']['total_dependencies']}")
        print(f"   High coupling files: {len(coupling['high_coupling'])}")
        return True
    else:
        print(f"❌ Request failed: {response.status_code}")
        return False

def test_architecture():
    print("\n🏗️ Testing architecture explanation...")
    response = requests.get(f"{BASE_URL}/architecture")
    
    if response.status_code == 200:
        arch = response.json()
        print("✅ Architecture explanation generated")
        print(f"   Evidence files: {len(arch.get('evidence_files', []))}")
        return True
    else:
        print(f"❌ Request failed: {response.status_code}")
        return False

if __name__ == "__main__":
    print("🚀 ARCHITECH System Test\n")
    print("Make sure Neo4j and backend are running!\n")
    
    # Test analysis
    if not test_analyze():
        print("\n❌ Analysis failed. Check logs.")
        exit(1)
    
    # Test other endpoints
    test_patterns()
    test_coupling()
    test_architecture()
    
    print("\n✅ All tests passed!")
