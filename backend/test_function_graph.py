"""
Test script for function-based graph functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_function_endpoints():
    print("🧪 Testing Function Graph Endpoints\n")
    
    # Test 1: List all functions
    print("1️⃣ Testing GET /functions")
    try:
        response = requests.get(f"{BASE_URL}/functions")
        data = response.json()
        print(f"   ✅ Found {data.get('total', 0)} functions")
        if data.get('functions'):
            print(f"   📝 Sample: {data['functions'][0]['name']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 2: Get function graph
    print("2️⃣ Testing GET /graph/functions")
    try:
        response = requests.get(f"{BASE_URL}/graph/functions")
        data = response.json()
        print(f"   ✅ Nodes: {len(data.get('nodes', []))}")
        print(f"   ✅ Edges: {len(data.get('edges', []))}")
        
        # Show node types
        if data.get('nodes'):
            functions = [n for n in data['nodes'] if n.get('type') == 'function']
            files = [n for n in data['nodes'] if n.get('type') == 'file']
            print(f"   📊 Functions: {len(functions)}, Files: {len(files)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 3: Get specific function call chain
    print("3️⃣ Testing GET /graph/function/{name}")
    try:
        # First get a function name
        response = requests.get(f"{BASE_URL}/functions")
        functions = response.json().get('functions', [])
        
        if functions:
            func_name = functions[0]['name']
            print(f"   🔍 Testing with function: {func_name}")
            
            response = requests.get(f"{BASE_URL}/graph/function/{func_name}")
            data = response.json()
            print(f"   ✅ Call chain nodes: {len(data.get('nodes', []))}")
            print(f"   ✅ Call chain edges: {len(data.get('edges', []))}")
        else:
            print("   ⚠️  No functions found to test")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*50)
    print("✅ Function graph tests complete!")

if __name__ == "__main__":
    test_function_endpoints()
