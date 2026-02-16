from src.parser.static_parser import StaticParser

parser = StaticParser()

test_file = "workspace\\test-02\\TestRepo4_TightlyCoupled\\module_a.py"

print(f"Parsing: {test_file}")
result = parser.parse_file(test_file, "python")

print(f"\nFunctions found: {len(result.get('functions', []))}")
for func in result.get('functions', []):
    print(f"  - {func['name']} at line {func['line']}")

print(f"\nFunction calls found: {len(result.get('function_calls', []))}")
for call in set(result.get('function_calls', [])):
    print(f"  - {call}")
