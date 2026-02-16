"""Test path normalization issue"""
from pathlib import Path

# Test paths from database
relative_path = "workspace\\test-02\\TestRepo4_TightlyCoupled\\module_a.py"
absolute_path = "C:\\Users\\user\\Desktop\\ARCHITECH\\backend\\workspace\\Repo-Analyzer-\\apps\\api\\app\\models\\repository.py"

print("=== PATH NORMALIZATION TEST ===")
print(f"Relative: {relative_path}")
print(f"Resolved: {str(Path(relative_path).resolve())}")
print()
print(f"Absolute: {absolute_path}")
print(f"Resolved: {str(Path(absolute_path).resolve())}")
print()

# The issue: when create_function_call normalizes a relative path,
# it becomes absolute and won't match the File node with relative path!
print("This is the problem:")
print(f"File node has: {relative_path}")
print(f"create_function_call looks for: {str(Path(relative_path).resolve())}")
print(f"They don't match!")
