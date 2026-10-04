import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser
from typing import Dict, List


class StaticParser:
    JS_LANGUAGES = {'javascript', 'typescript', 'tsx'}
    JS_FUNCTION_NODES = {
        'function_declaration', 'method_definition', 'arrow_function',
        'function_expression'
    }

    def __init__(self):
        self.parsers = {
            'python': Parser(Language(tspython.language())),
            'javascript': Parser(Language(tsjavascript.language())),
            'typescript': Parser(Language(tstypescript.language_typescript())),
            'tsx': Parser(Language(tstypescript.language_tsx()))
        }

    def parse_file(self, file_path: str, language: str) -> Dict:
        with open(file_path, 'rb') as f:
            code = f.read()

        parser = self.parsers.get(language)
        if not parser:
            return {}

        tree = parser.parse(code)
        result = {
            'file': file_path,
            'language': language,
            'classes': self._extract_classes(tree.root_node, code),
            'functions': self._extract_functions(tree.root_node, code),
            'imports': self._extract_imports(tree.root_node, code, language),
            'function_calls': self._extract_function_calls(tree.root_node, code, language),
            'function_to_function_calls': self._extract_function_to_function_calls(
                tree.root_node, code, language
            )
        }
        if language == 'python':
            result['class_methods'] = self._extract_class_methods(tree.root_node, code)
            result['self_attributes'] = self._extract_self_attributes(tree.root_node, code)
            result['method_calls'] = self._extract_method_calls(tree.root_node, code)
        return result

    def _extract_classes(self, node, code) -> List[Dict]:
        classes = []
        if node.type in ('class_definition', 'class_declaration'):
            classes.append({
                'name': self._get_node_text(node.child_by_field_name('name'), code),
                'line': node.start_point[0] + 1
            })
        for child in node.children:
            classes.extend(self._extract_classes(child, code))
        return classes

    def _extract_functions(self, node, code) -> List[Dict]:
        functions = []
        name = self._get_function_name(node, code)
        if name:
            functions.append({'name': name, 'line': node.start_point[0] + 1})
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
        elif language in self.JS_LANGUAGES and node.type in ('import_statement', 'export_statement'):
            source = node.child_by_field_name('source')
            if source and source.type == 'string':
                imports.append(self._get_node_text(source, code).strip('"\''))
            else:
                for child in node.children:
                    if child.type == 'string':
                        imports.append(self._get_node_text(child, code).strip('"\''))
        for child in node.children:
            imports.extend(self._extract_imports(child, code, language))
        return imports

    def _extract_function_calls(self, node, code, language) -> List[str]:
        """Extract function calls from code."""
        calls = []
        if language == 'python' and node.type == 'call':
            func_node = node.child_by_field_name('function')
            if func_node:
                if func_node.type == 'identifier':
                    calls.append(self._get_node_text(func_node, code))
                elif func_node.type == 'attribute':
                    calls.append(self._get_node_text(func_node, code).split('.')[-1])
        elif language in self.JS_LANGUAGES and node.type == 'call_expression':
            func_node = node.child_by_field_name('function')
            if func_node:
                if func_node.type == 'identifier':
                    calls.append(self._get_node_text(func_node, code))
                elif func_node.type == 'member_expression':
                    prop = func_node.child_by_field_name('property')
                    if prop:
                        calls.append(self._get_node_text(prop, code))
        for child in node.children:
            calls.extend(self._extract_function_calls(child, code, language))
        return calls

    def _get_node_text(self, node, code) -> str:
        if not node:
            return ""
        return code[node.start_byte:node.end_byte].decode('utf8')

    def _get_function_name(self, node, code) -> str:
        """Return the declared name for Python/JS/TS functions and methods."""
        if node.type in ('function_definition', 'function_declaration', 'method_definition'):
            return self._get_node_text(node.child_by_field_name('name'), code)

        if node.type in ('arrow_function', 'function_expression'):
            parent = node.parent
            if parent and parent.type in ('variable_declarator', 'pair', 'field_definition'):
                return self._get_node_text(parent.child_by_field_name('name'), code)

        return ''

    def _extract_function_to_function_calls(self, node, code, language) -> List[Dict]:
        """Extract which functions call which other functions."""
        result = []
        if language == 'python' and node.type == 'function_definition':
            func_name = self._get_node_text(node.child_by_field_name('name'), code)
            calls = self._extract_function_calls(node, code, language)
            for called in set(calls):
                if called != func_name:
                    result.append({'caller': func_name, 'callee': called})
        elif language in self.JS_LANGUAGES:
            func_name = self._get_function_name(node, code)
            if func_name:
                calls = self._extract_function_calls(node, code, language)
                for called in set(calls):
                    if called != func_name:
                        result.append({'caller': func_name, 'callee': called})

        for child in node.children:
            result.extend(self._extract_function_to_function_calls(child, code, language))
        return result

    def _extract_class_methods(self, node, code) -> List[Dict]:
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type == 'function_definition':
                        results.append({
                            'class': class_name,
                            'method': self._get_node_text(
                                child.child_by_field_name('name'), code
                            ),
                            'line': child.start_point[0] + 1
                        })
        for child in node.children:
            results.extend(self._extract_class_methods(child, code))
        return results

    def _extract_self_attributes(self, node, code) -> List[Dict]:
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type != 'function_definition':
                        continue
                    method_name = self._get_node_text(
                        child.child_by_field_name('name'), code
                    )
                    if method_name == '__init__':
                        init_body = child.child_by_field_name('body')
                        if init_body:
                            self._walk_init_for_self_attrs(
                                init_body, class_name, code, results
                            )
        for child in node.children:
            results.extend(self._extract_self_attributes(child, code))
        return results

    def _walk_init_for_self_attrs(self, node, class_name, code, results):
        for child in node.children:
            if child.type == 'expression_statement':
                for expression in child.children:
                    if expression.type != 'assignment':
                        continue
                    left = expression.child_by_field_name('left')
                    right = expression.child_by_field_name('right')
                    if not left or left.type != 'attribute':
                        continue
                    obj = left.child_by_field_name('object')
                    attr = left.child_by_field_name('attribute')
                    if obj and attr and self._get_node_text(obj, code) == 'self':
                        type_name = self._resolve_type_from_expr(right, code)
                        if type_name:
                            results.append({
                                'class': class_name,
                                'attr': self._get_node_text(attr, code),
                                'type': type_name
                            })
            elif child.type in (
                'if_statement', 'for_statement', 'try_statement',
                'with_statement', 'block', 'elif_clause', 'else_clause',
                'except_clause'
            ):
                self._walk_init_for_self_attrs(child, class_name, code, results)

    def _resolve_type_from_expr(self, node, code) -> str:
        if not node or node.type != 'call':
            return ''
        func = node.child_by_field_name('function')
        if not func:
            return ''
        if func.type == 'identifier':
            name = self._get_node_text(func, code)
        elif func.type == 'attribute':
            name = self._get_node_text(func.child_by_field_name('attribute'), code)
        else:
            return ''
        return name if name and name[0].isupper() else ''

    def _extract_method_calls(self, node, code) -> List[Dict]:
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type == 'function_definition':
                        method_name = self._get_node_text(
                            child.child_by_field_name('name'), code
                        )
                        self._walk_for_self_method_calls(
                            child, class_name, method_name, code, results
                        )
        for child in node.children:
            results.extend(self._extract_method_calls(child, code))
        return results

    def _walk_for_self_method_calls(
        self, node, class_name, method_name, code, results
    ):
        if node.type == 'call':
            func_node = node.child_by_field_name('function')
            if func_node and func_node.type == 'attribute':
                called_method = func_node.child_by_field_name('attribute')
                obj = func_node.child_by_field_name('object')
                if called_method and obj and obj.type == 'attribute':
                    inner_obj = obj.child_by_field_name('object')
                    target_attr = obj.child_by_field_name('attribute')
                    if (inner_obj and target_attr and
                            self._get_node_text(inner_obj, code) == 'self'):
                        results.append({
                            'caller_class': class_name,
                            'caller_method': method_name,
                            'target_attr': self._get_node_text(target_attr, code),
                            'target_method': self._get_node_text(called_method, code)
                        })
        for child in node.children:
            self._walk_for_self_method_calls(
                child, class_name, method_name, code, results
            )
