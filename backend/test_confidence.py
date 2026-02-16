"""
Test script for Confidence & Limitations System (Part 3)
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_confidence_report():
    """Test the /confidence-report endpoint"""
    print("\n" + "="*60)
    print("TESTING PART 3: CONFIDENCE & LIMITATIONS SYSTEM")
    print("="*60 + "\n")
    
    # Step 1: Analyze a test repository
    print("Step 1: Analyzing repository...")
    analysis_response = requests.post(
        f"{BASE_URL}/analyze",
        json={"repo_url": "https://github.com/RajKale07/test-02"}
    )
    
    if analysis_response.status_code != 200:
        print(f"❌ Failed to start analysis: {analysis_response.text}")
        return False
    
    data = analysis_response.json()
    job_id = data.get('job_id')
    print(f"✅ Analysis started (Job ID: {job_id})")
    
    # Step 2: Wait for analysis to complete
    print("\nStep 2: Waiting for analysis to complete...")
    max_wait = 60  # 60 seconds
    waited = 0
    
    while waited < max_wait:
        status_response = requests.get(f"{BASE_URL}/status/{job_id}")
        status_data = status_response.json()
        
        if status_data.get('status') == 'completed':
            print(f"✅ Analysis completed in {waited} seconds")
            break
        elif status_data.get('status') == 'failed':
            print(f"❌ Analysis failed: {status_data.get('error')}")
            return False
        
        time.sleep(2)
        waited += 2
        print(f"   ... waiting ({waited}s)")
    
    if waited >= max_wait:
        print(f"❌ Analysis timed out after {max_wait} seconds")
        return False
    
    # Step 3: Get confidence report
    print("\nStep 3: Retrieving confidence report...")
    confidence_response = requests.get(f"{BASE_URL}/confidence-report")
    
    if confidence_response.status_code != 200:
        print(f"❌ Failed to get confidence report: {confidence_response.text}")
        return False
    
    report = confidence_response.json()
    
    # Step 4: Validate report structure
    print("\nStep 4: Validating report structure...")
    
    if 'claims' not in report:
        print("❌ Report missing 'claims' field")
        return False
    
    claims = report['claims']
    
    if not claims or len(claims) == 0:
        print("❌ No claims in report")
        return False
    
    print(f"✅ Report contains {len(claims)} claims")
    
    # Step 5: Validate claim structure
    print("\nStep 5: Validating claim structure...")
    required_fields = ['claim', 'confidence', 'reasoning', 'failure_scenario']
    
    all_valid = True
    for i, claim in enumerate(claims):
        missing = [f for f in required_fields if f not in claim]
        if missing:
            print(f"❌ Claim {i+1} missing fields: {missing}")
            all_valid = False
        else:
            conf = claim['confidence']
            if not (0.0 <= conf <= 1.0):
                print(f"❌ Claim {i+1} has invalid confidence: {conf}")
                all_valid = False
    
    if all_valid:
        print(f"✅ All claims have required fields")
    
    # Step 6: Display confidence report
    print("\n" + "="*60)
    print("CONFIDENCE REPORT")
    print("="*60 + "\n")
    
    for i, claim in enumerate(claims, 1):
        print(f"Claim {i}: {claim['claim']}")
        print(f"  Confidence: {claim['confidence']:.2f}")
        print(f"  Reasoning: {claim['reasoning']}")
        print(f"  Failure Scenario: {claim['failure_scenario']}")
        if 'evidence' in claim and claim['evidence']:
            print(f"  Evidence: {len(claim['evidence'])} files")
        print()
    
    if 'summary' in report:
        print(f"Summary: {report['summary']}\n")
    
    # Step 7: Final validation
    print("="*60)
    print("VALIDATION RESULTS")
    print("="*60 + "\n")
    
    checks = [
        ("Report has claims", len(claims) >= 2),
        ("All claims have confidence scores", all(0 <= c['confidence'] <= 1 for c in claims)),
        ("All claims have reasoning", all('reasoning' in c and c['reasoning'] for c in claims)),
        ("All claims have failure scenarios", all('failure_scenario' in c and c['failure_scenario'] for c in claims)),
        ("Average confidence is reasonable", 0.5 <= sum(c['confidence'] for c in claims) / len(claims) <= 1.0)
    ]
    
    passed = 0
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("\n🎉 CONFIDENCE SYSTEM TEST: SUCCESS")
        return True
    else:
        print("\n⚠️ CONFIDENCE SYSTEM TEST: PARTIAL SUCCESS")
        return False

if __name__ == "__main__":
    print("\n🚀 Starting Confidence & Limitations System Test")
    print("Make sure the backend server is running on http://localhost:8000\n")
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 404:  # FastAPI returns 404 for root if no route defined
            print("✅ Server is running")
        
        success = test_confidence_report()
        
        if success:
            print("\n✅ All tests passed! Part 3 implementation is complete.")
        else:
            print("\n⚠️ Some tests failed. Please review the output above.")
    
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:8000")
        print("Please start the server with: python main.py")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
