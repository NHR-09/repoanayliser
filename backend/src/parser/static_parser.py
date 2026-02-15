import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser
from pathlib import Path
from typing import Dict, List

class StaticParser:
    def __init__(self):
        self.parsers = {
            'python': Parser(Language(tspython.language())),
            'javascript': Parser(Language(tsjavascript.language()))
        }
    
    def parse_file(self, file_path: str, language: str) -> Dict:
        with open(file_path, 'rb') as f:
            code = f.read()
        
        parser = self.parsers.get(language)
        if not parser:
            return {}
        
        tree = parser.parse(code)
        
        return {
            'file': file_path,
            'language': language,
            'classes': self._extract_classes(tree.root_node, code),
            'functions': self._extract_functions(tree.root_node, code),
            'imports': self._extract_imports(tree.root_node, code, language)
        }
    
    def _extract_classes(self, node, code) -> List[Dict]:
        classes = []
        if node.type == 'class_definition':
            classes.append({
                'name': self._get_node_text(node.child_by_field_name('name'), code),
                'line': node.start_point[0] + 1
            })
        for child in node.children:
            classes.extend(self._extract_classes(child, code))
        return classes
    
    def _extract_functions(self, node, code) -> List[Dict]:
        functions = []
        if node.type in ('function_definition', 'function_declaration'):
            functions.append({
                'name': self._get_node_text(node.child_by_field_name('name'), code),
                'line': node.start_point[0] + 1
            })
        for child in node.children:
            functions.extend(self._extract_functions(child, code))
        return functions
    
    def _extract_imports(self, node, code, language) -> List[str]:
        imports = []
        if language == 'python':
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(self._get_node_text(child, code))
            elif node.type == 'import_from_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(self._get_node_text(child, code))
        elif language == 'javascript' and node.type == 'import_statement':
            for child in node.children:
                if child.type == 'string':
                    imports.append(self._get_node_text(child, code).strip('"\'\''))
        for child in node.children:
            imports.extend(self._extract_imports(child, code, language))
        return imports
    
    def _get_node_text(self, node, code) -> str:
        if not node:
            return ""
        return code[node.start_byte:node.end_byte].decode('utf8')
