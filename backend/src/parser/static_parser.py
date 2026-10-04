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
        
        result = {
            'file': file_path,
            'language': language,
            'classes': self._extract_classes(tree.root_node, code),
            'functions': self._extract_functions(tree.root_node, code),
            'imports': self._extract_imports(tree.root_node, code, language),
            'function_calls': self._extract_function_calls(tree.root_node, code, language),
            'function_to_function_calls': self._extract_function_to_function_calls(tree.root_node, code, language)
        }
        
        # OOP-aware extraction (Python only for now)
        if language == 'python':
            result['class_methods'] = self._extract_class_methods(tree.root_node, code)
            result['self_attributes'] = self._extract_self_attributes(tree.root_node, code)
            result['method_calls'] = self._extract_method_calls(tree.root_node, code)
        
        return result
    
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
        
        def _walk(curr, current_class=None):
            if curr.type in ('class_definition', 'class_declaration'):
                cls_name = self._get_node_text(curr.child_by_field_name('name'), code)
                body = curr.child_by_field_name('body')
                if body:
                    for ch in body.children:
                        _walk(ch, current_class=cls_name)
                return
            
            # Python function
            if curr.type == 'function_definition':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                if fn_name:
                    functions.append({
                        'name': fn_name,
                        'line': curr.start_point[0] + 1,
                        'parent_class': current_class
                    })
                body = curr.child_by_field_name('body')
                if body:
                    for ch in body.children:
                        _walk(ch, current_class=current_class)
                return

            # JavaScript function declaration
            if curr.type == 'function_declaration':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                if fn_name:
                    functions.append({
                        'name': fn_name,
                        'line': curr.start_point[0] + 1,
                        'parent_class': current_class
                    })
                body = curr.child_by_field_name('body')
                if body:
                    for ch in body.children:
                        _walk(ch, current_class=current_class)
                return
            
            # JavaScript variable-assigned arrow or function expression: const foo = () => ...
            if curr.type == 'variable_declarator':
                val = curr.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression'):
                    fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                    if fn_name:
                        functions.append({
                            'name': fn_name,
                            'line': curr.start_point[0] + 1,
                            'parent_class': current_class
                        })
                    body = val.child_by_field_name('body')
                    if body:
                        for ch in body.children:
                            _walk(ch, current_class=current_class)
                    return
            
            # JavaScript class method: method_definition
            if curr.type == 'method_definition':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                if fn_name:
                    functions.append({
                        'name': fn_name,
                        'line': curr.start_point[0] + 1,
                        'parent_class': current_class
                    })
                val = curr.child_by_field_name('value') or curr
                body = val.child_by_field_name('body') if val else None
                if body:
                    for ch in body.children:
                        _walk(ch, current_class=current_class)
                return

            # JavaScript object method / property function: pair
            if curr.type == 'pair':
                val = curr.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression'):
                    fn_name = self._get_node_text(curr.child_by_field_name('key'), code)
                    if fn_name:
                        functions.append({
                            'name': fn_name,
                            'line': curr.start_point[0] + 1,
                            'parent_class': current_class
                        })
                    body = val.child_by_field_name('body')
                    if body:
                        for ch in body.children:
                            _walk(ch, current_class=current_class)
                    return

            for ch in curr.children:
                _walk(ch, current_class)

        _walk(node)
        return functions
    
    def _extract_imports(self, node, code, language) -> List[str]:
        imports = []
        if language == 'python':
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(self._get_node_text(child, code))
                    elif child.type == 'aliased_import':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            imports.append(self._get_node_text(name_node, code))
            elif node.type == 'import_from_statement':
                # In Python tree-sitter, the imported module is in field 'module_name'
                mod_node = node.child_by_field_name('module_name')
                if mod_node:
                    imports.append(self._get_node_text(mod_node, code))
                else:
                    # Fallback for relative imports e.g. from . import x
                    for child in node.children:
                        if child.type in ('dotted_name', 'relative_import'):
                            imports.append(self._get_node_text(child, code))
                            break
        elif language == 'javascript':
            if node.type == 'import_statement':
                src = node.child_by_field_name('source')
                if src:
                    imports.append(self._get_node_text(src, code).strip('"\'`'))
                else:
                    for child in node.children:
                        if child.type == 'string':
                            imports.append(self._get_node_text(child, code).strip('"\'`'))
            elif node.type == 'call_expression':
                # require('./module')
                func_n = node.child_by_field_name('function')
                if func_n and self._get_node_text(func_n, code) == 'require':
                    args = node.child_by_field_name('arguments')
                    if args:
                        for arg in args.children:
                            if arg.type == 'string':
                                imports.append(self._get_node_text(arg, code).strip('"\'`'))
        for child in node.children:
            imports.extend(self._extract_imports(child, code, language))
        return list(dict.fromkeys(imports))
    
    def _extract_function_calls(self, node, code, language) -> List[str]:
        """Extract function calls from code"""
        calls = []
        if language == 'python' and node.type == 'call':
            func_node = node.child_by_field_name('function')
            if func_node:
                if func_node.type == 'identifier':
                    calls.append(self._get_node_text(func_node, code))
                elif func_node.type == 'attribute':
                    calls.append(self._get_node_text(func_node, code).split('.')[-1])
        elif language == 'javascript' and node.type == 'call_expression':
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
    
    def _extract_function_to_function_calls(self, node, code, language) -> List[Dict]:
        """Extract which functions call which other functions, respecting scope boundaries."""
        results = []
        func_types = {'function_definition', 'function_declaration', 'arrow_function', 'function_expression', 'method_definition'}

        def _get_scoped_calls(scope_node):
            """Get function calls made directly within scope_node, stopping at nested function boundaries."""
            scoped_calls = []
            
            def _walk_calls(curr):
                if curr != scope_node and curr.type in func_types:
                    return  # Do not cross into nested function scopes
                
                if language == 'python' and curr.type == 'call':
                    func_n = curr.child_by_field_name('function')
                    if func_n:
                        if func_n.type == 'identifier':
                            scoped_calls.append(self._get_node_text(func_n, code))
                        elif func_n.type == 'attribute':
                            scoped_calls.append(self._get_node_text(func_n, code).split('.')[-1])
                elif language == 'javascript' and curr.type == 'call_expression':
                    func_n = curr.child_by_field_name('function')
                    if func_n:
                        if func_n.type == 'identifier':
                            scoped_calls.append(self._get_node_text(func_n, code))
                        elif func_n.type == 'member_expression':
                            prop = func_n.child_by_field_name('property')
                            if prop:
                                scoped_calls.append(self._get_node_text(prop, code))
                
                for ch in curr.children:
                    _walk_calls(ch)
            
            _walk_calls(scope_node)
            return scoped_calls

        def _walk_tree(curr, current_class=None):
            if curr.type in ('class_definition', 'class_declaration'):
                cls_name = self._get_node_text(curr.child_by_field_name('name'), code)
                body = curr.child_by_field_name('body')
                if body:
                    for ch in body.children:
                        _walk_tree(ch, current_class=cls_name)
                return

            fn_name = None
            fn_body = None

            if curr.type == 'function_definition':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                fn_body = curr.child_by_field_name('body') or curr
            elif curr.type == 'function_declaration':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                fn_body = curr.child_by_field_name('body') or curr
            elif curr.type == 'variable_declarator':
                val = curr.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression'):
                    fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                    fn_body = val.child_by_field_name('body') or val
            elif curr.type == 'method_definition':
                fn_name = self._get_node_text(curr.child_by_field_name('name'), code)
                val = curr.child_by_field_name('value') or curr
                fn_body = val.child_by_field_name('body') if val else None
            elif curr.type == 'pair':
                val = curr.child_by_field_name('value')
                if val and val.type in ('arrow_function', 'function_expression'):
                    fn_name = self._get_node_text(curr.child_by_field_name('key'), code)
                    fn_body = val.child_by_field_name('body') or val

            if fn_name and fn_body:
                calls = _get_scoped_calls(fn_body)
                for callee in set(calls):
                    results.append({
                        'caller': fn_name,
                        'callee': callee,
                        'caller_class': current_class
                    })
                # Recurse for nested functions inside body
                for ch in fn_body.children:
                    _walk_tree(ch, current_class=current_class)
                return

            for ch in curr.children:
                _walk_tree(ch, current_class)

        _walk_tree(node)
        return results
    
    # ─── OOP-Aware Extraction Methods ─────────────────────────────────────
    
    def _extract_class_methods(self, node, code) -> List[Dict]:
        """Extract methods with their parent class context.
        
        Returns: [{'class': 'Kernel', 'method': 'boot', 'line': 54}, ...]
        """
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type == 'function_definition':
                        method_name = self._get_node_text(child.child_by_field_name('name'), code)
                        results.append({
                            'class': class_name,
                            'method': method_name,
                            'line': child.start_point[0] + 1
                        })
        for child in node.children:
            results.extend(self._extract_class_methods(child, code))
        return results
    
    def _extract_self_attributes(self, node, code) -> List[Dict]:
        """Extract self.X = Type() assignments from __init__ methods.
        
        Resolves the right-hand-side to a type name using PEP8 convention
        (class names start with uppercase).
        
        Returns: [{'class': 'Kernel', 'attr': 'storage', 'type': 'StorageBackend'}, ...]
        """
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type == 'function_definition':
                        method_name = self._get_node_text(child.child_by_field_name('name'), code)
                        if method_name == '__init__':
                            init_body = child.child_by_field_name('body')
                            if init_body:
                                self._walk_init_for_self_attrs(init_body, class_name, code, results)
        for child in node.children:
            results.extend(self._extract_self_attributes(child, code))
        return results
    
    def _walk_init_for_self_attrs(self, node, class_name, code, results):
        """Recursively walk __init__ body to find self.X = Type() assignments.
        Handles assignments inside if/try/for blocks too."""
        for child in node.children:
            if child.type == 'expression_statement':
                # Check first child for assignment
                for expr in child.children:
                    if expr.type == 'assignment':
                        left = expr.child_by_field_name('left')
                        right = expr.child_by_field_name('right')
                        if left and left.type == 'attribute':
                            obj = left.child_by_field_name('object')
                            attr = left.child_by_field_name('attribute')
                            if obj and self._get_node_text(obj, code) == 'self' and attr:
                                attr_name = self._get_node_text(attr, code)
                                type_name = self._resolve_type_from_expr(right, code)
                                if type_name:
                                    results.append({
                                        'class': class_name,
                                        'attr': attr_name,
                                        'type': type_name
                                    })
            # Recurse into blocks (if/for/try/with bodies)
            elif child.type in ('if_statement', 'for_statement', 'try_statement',
                                'with_statement', 'block', 'elif_clause',
                                'else_clause', 'except_clause'):
                self._walk_init_for_self_attrs(child, class_name, code, results)
    
    def _resolve_type_from_expr(self, node, code) -> str:
        """Resolve the type name from a right-hand expression.
        
        Handles:
          - self.x = Foo()          → 'Foo'
          - self.x = Foo(arg1)      → 'Foo'
          - self.x = module.Foo()   → 'Foo'
        
        Uses PEP8 convention: class names start with uppercase.
        """
        if not node:
            return ""
        if node.type == 'call':
            func = node.child_by_field_name('function')
            if func:
                if func.type == 'identifier':
                    name = self._get_node_text(func, code)
                    if name and name[0].isupper():
                        return name
                elif func.type == 'attribute':
                    # module.ClassName() — take the last part
                    attr = func.child_by_field_name('attribute')
                    if attr:
                        name = self._get_node_text(attr, code)
                        if name and name[0].isupper():
                            return name
        return ""
    
    def _extract_method_calls(self, node, code) -> List[Dict]:
        """Extract self.X.method() calls with full OOP context.
        
        Returns: [{
            'caller_class': 'Kernel',
            'caller_method': 'request_seat',
            'target_attr': 'process_manager',
            'target_method': 'get_process'
        }, ...]
        """
        results = []
        if node.type == 'class_definition':
            class_name = self._get_node_text(node.child_by_field_name('name'), code)
            body = node.child_by_field_name('body')
            if body:
                for child in body.children:
                    if child.type == 'function_definition':
                        method_name = self._get_node_text(child.child_by_field_name('name'), code)
                        self._walk_for_self_method_calls(
                            child, class_name, method_name, code, results
                        )
        for child in node.children:
            results.extend(self._extract_method_calls(child, code))
        return results
    
    def _walk_for_self_method_calls(self, node, class_name, method_name, code, results):
        """Find self.X.method() call patterns within a method body.
        
        AST structure for self.process_manager.get_process(pid):
          call
            function: attribute
              object: attribute
                object: identifier "self"
                attribute: identifier "process_manager"
              attribute: identifier "get_process"
        """
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
                            'target_method': self._get_node_text(called_method, code),
                        })
        for child in node.children:
            self._walk_for_self_method_calls(child, class_name, method_name, code, results)
