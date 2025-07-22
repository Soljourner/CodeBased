"""
Python AST parser for CodeBased.
"""

import ast
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union

from .base import BaseParser, ParsedEntity, ParsedRelationship, ParseResult

logger = logging.getLogger(__name__)


class PythonASTParser(BaseParser):
    """Python AST parser implementation."""
    
    SUPPORTED_EXTENSIONS = {'.py'}
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Python file."""
        return Path(file_path).suffix in self.SUPPORTED_EXTENSIONS
    
    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a Python file using AST.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            ParseResult with entities and relationships
        """
        start_time = time.time()
        entities = []
        relationships = []
        errors = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            
            # Parse AST
            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as e:
                error_msg = f"Syntax error in {file_path}:{e.lineno}: {e.msg}"
                logger.error(error_msg)
                errors.append(error_msg)
                return ParseResult([], [], file_hash, file_path, errors, time.time() - start_time)
            
            # Create parser visitor
            visitor = PythonASTVisitor(file_path, content.splitlines())
            visitor.visit(tree)
            
            entities = visitor.entities
            relationships = visitor.relationships
            errors = visitor.errors
            
        except Exception as e:
            error_msg = f"Failed to parse {file_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            file_hash = ""
        
        parse_time = time.time() - start_time
        return ParseResult(entities, relationships, file_hash, file_path, errors, parse_time)


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting entities and relationships."""
    
    def __init__(self, file_path: str, lines: List[str]):
        """
        Initialize visitor.
        
        Args:
            file_path: Path to the file being parsed
            lines: List of file lines for context
        """
        self.file_path = file_path
        self.lines = lines
        self.entities: List[ParsedEntity] = []
        self.relationships: List[ParsedRelationship] = []
        self.errors: List[str] = []
        
        # Context stacks for tracking nested structures
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self.current_module: Optional[str] = None
        
        # Track entity IDs for relationship creation
        self.entity_ids: Dict[str, str] = {}
        
        # Track imports
        self.imports: Dict[str, str] = {}  # module_name -> alias
        
        # Track name context hierarchy for unique ID generation
        self.class_name_stack: List[str] = []
        self.function_name_stack: List[str] = []
        self.module_name: str = Path(self.file_path).stem
        
        # Initialize with file entity
        self._create_file_entity()
    
    def _create_file_entity(self):
        """Create the file entity."""
        file_path_obj = Path(self.file_path)
        file_id = self._generate_id("file", self.file_path, 1)
        
        file_entity = ParsedEntity(
            id=file_id,
            name=file_path_obj.name,
            type="File",
            file_path=self.file_path,
            line_start=1,
            line_end=len(self.lines),
            metadata={
                "path": self.file_path,
                "extension": file_path_obj.suffix,
                "size": len('\n'.join(self.lines)),
                "lines_of_code": len([line for line in self.lines if line.strip() and not line.strip().startswith('#')])
            }
        )
        
        self.entities.append(file_entity)
        self.entity_ids['file'] = file_id
    
    def visit_Module(self, node: ast.Module) -> None:
        """Visit module node."""
        file_path_obj = Path(self.file_path)
        module_name = file_path_obj.stem
        module_id = self._generate_id("module", module_name, 1)
        
        # Get module docstring
        docstring = self._get_docstring(node)
        
        module_entity = ParsedEntity(
            id=module_id,
            name=module_name,
            type="Module",
            file_path=self.file_path,
            line_start=1,
            line_end=len(self.lines),
            metadata={
                "docstring": docstring,
                "file_id": self.entity_ids['file']
            }
        )
        
        self.entities.append(module_entity)
        self.entity_ids['module'] = module_id
        self.current_module = module_id
        
        # Create FILE_CONTAINS_MODULE relationship
        self._create_relationship(
            self.entity_ids['file'],
            module_id,
            "FILE_CONTAINS_MODULE"
        )
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        # Add to name context before generating ID
        self.class_name_stack.append(node.name)
        
        class_id = self._generate_id("class", node.name, node.lineno)
        parent_class = self.current_class
        self.current_class = class_id
        
        # Get class metadata
        docstring = self._get_docstring(node)
        is_abstract = self._is_abstract_class(node)
        
        class_entity = ParsedEntity(
            id=class_id,
            name=node.name,
            type="Class",
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=self._get_end_line(node),
            metadata={
                "docstring": docstring,
                "is_abstract": is_abstract,
                "file_id": self.entity_ids['file'],
                "module_id": self.current_module,
                "parent_class": parent_class
            }
        )
        
        self.entities.append(class_entity)
        self.entity_ids[f"class:{node.name}"] = class_id
        
        # Create appropriate CONTAINS relationship
        if parent_class:
            self._create_relationship(parent_class, class_id, "CLASS_CONTAINS_CLASS")  # For nested classes
        elif self.current_module:
            self._create_relationship(self.current_module, class_id, "MODULE_CONTAINS_CLASS")
            # Also create direct file relationship for better visualization
            self._create_relationship(self.entity_ids['file'], class_id, "FILE_CONTAINS_CLASS")
        else:
            self._create_relationship(self.entity_ids['file'], class_id, "FILE_CONTAINS_CLASS")
        
        # Handle inheritance
        for base in node.bases:
            base_name = self._get_name_from_node(base)
            if base_name:
                # Create INHERITS relationship (will be resolved in second pass)
                self._create_relationship(
                    class_id,
                    f"unresolved:{base_name}",
                    "INHERITS"
                )
        
        # Visit class body
        self.generic_visit(node)
        
        # Restore context
        self.current_class = parent_class
        self.class_name_stack.pop()
    
    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        """Visit function/method definition."""
        # Add to name context before generating ID
        self.function_name_stack.append(node.name)
        
        function_id = self._generate_id("function", node.name, node.lineno)
        parent_function = self.current_function
        self.current_function = function_id
        
        # Get function metadata
        docstring = self._get_docstring(node)
        signature = self._get_function_signature(node)
        return_type = self._get_return_type(node)
        
        # Determine function characteristics
        is_async = isinstance(node, ast.AsyncFunctionDef)
        is_generator = self._is_generator(node)
        is_property = self._has_decorator(node, "property")
        is_staticmethod = self._has_decorator(node, "staticmethod")
        is_classmethod = self._has_decorator(node, "classmethod")
        complexity = self._calculate_complexity(node)
        
        function_entity = ParsedEntity(
            id=function_id,
            name=node.name,
            type="Function",
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=self._get_end_line(node),
            metadata={
                "docstring": docstring,
                "signature": signature,
                "return_type": return_type,
                "is_async": is_async,
                "is_generator": is_generator,
                "is_property": is_property,
                "is_staticmethod": is_staticmethod,
                "is_classmethod": is_classmethod,
                "complexity": complexity,
                "file_id": self.entity_ids['file'],
                "module_id": self.current_module,
                "class_id": self.current_class,
                "parent_function": parent_function
            }
        )
        
        self.entities.append(function_entity)
        self.entity_ids[f"function:{node.name}"] = function_id
        
        # Create appropriate CONTAINS relationship
        if self.current_class:
            self._create_relationship(self.current_class, function_id, "CLASS_CONTAINS_FUNCTION")
        elif parent_function:
            self._create_relationship(parent_function, function_id, "FUNCTION_CONTAINS_FUNCTION")  # For nested functions
        elif self.current_module:
            self._create_relationship(self.current_module, function_id, "MODULE_CONTAINS_FUNCTION")
            # Also create direct file relationship for better visualization
            self._create_relationship(self.entity_ids['file'], function_id, "FILE_CONTAINS_FUNCTION")
        else:
            self._create_relationship(self.entity_ids['file'], function_id, "FILE_CONTAINS_FUNCTION")
        
        # Handle decorators
        for decorator in node.decorator_list:
            decorator_name = self._get_name_from_node(decorator)
            if decorator_name:
                self._create_relationship(
                    f"unresolved:{decorator_name}",
                    function_id,
                    "DECORATES",
                    {"decorator_name": decorator_name, "line_number": node.lineno}
                )
        
        # Visit function body
        self.generic_visit(node)
        
        # Restore context
        self.current_function = parent_function
        self.function_name_stack.pop()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.visit_FunctionDef(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            import_id = self._generate_id("import", alias.name, node.lineno)
            
            import_entity = ParsedEntity(
                id=import_id,
                name=alias.asname if alias.asname else alias.name,
                type="Import",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                metadata={
                    "module_name": alias.name,
                    "alias": alias.asname,
                    "is_from_import": False,
                    "file_id": self.entity_ids['file']
                }
            )
            
            self.entities.append(import_entity)
            
            # Track import for later resolution
            import_name = alias.asname if alias.asname else alias.name
            self.imports[import_name] = alias.name
            
            # Create FILE_CONTAINS_IMPORT relationship
            self._create_relationship(
                self.entity_ids['file'],
                import_id,
                "FILE_CONTAINS_IMPORT"
            )
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statement."""
        module_name = node.module or ""
        
        for alias in node.names:
            import_id = self._generate_id("import", f"{module_name}.{alias.name}", node.lineno)
            
            import_entity = ParsedEntity(
                id=import_id,
                name=alias.name,
                type="Import",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                metadata={
                    "module_name": module_name,
                    "alias": alias.asname,
                    "is_from_import": True,
                    "file_id": self.entity_ids['file']
                }
            )
            
            self.entities.append(import_entity)
            
            # Track import for later resolution
            import_name = alias.asname if alias.asname else alias.name
            self.imports[import_name] = f"{module_name}.{alias.name}"
            
            # Create FILE_CONTAINS_IMPORT relationship
            self._create_relationship(
                self.entity_ids['file'],
                import_id,
                "FILE_CONTAINS_IMPORT"
            )
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if self.current_function:
            func_name = self._get_name_from_node(node.func)
            if func_name:
                # Create CALLS relationship (will be resolved in second pass)
                self._create_relationship(
                    self.current_function,
                    f"unresolved:{func_name}",
                    "CALLS",
                    {
                        "call_type": "function_call",
                        "line_number": node.lineno
                    }
                )
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit variable assignment."""
        # Extract variable names from targets
        for target in node.targets:
            var_names = self._extract_variable_names(target)
            for var_name in var_names:
                if var_name and not var_name.startswith('_'):  # Skip private variables
                    var_id = self._generate_id("variable", var_name, node.lineno)
                    
                    type_annotation = self._infer_type_from_value(node.value)
                    
                    variable_entity = ParsedEntity(
                        id=var_id,
                        name=var_name,
                        type="Variable",
                        file_path=self.file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        metadata={
                            "type_annotation": type_annotation,
                            "is_global": self.current_function is None and self.current_class is None,
                            "is_constant": var_name.isupper(),
                            "file_id": self.entity_ids['file'],
                            "scope_id": self.current_function or self.current_class or self.current_module
                        }
                    )
                    
                    self.entities.append(variable_entity)
                    
                    # Create appropriate CONTAINS relationship
                    if self.current_function:
                        self._create_relationship(self.current_function, var_id, "FUNCTION_CONTAINS_VARIABLE")
                    elif self.current_class:
                        self._create_relationship(self.current_class, var_id, "CLASS_CONTAINS_VARIABLE")
                        # Also create direct file relationship for better visualization
                        self._create_relationship(self.entity_ids['file'], var_id, "FILE_CONTAINS_VARIABLE")
                    elif self.current_module:
                        self._create_relationship(self.current_module, var_id, "MODULE_CONTAINS_VARIABLE")
                        # Also create direct file relationship for better visualization  
                        self._create_relationship(self.entity_ids['file'], var_id, "FILE_CONTAINS_VARIABLE")
                    else:
                        self._create_relationship(self.entity_ids['file'], var_id, "FILE_CONTAINS_VARIABLE")
        
        self.generic_visit(node)
    
    # Helper methods
    
    def _generate_id(self, entity_type: str, name: str, line: int) -> str:
        """Generate unique entity ID with full context hierarchy."""
        import hashlib
        
        # Build hierarchical context path for uniqueness
        context_parts = [
            self.file_path,
            self.module_name,
            ".".join(self.class_name_stack) if self.class_name_stack else "",
            ".".join(self.function_name_stack) if self.function_name_stack else "",
            entity_type,
            name,
            str(line)
        ]
        
        # Remove empty parts and join with colons
        identifier = ":".join(part for part in context_parts if part)
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def _get_docstring(self, node: ast.AST) -> str:
        """Extract docstring from AST node."""
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and
            node.body and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return ""
    
    def _get_end_line(self, node: ast.AST) -> int:
        """Get end line number for AST node."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        # Fallback: estimate based on content
        return getattr(node, 'lineno', 1)
    
    def _get_function_signature(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Generate function signature string."""
        args = []
        
        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_name_from_node(arg.annotation)}"
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            vararg = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg += f": {self._get_name_from_node(node.args.vararg.annotation)}"
            args.append(vararg)
        
        # **kwargs
        if node.args.kwarg:
            kwarg = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg += f": {self._get_name_from_node(node.args.kwarg.annotation)}"
            args.append(kwarg)
        
        return f"({', '.join(args)})"
    
    def _get_return_type(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Get function return type annotation."""
        if node.returns:
            return self._get_name_from_node(node.returns)
        return ""
    
    def _get_name_from_node(self, node: ast.AST) -> str:
        """Extract name string from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name_from_node(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""
    
    def _is_abstract_class(self, node: ast.ClassDef) -> bool:
        """Check if class is abstract."""
        # Check for ABC inheritance or abstractmethod decorators
        for base in node.bases:
            if self._get_name_from_node(base) in ('ABC', 'abc.ABC'):
                return True
        
        # Check for abstractmethod decorators in methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in item.decorator_list:
                    if self._get_name_from_node(decorator) in ('abstractmethod', 'abc.abstractmethod'):
                        return True
        
        return False
    
    def _is_generator(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> bool:
        """Check if function is a generator."""
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False
    
    def _has_decorator(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], decorator_name: str) -> bool:
        """Check if function has specific decorator."""
        for decorator in node.decorator_list:
            if self._get_name_from_node(decorator) == decorator_name:
                return True
        return False
    
    def _calculate_complexity(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                                ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _get_call_context(self, node: ast.Call) -> str:
        """Get context information for function call."""
        try:
            if hasattr(node, 'lineno') and node.lineno <= len(self.lines):
                return self.lines[node.lineno - 1].strip()
        except:
            pass
        return ""
    
    def _extract_variable_names(self, node: ast.AST) -> List[str]:
        """Extract variable names from assignment target."""
        names = []
        
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Tuple):
            for elt in node.elts:
                names.extend(self._extract_variable_names(elt))
        elif isinstance(node, ast.List):
            for elt in node.elts:
                names.extend(self._extract_variable_names(elt))
        
        return names
    
    def _infer_type_from_value(self, node: ast.AST) -> str:
        """Infer type from assignment value."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        elif isinstance(node, ast.Call):
            func_name = self._get_name_from_node(node.func)
            return func_name if func_name else "unknown"
        
        return "unknown"
    
    def _create_relationship(self, from_id: str, to_id: str, rel_type: str, metadata: Dict[str, Any] = None):
        """Create a relationship between entities."""
        relationship = ParsedRelationship(
            from_id=from_id,
            to_id=to_id,
            relationship_type=rel_type,
            metadata=metadata or {}
        )
        self.relationships.append(relationship)