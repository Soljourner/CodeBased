"""
CSS parser for CodeBased with SCSS/SASS and Angular support.
"""

import time
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Set

from .base import BaseParser, ParsedEntity, ParsedRelationship, ParseResult

logger = logging.getLogger(__name__)


class CSSParser(BaseParser):
    """CSS parser with SCSS/SASS and Angular support."""

    SUPPORTED_FILE_TYPES = {"css", "scss", "sass", "angular_style"}

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a CSS/SCSS/SASS file and extract style features.

        Args:
            file_path: Path to CSS file

        Returns:
            ParseResult with entities and relationships
        """
        start_time = time.time()
        entities = []
        relationships = []
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_hash = self._calculate_file_hash(file_path)
            
            # Create File entity with enhanced metadata
            file_entity = self._create_css_file_entity(file_path, content)
            entities.append(file_entity)

            # Extract CSS features and relationships
            self._extract_css_features(file_entity, content, relationships)

        except Exception as e:
            error_msg = f"Failed to parse {file_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            file_hash = ""

        parse_time = time.time() - start_time
        return ParseResult(entities, relationships, file_hash, file_path, errors, parse_time)

    def _create_css_file_entity(self, file_path: str, content: str) -> ParsedEntity:
        """Create a File entity for a CSS file with enhanced metadata."""
        lines = content.splitlines()
        file_stats = os.stat(file_path)
        path_obj = Path(file_path)
        
        # Determine CSS preprocessor type
        css_type = self._detect_css_type(path_obj.suffix, content)
        
        # Detect if this is an Angular component style
        is_angular_style = self._detect_angular_style(file_path, content)
        
        metadata = {
            'full_path': file_path,
            'extension': path_obj.suffix,
            'size': file_stats.st_size,
            'lines_of_code': len(lines),
            'language': css_type,
            'framework': 'angular' if is_angular_style else None,
            'is_stylesheet': True,
            'style_type': css_type,
            'is_component_style': is_angular_style
        }
        
        # Add CSS-specific metadata
        metadata.update(self._extract_css_metadata(content, css_type))

        return ParsedEntity(
            id=self._generate_entity_id(path_obj.name, file_path, 1, 
                                       entity_type="File", line_end=len(lines)),
            name=path_obj.name,
            type="File",
            file_path=file_path,
            line_start=1,
            line_end=len(lines),
            metadata=metadata
        )

    def _detect_css_type(self, extension: str, content: str) -> str:
        """Detect the type of CSS file (css, scss, sass)."""
        if extension == '.scss':
            return 'scss'
        elif extension == '.sass':
            return 'sass'
        elif extension == '.css':
            # Check if it contains SCSS syntax in a .css file
            if re.search(r'[\$@&]|\{[^}]*\{', content):
                return 'scss'
            return 'css'
        return 'css'

    def _detect_angular_style(self, file_path: str, content: str) -> bool:
        """Detect if this is an Angular component style file."""
        # Check file naming pattern
        if '.component.' in file_path:
            return True
        
        # Check for Angular-specific CSS patterns
        angular_patterns = [
            r':host',               # Host selector
            r'::ng-deep',           # Deep selector
            r'@use [\'"]@angular',  # Angular Material imports
            r'mat-[a-z-]+',         # Material component selectors
        ]
        
        for pattern in angular_patterns:
            if re.search(pattern, content):
                return True
        return False

    def _extract_css_metadata(self, content: str, css_type: str) -> Dict[str, Any]:
        """Extract CSS-specific metadata from stylesheet content."""
        metadata = {}
        
        # Count selectors
        selectors = self._extract_selectors(content)
        metadata['selector_count'] = len(selectors)
        metadata['selectors'] = list(selectors)[:20]  # First 20 selectors
        
        # Count CSS rules/declarations
        rule_count = len(re.findall(r'\{[^}]*\}', content))
        metadata['rule_count'] = rule_count
        
        # Extract imports
        imports = self._extract_imports(content, css_type)
        metadata['import_count'] = len(imports)
        metadata['imports'] = imports
        
        # SCSS/SASS specific features
        if css_type in ['scss', 'sass']:
            metadata.update(self._extract_preprocessor_features(content, css_type))
        
        # Angular specific features
        if self._detect_angular_style('', content):
            metadata.update(self._extract_angular_style_features(content))
        
        return metadata

    def _extract_selectors(self, content: str) -> Set[str]:
        """Extract CSS selectors from content."""
        selectors = set()
        
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Extract selectors (simplified)
        pattern = r'([.#]?[a-zA-Z][a-zA-Z0-9_-]*(?:\s*[>+~]\s*[.#]?[a-zA-Z][a-zA-Z0-9_-]*)*)\s*{'
        for match in re.finditer(pattern, content):
            selector = match.group(1).strip()
            if selector:
                selectors.add(selector)
        
        return selectors

    def _extract_imports(self, content: str, css_type: str) -> List[str]:
        """Extract CSS/SCSS imports from content."""
        imports = []
        
        # CSS @import statements
        css_imports = re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', content)
        imports.extend(css_imports)
        
        # SCSS @use and @forward statements
        if css_type == 'scss':
            scss_uses = re.findall(r'@use\s+[\'"]([^\'"]+)[\'"]', content)
            imports.extend(scss_uses)
            
            scss_forwards = re.findall(r'@forward\s+[\'"]([^\'"]+)[\'"]', content)
            imports.extend(scss_forwards)
        
        return imports

    def _extract_preprocessor_features(self, content: str, css_type: str) -> Dict[str, Any]:
        """Extract SCSS/SASS specific features."""
        features = {}
        
        # Variables
        if css_type == 'scss':
            variables = re.findall(r'\$([a-zA-Z][a-zA-Z0-9_-]*)', content)
            features['scss_variables'] = list(set(variables))
            features['variable_count'] = len(set(variables))
        
        # Mixins
        mixins = re.findall(r'@mixin\s+([a-zA-Z][a-zA-Z0-9_-]*)', content)
        features['mixins'] = list(set(mixins))
        features['mixin_count'] = len(set(mixins))
        
        # Functions
        functions = re.findall(r'@function\s+([a-zA-Z][a-zA-Z0-9_-]*)', content)
        features['functions'] = list(set(functions))
        features['function_count'] = len(set(functions))
        
        # Nesting depth (simplified)
        max_nesting = self._calculate_max_nesting_depth(content)
        features['max_nesting_depth'] = max_nesting
        
        return features

    def _extract_angular_style_features(self, content: str) -> Dict[str, Any]:
        """Extract Angular-specific style features."""
        features = {}
        
        # Host selectors
        host_selectors = len(re.findall(r':host', content))
        features['host_selectors'] = host_selectors
        
        # Deep selectors
        deep_selectors = len(re.findall(r'::ng-deep', content))
        features['deep_selectors'] = deep_selectors
        
        # Material component usage
        material_selectors = set(re.findall(r'(mat-[a-z-]+)', content))
        features['material_components'] = list(material_selectors)
        
        return features

    def _calculate_max_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth in CSS."""
        max_depth = 0
        current_depth = 0
        
        for char in content:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)
        
        return max_depth

    def _extract_css_features(self, file_entity: ParsedEntity, content: str, 
                            relationships: List[ParsedRelationship]) -> None:
        """Extract CSS features and create relationships."""
        
        # Extract import relationships
        imports = self._extract_imports(content, file_entity.metadata.get('style_type', 'css'))
        for import_path in imports:
            relationships.append(ParsedRelationship(
                from_id=file_entity.id,
                to_id=f"unresolved:style_{import_path}",
                relationship_type="IMPORTS_STYLE",
                metadata={
                    'import_path': import_path,
                    'import_type': 'css_import'
                }
            ))
