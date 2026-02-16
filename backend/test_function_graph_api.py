"""Test function graph endpoint"""
import requests

response = requests.get("http://localhost:8000/graph/functions")
data = response.json()

print(f"Nodes: {len(data['nodes'])}")
print(f"Edges: {len(data['edges'])}")

if data['edges']:
    print("\nSample edges:")
    for edge in data['edges'][:5]:
        print(f"  {edge['source']} -> {edge['target']}")
else:
    print("\n⚠️ No edges found!")
