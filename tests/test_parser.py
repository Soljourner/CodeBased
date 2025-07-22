"""
Unit tests for Python AST parser.
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from codebased.parsers.python import PythonASTParser
from codebased.parsers.base import ParsedEntity, ParsedRelationship


class TestPythonASTParser(unittest.TestCase):
    """Test cases for Python AST parser."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = PythonASTParser({
            'exclude_patterns': [],
            'max_file_size': 1024 * 1024,
            'include_docstrings': True
        })
        
    def tearDown(self):
        """Clean up test environment."""
        pass
        
    def test_can_parse_python_files(self):
        """Test that parser can identify Python files."""
        self.assertTrue(self.parser.can_parse('test.py'))
        self.assertTrue(self.parser.can_parse('/path/to/script.py'))
        self.assertFalse(self.parser.can_parse('test.js'))
        self.assertFalse(self.parser.can_parse('README.md'))
        
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        code = '''
def hello_world():
    """A simple function."""
    print("Hello, World!")
    return "Hello"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check entities
                entity_types = [e.type for e in result.entities]
                self.assertIn('File', entity_types)
                self.assertIn('Module', entity_types)
                self.assertIn('Function', entity_types)
                
                # Check function details
                functions = [e for e in result.entities if e.type == 'Function']
                self.assertEqual(len(functions), 1)
                func = functions[0]
                self.assertEqual(func.name, 'hello_world')
                self.assertEqual(func.metadata.get('docstring'), 'A simple function.')
                
                # Check relationships
                self.assertGreater(len(result.relationships), 0)
                
            finally:
                os.unlink(f.name)
                
    def test_parse_class_with_methods(self):
        """Test parsing a class with methods."""
        code = '''
class Calculator:
    """A simple calculator class."""
    
    def __init__(self, name):
        self.name = name
        
    def add(self, a, b):
        """Add two numbers."""
        return a + b
        
    def multiply(self, a, b):
        """Multiply two numbers."""
        result = self.add(a, 0)  # This creates a call relationship
        for i in range(b - 1):
            result = self.add(result, a)
        return result
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check class
                classes = [e for e in result.entities if e.type == 'Class']
                self.assertEqual(len(classes), 1)
                calc_class = classes[0]
                self.assertEqual(calc_class.name, 'Calculator')
                self.assertEqual(calc_class.metadata.get('docstring'), 'A simple calculator class.')
                
                # Check methods
                functions = [e for e in result.entities if e.type == 'Function']
                func_names = {f.name for f in functions}
                expected_methods = {'__init__', 'add', 'multiply'}
                self.assertTrue(expected_methods.issubset(func_names))
                
                # Check function calls (multiply calls add)
                call_relationships = [r for r in result.relationships if r.relationship_type == 'CALLS']
                self.assertGreater(len(call_relationships), 0)
                
            finally:
                os.unlink(f.name)
                
    def test_parse_imports(self):
        """Test parsing import statements."""
        code = '''
import os
import sys
from pathlib import Path
from collections import defaultdict, deque
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check imports
                imports = [e for e in result.entities if e.type == 'Import']
                self.assertGreaterEqual(len(imports), 4)  # os, sys, Path, defaultdict, deque
                
                import_names = {i.name for i in imports}
                expected_imports = {'os', 'sys', 'Path', 'defaultdict', 'deque'}
                self.assertTrue(expected_imports.issubset(import_names))
                
            finally:
                os.unlink(f.name)
                
    def test_parse_inheritance(self):
        """Test parsing class inheritance."""
        code = '''
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check inheritance relationships
                inherits_relationships = [r for r in result.relationships if r.relationship_type == 'INHERITS']
                self.assertEqual(len(inherits_relationships), 2)  # Dog and Cat inherit from Animal
                
            finally:
                os.unlink(f.name)
                
    def test_parse_variables(self):
        """Test parsing variable assignments."""
        code = '''
# Global constants
MAX_SIZE = 100
DEFAULT_NAME = "test"

def process_data():
    # Local variables
    items = []
    count = 0
    result = {"status": "ok"}
    
    return result
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check variables
                variables = [e for e in result.entities if e.type == 'Variable']
                self.assertGreater(len(variables), 0)
                
                var_names = {v.name for v in variables}
                expected_vars = {'MAX_SIZE', 'DEFAULT_NAME', 'items', 'count', 'result'}
                # At least some of these should be found
                self.assertTrue(len(expected_vars.intersection(var_names)) > 0)
                
            finally:
                os.unlink(f.name)
                
    def test_parse_syntax_error(self):
        """Test handling of syntax errors."""
        code = '''
def broken_function(
    # Missing closing parenthesis
    print("This will fail")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Should have errors
                self.assertGreater(len(result.errors), 0)
                
                # Should still return a result object
                self.assertIsNotNone(result)
                
            finally:
                os.unlink(f.name)
                
    def test_complex_code_structure(self):
        """Test parsing a more complex code structure."""
        code = '''
"""Module docstring."""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes data with various methods."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.cache = {}
        
    def process(self, data: List[str]) -> Optional[Dict]:
        """Main processing method."""
        if not data:
            logger.warning("No data provided")
            return None
            
        result = {}
        for item in data:
            processed = self._process_item(item)
            if processed:
                result[item] = processed
                
        return result
        
    def _process_item(self, item: str) -> Optional[str]:
        """Process a single item."""
        if item in self.cache:
            return self.cache[item]
            
        # Simulate processing
        processed = item.upper()
        self.cache[item] = processed
        return processed

def main():
    """Main function."""
    processor = DataProcessor({"mode": "test"})
    result = processor.process(["hello", "world"])
    print(result)

if __name__ == "__main__":
    main()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            try:
                result = self.parser.parse_file(f.name)
                
                # Check no errors
                self.assertEqual(len(result.errors), 0)
                
                # Check we found all major components
                entity_types = [e.type for e in result.entities]
                self.assertIn('File', entity_types)
                self.assertIn('Module', entity_types)
                self.assertIn('Class', entity_types)
                self.assertIn('Function', entity_types)
                self.assertIn('Import', entity_types)
                self.assertIn('Variable', entity_types)
                
                # Check specific entities
                classes = [e for e in result.entities if e.type == 'Class']
                self.assertEqual(len(classes), 1)
                self.assertEqual(classes[0].name, 'DataProcessor')
                
                functions = [e for e in result.entities if e.type == 'Function']
                func_names = {f.name for f in functions}
                expected_funcs = {'__init__', 'process', '_process_item', 'main'}
                self.assertTrue(expected_funcs.issubset(func_names))
                
                # Check relationships
                relationships = result.relationships
                self.assertGreater(len(relationships), 0)
                
                # Should have various relationship types
                rel_types = {r.relationship_type for r in relationships}
                expected_rel_types = {'CONTAINS', 'CALLS'}
                self.assertTrue(len(expected_rel_types.intersection(rel_types)) > 0)
                
            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()