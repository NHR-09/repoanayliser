"""Test if function calls are being extracted"""
from src.parser.static_parser import StaticParser

parser = StaticParser()

# Test with a simple Python file
test_code = """
def func_a():
    return "A"

def func_b():
    result = func_a()  # This should be detected as a call
    return result

def main():
    func_b()  # This should be detected
    func_a()  # This should be detected
"""

# Write test file
with open('test_parse.py', 'w') as f:
    f.write(test_code)

# Parse it
result = parser.parse_file('test_parse.py', 'python')

print("=== PARSED RESULT ===")
print(f"Functions found: {[f['name'] for f in result['functions']]}")
print(f"Function calls found: {result['function_calls']}")
print(f"Total calls: {len(result['function_calls'])}")

# Clean up
import os
os.remove('test_parse.py')
