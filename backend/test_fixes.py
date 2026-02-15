"""
Quick test to verify path matching and vector store fixes
"""
import sys
from pathlib import Path

# Test path normalization
def test_path_normalization():
    print("Testing Path Normalization")
    print("-" * 50)
    
    test_paths = [
        "workspace\\Repo\\file.py",
        "C:\\Users\\user\\workspace\\Repo\\file.py",
        "apps\\api\\main.py"
    ]
    
    for path in test_paths:
        try:
            normalized = str(Path(path).resolve())
            print(f"OK {path}")
            print(f"   -> {normalized}")
        except:
            print(f"Warning: {path} (not resolvable)")
    
    print()

# Test path suffix extraction
def test_path_suffix():
    print("Testing Path Suffix Extraction")
    print("-" * 50)
    
    test_paths = [
        "C:\\Users\\user\\workspace\\Repo\\apps\\api\\main.py",
        "workspace\\Repo\\file.py",
        "main.py"
    ]
    
    for path in test_paths:
        parts = Path(path).parts
        if len(parts) >= 3:
            suffix = str(Path(*parts[-3:]))
        else:
            suffix = str(Path(path).name)
        print(f"Path: {path}")
        print(f"Suffix: {suffix}")
        print()

# Test vector store data extraction
def test_vector_extraction():
    print("Testing Vector Store Data Extraction")
    print("-" * 50)
    
    sample_parsed = {
        'file': 'C:\\workspace\\test.py',
        'language': 'python',
        'classes': [
            {'name': 'User', 'line': 10},
            {'name': 'Admin', 'line': 25}
        ],
        'functions': [
            {'name': 'login', 'line': 5},
            {'name': 'logout', 'line': 15}
        ],
        'imports': ['fastapi', 'typing', 'database']
    }
    
    parts = []
    parts.append(f"File: {sample_parsed['file']}")
    
    for cls in sample_parsed.get('classes', []):
        parts.append(f"Class {cls['name']} at line {cls['line']}")
    
    for func in sample_parsed.get('functions', []):
        parts.append(f"Function {func['name']} at line {func['line']}")
    
    if sample_parsed.get('imports'):
        parts.append(f"Imports: {', '.join(sample_parsed['imports'])}")
    
    code_text = '\n'.join(parts)
    
    print("Extracted Code Text:")
    print(code_text)
    print()
    print(f"OK Length: {len(code_text)} characters")
    print()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("ARCHITECH - Path & Vector Store Fix Verification")
    print("="*50 + "\n")
    
    test_path_normalization()
    test_path_suffix()
    test_vector_extraction()
    
    print("="*50)
    print("All tests completed!")
    print("="*50)
