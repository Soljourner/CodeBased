"""
JavaScript parser for CodeBased using tree-sitter.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import TreeSitterParser, ParsedEntity, ParsedRelationship, ParseResult
try:
    from tree_sitter import Node
except ImportError:
    Node = None

logger = logging.getLogger(__name__)


class JavaScriptParser(TreeSitterParser):
    """JavaScript parser using tree-sitter."""

    SUPPORTED_FILE_TYPES = {"javascript"}
    TREE_SITTER_LANGUAGE = "javascript"

    # JavaScript node types we want to extract as entities
    ENTITY_NODE_TYPES = {
        'class_declaration': 'Class',
        'function_declaration': 'Function',
        'function': 'Function',
        'arrow_function': 'Function',
        'method_definition': 'Method',
        'variable_declaration': 'Variable',
        'lexical_declaration': 'Variable',  # let/const declarations
        'import_statement': 'Import',
        'export_statement': 'Export',
        'generator_function_declaration': 'Function',
        'async_function_declaration': 'Function',
        'object_pattern': 'ObjectPattern',
        'array_pattern': 'ArrayPattern',
        'decorator': 'Decorator',
        'arrow_function': 'ArrowFunction',
        'async_function_declaration': 'AsyncFunction',
        'async_function': 'AsyncFunction',
        'generator_function': 'GeneratorFunction',
        'property_definition': 'Property',
        'field_definition': 'Field'
    }

    # Angular-specific decorator mappings
    ANGULAR_DECORATORS = {
        'Component': 'AngularComponent',
        'Injectable': 'AngularService', 
        'Directive': 'AngularDirective',
        'Pipe': 'AngularPipe',
        'NgModule': 'AngularModule',
        'Input': 'AngularInput',
        'Output': 'AngularOutput'
    }

    def _extract_entities_from_node(self, node: Node, source_code: str, file_path: str) -> List[ParsedEntity]:
        """Extract JavaScript entities from tree-sitter AST."""
        entities = []
        
        # Add file entity
        entities.append(self._create_file_entity(file_path, source_code))
        
        # Traverse tree and extract entities
        self._traverse_for_entities(node, source_code, file_path, entities)
        
        return entities

    def _extract_relationships_from_node(self, node: Node, source_code: str, 
                                       entities: List[ParsedEntity], file_path: str) -> List[ParsedRelationship]:
        """Extract JavaScript relationships from tree-sitter AST."""
        relationships = []
        
        # Create entity lookup for relationships
        entity_lookup = {entity.name: entity for entity in entities}
        
        # Traverse tree and extract relationships
        self._traverse_for_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        
        return relationships
    
    def _normalize_relationship_metadata(self, relationship: ParsedRelationship) -> Dict[str, Any]:
        """
        Normalize JavaScript relationship metadata to match database schema.
        
        Args:
            relationship: Relationship with metadata to normalize
            
        Returns:
            Dictionary with properties that match the schema
        """
        rel_type = relationship.relationship_type
        metadata = relationship.metadata or {}
        
        # Mapping for each relationship type based on schema definitions
        if rel_type == "CALLS":
            # Schema: call_type STRING, line_number INT64
            return {
                'call_type': metadata.get('type', 'function_call'),
                'line_number': metadata.get('call_location', metadata.get('line_number', 0))
            }
        
        elif rel_type == "USES":
            # Schema: usage_type STRING, line_number INT64
            return {
                'usage_type': metadata.get('type', 'variable_access'),
                'line_number': metadata.get('access_location', metadata.get('line_number', 0))
            }
        
        elif rel_type == "ACCESSES":
            # Schema: property_path STRING, access_location INT64
            return {
                'property_path': metadata.get('property_path', ''),
                'access_location': metadata.get('access_location', metadata.get('line_number', 0))
            }
        
        elif rel_type == "EXPORTS":
            # Schema: export_type STRING, symbol STRING
            return {
                'export_type': metadata.get('export_type', 'named'),
                'symbol': metadata.get('symbol', metadata.get('function_name', ''))
            }
        
        elif rel_type == "IMPORTS":
            # Schema: import_type STRING
            return {
                'import_type': metadata.get('import_type', 'named')
            }
        
        elif rel_type == "DECORATES":
            # Schema: decorator_name STRING
            return {
                'decorator_name': metadata.get('decorator_name', '')
            }
        
        elif rel_type == "USES_TEMPLATE":
            # Schema: template_path STRING, resolved_path STRING, component_selector STRING
            return {
                'template_path': metadata.get('template_path', ''),
                'resolved_path': metadata.get('resolved_path', ''),
                'component_selector': metadata.get('component_selector', '')
            }
        
        elif rel_type == "USES_STYLES":
            # Schema: style_path STRING, resolved_path STRING, component_selector STRING
            return {
                'style_path': metadata.get('style_path', ''),
                'resolved_path': metadata.get('resolved_path', ''),
                'component_selector': metadata.get('component_selector', '')
            }
        
        # For containment relationships (FILE_CONTAINS_*, CLASS_CONTAINS_*, etc.)
        # these don't have additional properties in the schema, so return empty dict
        elif rel_type.startswith("FILE_CONTAINS_") or rel_type.startswith("CLASS_CONTAINS_") or \
             rel_type.startswith("MODULE_CONTAINS_") or rel_type.startswith("FUNCTION_CONTAINS_"):
            return {}
        
        # For relationship types without extra properties (IMPLEMENTS, EXTENDS, INHERITS)
        elif rel_type in ["IMPLEMENTS", "EXTENDS", "INHERITS"]:
            return {}
        
        # For unknown relationship types, log warning and return empty dict
        else:
            logger.warning(f"Unknown relationship type: {rel_type}")
            return {}

    def _create_file_entity(self, file_path: str, source_code: str) -> ParsedEntity:
        """Create entity for the file itself."""
        lines = source_code.splitlines()
        filename = str(Path(file_path).name)
        file_path_obj = Path(file_path)
        
        # Get file metadata
        import os
        import time
        import hashlib
        
        file_stats = os.stat(file_path) if os.path.exists(file_path) else None
        file_size = file_stats.st_size if file_stats else 0
        modified_time = int(file_stats.st_mtime) if file_stats else int(time.time())
        
        # Generate file hash
        file_hash = hashlib.md5(source_code.encode()).hexdigest()
        
        return ParsedEntity(
            id=self._generate_entity_id(filename, file_path, 1, entity_type="File"),
            name=filename,
            type="File",
            file_path=file_path,
            line_start=1,
            line_end=len(lines),
            metadata={
                'extension': file_path_obj.suffix,
                'size': file_size,
                'modified_time': modified_time,
                'hash': file_hash,
                'lines_of_code': len(lines),
                'full_path': file_path,
                'language': 'javascript'
            }
        )

    def _traverse_for_entities(self, node: Node, source_code: str, file_path: str, entities: List[ParsedEntity]) -> None:
        """Traverse AST and extract entities."""
        if node.type in self.ENTITY_NODE_TYPES:
            entity = self._create_entity_from_node(node, source_code, file_path)
            if entity:
                entities.append(entity)
        
        # Recursively process children
        for child in node.children:
            self._traverse_for_entities(child, source_code, file_path, entities)

    def _create_entity_from_node(self, node: Node, source_code: str, file_path: str) -> Optional[ParsedEntity]:
        """Create entity from a tree-sitter node."""
        try:
            # Handle decorators specially
            if node.type == 'decorator':
                return self._create_angular_decorator_entity(node, source_code, file_path)
            
            entity_type = self.ENTITY_NODE_TYPES.get(node.type, node.type)
            name = self._extract_name_from_node(node, source_code)
            
            if not name:
                return None
            
            start_line, end_line = self._get_node_line_info(node)
            node_text = self._get_node_text(node, source_code)
            
            # Extract additional metadata based on node type
            metadata = self._extract_node_metadata(node, source_code, entity_type)
            metadata.update({
                'node_type': node.type,
                'code_snippet': node_text[:500],  # Limit snippet size
                'language': 'javascript'
            })
            
            return ParsedEntity(
                id=self._generate_entity_id(name, file_path, start_line),
                name=name,
                type=entity_type,
                file_path=file_path,
                line_start=start_line,
                line_end=end_line,
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Failed to create entity from node {node.type}: {e}")
            return None

    def _create_angular_decorator_entity(self, node: Node, source_code: str, file_path: str) -> Optional[ParsedEntity]:
        """Create Angular decorator entity from decorator node."""
        try:
            node_text = self._get_node_text(node, source_code)
            start_line, end_line = self._get_node_line_info(node)
            
            # Extract decorator name (e.g., @Component -> Component)
            decorator_name = None
            if node_text.startswith('@'):
                # Simple case: @Component
                decorator_name = node_text[1:].split('(')[0].strip()
            
            if not decorator_name:
                return None
            
            # Check if this is an Angular decorator
            angular_type = self.ANGULAR_DECORATORS.get(decorator_name)
            if not angular_type:
                # Not an Angular decorator, create generic Decorator entity
                return ParsedEntity(
                    id=self._generate_entity_id(f"decorator_{decorator_name}", file_path, start_line),
                    name=f"@{decorator_name}",
                    type="Decorator",
                    file_path=file_path,
                    line_start=start_line,
                    line_end=end_line,
                    metadata={
                        'decorator_name': decorator_name,
                        'node_type': node.type,
                        'language': 'javascript'
                    }
                )
            
            # Extract Angular decorator configuration
            metadata = self._extract_angular_decorator_metadata(node, source_code, decorator_name)
            metadata.update({
                'decorator_name': decorator_name,
                'node_type': node.type,
                'language': 'javascript',
                'framework': 'angular'
            })
            
            return ParsedEntity(
                id=self._generate_entity_id(f"angular_{decorator_name}", file_path, start_line),
                name=f"@{decorator_name}",
                type=angular_type,
                file_path=file_path,
                line_start=start_line,
                line_end=end_line,
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Failed to create Angular decorator entity: {e}")
            return None

    def _extract_angular_decorator_metadata(self, node: Node, source_code: str, decorator_name: str) -> Dict[str, Any]:
        """Extract Angular-specific metadata from decorator configuration."""
        metadata = {}
        node_text = self._get_node_text(node, source_code)
        
        try:
            if decorator_name == 'Component':
                # Extract @Component configuration
                metadata.update(self._extract_component_config(node_text))
            elif decorator_name == 'Injectable':
                # Extract @Injectable configuration
                metadata.update(self._extract_injectable_config(node_text))
            elif decorator_name == 'Directive':
                # Extract @Directive configuration
                metadata.update(self._extract_directive_config(node_text))
            elif decorator_name == 'NgModule':
                # Extract @NgModule configuration
                metadata.update(self._extract_module_config(node_text))
                
        except Exception as e:
            logger.debug(f"Failed to extract Angular metadata for {decorator_name}: {e}")
        
        return metadata
    
    def _extract_component_config(self, decorator_text: str) -> Dict[str, Any]:
        """Extract @Component decorator configuration."""
        config = {}
        
        # Extract selector
        import re
        selector_match = re.search(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]', decorator_text)
        if selector_match:
            config['selector'] = selector_match.group(1)
        
        # Extract templateUrl
        template_url_match = re.search(r'templateUrl\s*:\s*[\'"]([^\'"]+)[\'"]', decorator_text)
        if template_url_match:
            config['templateUrl'] = template_url_match.group(1)
        
        # Extract template (inline)
        template_match = re.search(r'template\s*:\s*[\'"`]([^\'"`]*)[\'"`]', decorator_text, re.DOTALL)
        if template_match:
            config['template'] = template_match.group(1)[:200]  # Limit length
        
        # Extract styleUrls
        style_urls_match = re.search(r'styleUrls\s*:\s*\[(.*?)\]', decorator_text, re.DOTALL)
        if style_urls_match:
            style_urls_text = style_urls_match.group(1)
            # Extract individual URLs
            url_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', style_urls_text)
            config['styleUrls'] = url_matches
        
        # Extract styles (inline)
        styles_match = re.search(r'styles\s*:\s*\[(.*?)\]', decorator_text, re.DOTALL)
        if styles_match:
            config['hasInlineStyles'] = True
        
        return config
    
    def _extract_injectable_config(self, decorator_text: str) -> Dict[str, Any]:
        """Extract @Injectable decorator configuration."""
        config = {}
        
        # Extract providedIn
        import re
        provided_in_match = re.search(r'providedIn\s*:\s*[\'"]([^\'"]+)[\'"]', decorator_text)
        if provided_in_match:
            config['providedIn'] = provided_in_match.group(1)
        
        return config
    
    def _extract_directive_config(self, decorator_text: str) -> Dict[str, Any]:
        """Extract @Directive decorator configuration."""
        config = {}
        
        # Extract selector
        import re
        selector_match = re.search(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]', decorator_text)
        if selector_match:
            config['selector'] = selector_match.group(1)
        
        return config
    
    def _extract_module_config(self, decorator_text: str) -> Dict[str, Any]:
        """Extract @NgModule decorator configuration."""
        config = {}
        
        # Extract basic module properties
        import re
        
        # Check for declarations
        if 'declarations' in decorator_text:
            config['hasDeclarations'] = True
        
        # Check for imports
        if 'imports' in decorator_text:
            config['hasImports'] = True
        
        # Check for providers
        if 'providers' in decorator_text:
            config['hasProviders'] = True
        
        # Check for exports
        if 'exports' in decorator_text:
            config['hasExports'] = True
        
        return config

    def _extract_name_from_node(self, node: Node, source_code: str) -> str:
        """Extract the name/identifier from a node."""
        # Look for identifier child nodes
        for child in node.children:
            if child.type == 'identifier':
                return self._get_node_text(child, source_code)
            elif child.type == 'property_identifier':
                return self._get_node_text(child, source_code)
        
        # Handle variable declarations
        if node.type in ['variable_declaration', 'lexical_declaration']:
            for child in node.children:
                if child.type == 'variable_declarator':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            return self._get_node_text(grandchild, source_code)
        
        # Handle arrow functions assigned to variables
        if node.type == 'arrow_function':
            # Look for parent assignment
            node_text = self._get_node_text(node, source_code)
            # Use line number for deterministic naming
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            return f"arrow_function_L{start_line}_{end_line}"
        
        # Fallback: extract from node text
        node_text = self._get_node_text(node, source_code)
        
        # Simple extraction for common patterns
        if node.type in ['class_declaration', 'function_declaration']:
            parts = node_text.split()
            if len(parts) >= 2:
                return parts[1].split('(')[0].split('{')[0].strip()
        
        return node_text.split('(')[0].split('{')[0].strip()[:50]  # Limit name length

    def _extract_node_metadata(self, node: Node, source_code: str, entity_type: str) -> Dict[str, Any]:
        """Extract additional metadata from node based on type."""
        metadata = {}
        
        try:
            if entity_type == 'Class':
                metadata.update(self._extract_class_metadata(node, source_code))
            elif entity_type == 'Function':
                metadata.update(self._extract_function_metadata(node, source_code))
            elif entity_type == 'Method':
                metadata.update(self._extract_method_metadata(node, source_code))
            elif entity_type in ['Import', 'Export']:
                metadata.update(self._extract_import_export_metadata(node, source_code))
            elif entity_type == 'Variable':
                metadata.update(self._extract_variable_metadata(node, source_code))
                
        except Exception as e:
            logger.debug(f"Failed to extract metadata for {entity_type}: {e}")
        
        return metadata

    def _extract_class_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to class declarations."""
        metadata = {}
        
        # Look for extends clause
        for child in node.children:
            if child.type == 'class_heritage':
                extends_clause = self._get_node_text(child, source_code)
                metadata['extends'] = extends_clause.replace('extends', '').strip()
        
        # Count methods and properties
        method_count = 0
        property_count = 0
        
        for child in node.children:
            if child.type == 'class_body':
                for member in child.children:
                    if member.type in ['method_definition', 'function_declaration']:
                        method_count += 1
                    elif member.type in ['field_definition', 'property_definition']:
                        property_count += 1
        
        metadata.update({
            'method_count': method_count,
            'property_count': property_count
        })
        
        return metadata

    def _extract_function_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to function declarations."""
        metadata = {}
        
        # Extract parameters with enhanced modern JS support
        for child in node.children:
            if child.type == 'formal_parameters':
                param_text = self._get_node_text(child, source_code)
                metadata['parameters'] = param_text
                
                # Enhanced parameter analysis
                param_features = self._analyze_parameters(param_text)
                metadata.update(param_features)
        
        # Check function type with enhanced detection
        node_text = self._get_node_text(node, source_code)
        metadata['is_async'] = 'async' in node_text or node.type in ['async_function_declaration', 'async_function']
        metadata['is_generator'] = node.type in ['generator_function_declaration', 'generator_function']
        metadata['is_arrow'] = node.type == 'arrow_function'
        
        # Detect modern JavaScript patterns
        if '=>' in node_text:
            metadata['function_style'] = 'arrow'
        elif node.type in ['async_function_declaration', 'async_function']:
            metadata['function_style'] = 'async'
        elif node.type in ['generator_function_declaration', 'generator_function']:
            metadata['function_style'] = 'generator'
        else:
            metadata['function_style'] = 'traditional'
        
        return metadata
    
    def _analyze_parameters(self, param_text: str) -> Dict[str, Any]:
        """Analyze function parameters for modern JavaScript features."""
        features = {}
        
        # Count parameters
        if param_text.strip() == '()':
            features['parameter_count'] = 0
        else:
            # More accurate parameter counting considering destructuring
            param_count = param_text.count(',') + 1
            features['parameter_count'] = param_count
        
        # Check for destructuring parameters
        features['has_destructuring'] = '{' in param_text or '[' in param_text
        
        # Check for default parameters
        features['has_defaults'] = '=' in param_text
        
        # Check for rest parameters
        features['has_rest_params'] = '...' in param_text
        
        # Check for type annotations (TypeScript-style in JS)
        features['has_type_annotations'] = ':' in param_text
        
        return features

    def _extract_method_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to method definitions."""
        metadata = {}
        
        node_text = self._get_node_text(node, source_code)
        
        # Check if static
        metadata['is_static'] = 'static' in node_text
        metadata['is_async'] = 'async' in node_text
        
        # Check method kind
        if 'get ' in node_text:
            metadata['method_kind'] = 'getter'
        elif 'set ' in node_text:
            metadata['method_kind'] = 'setter'
        else:
            metadata['method_kind'] = 'method'
        
        return metadata

    def _extract_variable_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata for variable declarations with modern JS support."""
        metadata = {}
        
        node_text = self._get_node_text(node, source_code)
        
        # Determine declaration type
        if node_text.startswith('const'):
            metadata['declaration_type'] = 'const'
        elif node_text.startswith('let'):
            metadata['declaration_type'] = 'let'
        elif node_text.startswith('var'):
            metadata['declaration_type'] = 'var'
        
        # Enhanced assignment analysis
        if '=>' in node_text:
            metadata['is_arrow_function_assignment'] = True
        elif 'function' in node_text:
            metadata['is_function_assignment'] = True
        elif 'async' in node_text:
            metadata['is_async_assignment'] = True
        
        # Check for destructuring
        metadata['has_destructuring'] = '{' in node_text or '[' in node_text
        
        # Check for object/array literals
        if node_text.count('{') > node_text.count('=>'):  # Avoid counting arrow functions
            metadata['is_object_literal'] = True
        if node_text.count('[') > 0:
            metadata['has_array_syntax'] = True
        
        # Check for template literals
        metadata['has_template_literal'] = '`' in node_text
        
        # Check for spread operator
        metadata['has_spread_operator'] = '...' in node_text
        
        # Estimate complexity based on modern JS features
        complexity = 0
        if metadata.get('has_destructuring'): complexity += 1
        if metadata.get('is_arrow_function_assignment'): complexity += 1
        if metadata.get('has_template_literal'): complexity += 1
        if metadata.get('has_spread_operator'): complexity += 1
        metadata['modern_js_complexity'] = complexity
        
        return metadata

    def _extract_import_export_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata for import/export statements."""
        metadata = {}
        
        node_text = self._get_node_text(node, source_code)
        
        # Extract module path
        if 'from' in node_text:
            parts = node_text.split('from')
            if len(parts) > 1:
                module_path = parts[1].strip().strip('\'"')
                metadata['module_path'] = module_path
                metadata['is_relative'] = module_path.startswith('.')
        
        # Check if default import/export
        metadata['is_default'] = 'default' in node_text
        
        # Check if namespace import
        metadata['is_namespace'] = '*' in node_text
        
        return metadata

    def _traverse_for_relationships(self, node: Node, source_code: str, file_path: str,
                                  entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                  entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Traverse AST and extract relationships."""
        
        # Look for specific relationship patterns
        if node.type == 'class_declaration':
            self._extract_class_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'decorator':
            self._extract_angular_decorator_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type in ['import_statement', 'export_statement']:
            self._extract_import_export_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'call_expression':
            self._extract_function_call_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'member_expression':
            self._extract_property_access_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        
        # Recursively process children
        for child in node.children:
            self._traverse_for_relationships(child, source_code, file_path, entities, relationships, entity_lookup)

    def _extract_angular_decorator_relationships(self, node: Node, source_code: str, file_path: str,
                                              entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                              entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract Angular decorator relationships for templates and styles."""
        try:
            node_text = self._get_node_text(node, source_code)
            
            # Check if this is a @Component decorator
            if not node_text.startswith('@Component'):
                return
            
            # Find the component entity (usually the class that follows the decorator)
            component_entity = self._find_component_entity_for_decorator(node, entities)
            if not component_entity:
                return
            
            # Extract templateUrl relationships
            import re
            template_url_match = re.search(r'templateUrl\s*:\s*[\'"]([^\'"]+)[\'"]', node_text)
            if template_url_match:
                template_path = template_url_match.group(1)
                relationships.append(ParsedRelationship(
                    from_id=component_entity.id,
                    to_id=f"unresolved:template_{template_path}",
                    relationship_type="USES_TEMPLATE",
                    metadata={
                        'template_path': template_path,
                        'resolved_path': template_path,  # Will be resolved later
                        'component_selector': '',  # Extract if available
                        'component_file_path': file_path
                    }
                ))
            
            # Extract styleUrls relationships
            style_urls_match = re.search(r'styleUrls\s*:\s*\[(.*?)\]', node_text, re.DOTALL)
            if style_urls_match:
                style_urls_text = style_urls_match.group(1)
                url_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', style_urls_text)
                
                for style_url in url_matches:
                    relationships.append(ParsedRelationship(
                        from_id=component_entity.id,
                        to_id=f"unresolved:style_{style_url}",
                        relationship_type="USES_STYLES",
                        metadata={
                            'style_path': style_url,
                            'resolved_path': style_url,  # Will be resolved later
                            'component_selector': '',  # Extract if available
                            'component_file_path': file_path
                        }
                    ))
            
        except Exception as e:
            logger.debug(f"Failed to extract Angular decorator relationships: {e}")
    
    def _find_component_entity_for_decorator(self, decorator_node: Node, entities: List[ParsedEntity]) -> Optional[ParsedEntity]:
        """Find the component class entity that this decorator applies to."""
        try:
            decorator_line = self._get_node_line_info(decorator_node)[0]
            
            # Look for a class entity that starts shortly after the decorator
            for entity in entities:
                if (entity.type == "Class" and 
                    entity.line_start > decorator_line and 
                    entity.line_start <= decorator_line + 5):  # Within 5 lines
                    return entity
                    
        except Exception as e:
            logger.debug(f"Failed to find component entity for decorator: {e}")
        
        return None

    def _extract_class_relationships(self, node: Node, source_code: str, file_path: str,
                                   entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                   entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract relationships for class declarations."""
        class_name = self._extract_name_from_node(node, source_code)
        
        # Find extends relationships
        for child in node.children:
            if child.type == 'class_heritage':
                heritage_text = self._get_node_text(child, source_code)
                if 'extends' in heritage_text:
                    parent_class = heritage_text.replace('extends', '').strip()
                    if parent_class in entity_lookup:
                        relationships.append(ParsedRelationship(
                            from_id=entity_lookup[class_name].id,
                            to_id=entity_lookup[parent_class].id,
                            relationship_type="EXTENDS",
                            metadata={'type': 'inheritance'}
                        ))

    def _extract_function_call_relationships(self, node: Node, source_code: str, file_path: str,
                                           entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                           entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract function call relationships."""
        if node.type == 'call_expression':
            try:
                # Find the function being called
                function_node = node.children[0] if node.children else None
                if function_node:
                    function_name = self._get_node_text(function_node, source_code)
                    
                    # Find the containing function/method that makes this call
                    caller_entity = self._find_containing_function(node, entities)
                    
                    if caller_entity and function_name:
                        # Mark external function calls as unresolved
                        to_id = f"unresolved:function_{function_name}"
                        
                        # Create function call relationship
                        relationships.append(ParsedRelationship(
                            from_id=caller_entity.id,
                            to_id=to_id,
                            relationship_type="CALLS",
                            metadata={
                                'call_type': 'function_call',
                                'line_number': self._get_node_line_info(node)[0]
                            }
                        ))
                        
            except Exception as e:
                logger.debug(f"Failed to extract function call relationship: {e}")
    
    def _extract_property_access_relationships(self, node: Node, source_code: str, file_path: str,
                                             entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                             entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract property access relationships."""
        if node.type == 'member_expression':
            try:
                access_text = self._get_node_text(node, source_code)
                
                # Find the containing function/method that accesses this property
                accessor_entity = self._find_containing_function(node, entities)
                
                if accessor_entity and access_text:
                    # Mark property accesses as unresolved for cross-file resolution
                    to_id = f"unresolved:property_{access_text}"
                    
                    relationships.append(ParsedRelationship(
                        from_id=accessor_entity.id,
                        to_id=to_id,
                        relationship_type="ACCESSES",
                        metadata={
                            'property_path': access_text,
                            'access_location': self._get_node_line_info(node)[0]
                        }
                    ))
                    
            except Exception as e:
                logger.debug(f"Failed to extract property access relationship: {e}")
    
    def _find_containing_function(self, node: Node, entities: List[ParsedEntity]) -> Optional[ParsedEntity]:
        """Find the function or method that contains the given node."""
        try:
            node_line = self._get_node_line_info(node)[0]
            
            # Find entities that contain this line
            containing_entities = []
            for entity in entities:
                if (entity.type in ['Function', 'Method', 'Constructor'] and 
                    entity.line_start <= node_line <= entity.line_end):
                    containing_entities.append(entity)
            
            # Return the most specific (smallest) containing entity
            if containing_entities:
                return min(containing_entities, key=lambda e: e.line_end - e.line_start)
                
        except Exception as e:
            logger.debug(f"Failed to find containing function: {e}")
        
        return None

    def _extract_import_export_relationships(self, node: Node, source_code: str, file_path: str,
                                           entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                           entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract relationships for import/export statements."""
        try:
            node_text = self._get_node_text(node, source_code)
            
            # Find the file entity as the source
            file_entity = None
            for entity in entities:
                if entity.type == "File":
                    file_entity = entity
                    break
            
            if not file_entity:
                return
            
            if node.type == 'import_statement':
                # Extract imported module path
                if 'from' in node_text:
                    parts = node_text.split('from')
                    if len(parts) > 1:
                        module_path = parts[1].strip().strip('\'"')
                        
                        # Mark external modules as unresolved to prevent storage failures
                        is_external = (module_path.startswith('@') or 
                                     module_path in ['react', 'lodash', 'moment', 'axios', 'rxjs'] or
                                     module_path.startswith('node_modules') or
                                     not module_path.startswith('.'))
                        
                        to_id = f"unresolved:module_{module_path}" if is_external else f"module_{module_path}"
                        
                        # Create import relationship
                        relationships.append(ParsedRelationship(
                            from_id=file_entity.id,
                            to_id=to_id,
                            relationship_type="IMPORTS",
                            metadata={
                                'module_path': module_path,
                                'is_relative': module_path.startswith('.'),
                                'import_text': parts[0].strip(),
                                'import_type': 'external' if is_external else 'internal'
                            }
                        ))
                        
                        # Extract specific imports
                        import_spec = parts[0].replace('import', '').strip()
                        if '{' in import_spec and '}' in import_spec:
                            # Named imports
                            named_imports = import_spec.split('{')[1].split('}')[0]
                            for named_import in named_imports.split(','):
                                clean_import = named_import.strip()
                                if clean_import:
                                    # Mark external symbols as unresolved
                                    symbol_id = f"unresolved:external_{clean_import}" if is_external else f"external_{clean_import}"
                                    
                                    relationships.append(ParsedRelationship(
                                        from_id=file_entity.id,
                                        to_id=symbol_id,
                                        relationship_type="USES",
                                        metadata={
                                            'type': 'named_import',
                                            'symbol': clean_import,
                                            'source_module': module_path,
                                            'usage_type': 'import'
                                        }
                                    ))
            
            elif node.type == 'export_statement':
                # Track what this file exports
                export_spec = node_text.replace('export', '').strip()
                
                if export_spec.startswith('default'):
                    # Default export
                    relationships.append(ParsedRelationship(
                        from_id=file_entity.id,
                        to_id=f"unresolved:export_default_{file_entity.name}",
                        relationship_type="EXPORTS",
                        metadata={
                            'export_type': 'default',
                            'symbol': 'default'
                        }
                    ))
                elif '{' in export_spec and '}' in export_spec:
                    # Named exports
                    named_exports = export_spec.split('{')[1].split('}')[0]
                    for named_export in named_exports.split(','):
                        clean_export = named_export.strip()
                        if clean_export:
                            relationships.append(ParsedRelationship(
                                from_id=file_entity.id,
                                to_id=f"unresolved:export_{clean_export}",
                                relationship_type="EXPORTS",
                                metadata={
                                    'export_type': 'named',
                                    'symbol': clean_export
                                }
                            ))
                            
        except Exception as e:
            logger.debug(f"Failed to extract import/export relationships: {e}")

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a JavaScript file with enhanced external entity creation.
        
        Overrides base parse_file to create stub entities for external function references
        that don't have corresponding entities, preventing relationship storage failures.
        """
        # Call parent method to do normal parsing
        result = super().parse_file(file_path)
        
        # Create external entities for unresolved function references
        external_entities = self._create_external_entities_for_relationships(result.relationships, result.entities)
        
        # Combine entities
        all_entities = result.entities + external_entities
        
        # Return enhanced result
        return ParseResult(
            entities=all_entities,
            relationships=result.relationships,
            file_hash=result.file_hash,
            file_path=result.file_path,
            errors=result.errors,
            parse_time=result.parse_time
        )
    
    def _sanitize_external_name(self, name: str) -> str:
        """
        Sanitize external entity names to prevent ID collisions.
        
        Args:
            name: The entity name to sanitize
            
        Returns:
            Sanitized name that won't cause ID collisions
        """
        if not name:
            return "unknown"
        
        # Handle very long names (like chained D3.js calls)
        if len(name) > 100:
            # Create hash suffix to maintain uniqueness
            import hashlib
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            # Keep meaningful prefix and add hash
            truncated = name[:90]
            # Clean up truncation point
            if '.' in truncated[-10:]:
                truncated = truncated[:truncated.rfind('.')]
            return f"{truncated}...{hash_suffix}"
        
        return name
    
    def _create_external_entities_for_relationships(self, relationships: List[ParsedRelationship], 
                                                   existing_entities: List[ParsedEntity]) -> List[ParsedEntity]:
        """
        Create stub entities for external function references in relationships.
        
        This prevents relationship storage failures when target entities don't exist.
        """
        external_entities = []
        existing_entity_ids = {entity.id for entity in existing_entities}
        
        for rel in relationships:
            # Check if this is an unresolved function call
            if rel.relationship_type == 'CALLS' and rel.to_id.startswith('unresolved:function_'):
                if rel.to_id not in existing_entity_ids:
                    # Extract function name from unresolved ID
                    function_name = rel.to_id.replace('unresolved:function_', '')
                    
                    # Sanitize long function names for external entities
                    sanitized_name = self._sanitize_external_name(function_name)
                    sanitized_id = f'unresolved:function_{sanitized_name}'
                    
                    # Create stub entity for external function
                    external_entity = ParsedEntity(
                        id=sanitized_id,
                        name=sanitized_name,
                        type='ExternalFunction',
                        file_path='<external>',
                        line_start=0,
                        line_end=0,
                        metadata={
                            'external': True,
                            'stub': True,
                            'function_name': function_name,
                            'language': 'javascript',
                            'source': 'external_reference'
                        }
                    )
                    external_entities.append(external_entity)
                    existing_entity_ids.add(sanitized_id)  # Prevent duplicates
                    # Update relationship to use sanitized ID
                    rel.to_id = sanitized_id
            
            # Handle other unresolved references (modules, properties, etc.)
            elif rel.to_id.startswith('unresolved:') and rel.to_id not in existing_entity_ids:
                reference_type = rel.to_id.split(':')[1].split('_')[0]  # Extract type from unresolved:type_name
                reference_name = rel.to_id.replace(f'unresolved:{reference_type}_', '')
                
                # Map reference types to entity types
                entity_type_map = {
                    'module': 'ExternalModule',
                    'export': 'ExternalExport', 
                    'external': 'ExternalSymbol',
                    'property': 'ExternalProperty',
                    'template': 'ExternalTemplate',
                    'style': 'ExternalStyle'
                }
                
                entity_type = entity_type_map.get(reference_type, 'ExternalReference')
                
                # Sanitize name for external entities
                sanitized_name = self._sanitize_external_name(reference_name)
                sanitized_id = f'unresolved:{reference_type}_{sanitized_name}'
                
                external_entity = ParsedEntity(
                    id=sanitized_id,
                    name=sanitized_name,
                    type=entity_type,
                    file_path='<external>',
                    line_start=0,
                    line_end=0,
                    metadata={
                        'external': True,
                        'stub': True,
                        'reference_type': reference_type,
                        'reference_name': reference_name,
                        'language': 'javascript',
                        'source': 'external_reference'
                    }
                )
                external_entities.append(external_entity)
                existing_entity_ids.add(sanitized_id)
                # Update relationship to use sanitized ID
                rel.to_id = sanitized_id
        
        if external_entities:
            logger.debug(f"Created {len(external_entities)} external entities for unresolved references")
        
        return external_entities
