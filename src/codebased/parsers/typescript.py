"""
TypeScript parser for CodeBased using tree-sitter.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from .base import TreeSitterParser, ParsedEntity, ParsedRelationship
try:
    from tree_sitter import Node
except ImportError:
    Node = None

logger = logging.getLogger(__name__)


class TypeScriptParser(TreeSitterParser):
    """TypeScript parser using tree-sitter."""

    SUPPORTED_FILE_TYPES = {"typescript"}
    TREE_SITTER_LANGUAGE = "typescript"

    # TypeScript node types we want to extract as entities
    ENTITY_NODE_TYPES = {
        'class_declaration': 'Class',
        'interface_declaration': 'Interface', 
        'function_declaration': 'Function',
        'method_definition': 'Method',
        'variable_declaration': 'Variable',
        'type_alias_declaration': 'Type',
        'enum_declaration': 'Enum',
        'import_statement': 'Import',
        'export_statement': 'Export',
        'constructor_definition': 'Constructor',
        'get_accessor': 'Getter',
        'set_accessor': 'Setter',
        'decorator': 'Decorator'
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
        """Extract TypeScript entities from tree-sitter AST."""
        entities = []
        
        # Add file entity
        entities.append(self._create_file_entity(file_path, source_code))
        
        # Traverse tree and extract entities
        self._traverse_for_entities(node, source_code, file_path, entities)
        
        return entities

    def _extract_relationships_from_node(self, node: Node, source_code: str, 
                                       entities: List[ParsedEntity], file_path: str) -> List[ParsedRelationship]:
        """Extract TypeScript relationships from tree-sitter AST."""
        relationships = []
        
        # Create entity lookup for relationships
        entity_lookup = {entity.name: entity for entity in entities}
        
        # Traverse tree and extract relationships
        self._traverse_for_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        
        return relationships
    
    def _normalize_relationship_metadata(self, relationship: ParsedRelationship) -> Dict[str, Any]:
        """
        Normalize TypeScript relationship metadata to match database schema.
        
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
            id=self._generate_entity_id(filename, file_path, 1, 
                                       entity_type="File", line_end=len(lines)),
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
                'language': 'typescript'
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
                'language': 'typescript'
            })
            
            return ParsedEntity(
                id=self._generate_entity_id(name, file_path, start_line, 
                                           entity_type=entity_type, line_end=end_line),
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

    def _extract_name_from_node(self, node: Node, source_code: str) -> str:
        """Extract the name/identifier from a node."""
        # Look for identifier child nodes
        for child in node.children:
            if child.type == 'identifier':
                return self._get_node_text(child, source_code)
            elif child.type == 'property_identifier':
                return self._get_node_text(child, source_code)
        
        # Fallback: if no identifier found, try to extract from node text
        node_text = self._get_node_text(node, source_code)
        
        # For variable declarations, extract from declarator
        if node.type == 'variable_declaration':
            for child in node.children:
                if child.type == 'variable_declarator':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            return self._get_node_text(grandchild, source_code)
        
        # Simple extraction for common patterns
        if node.type in ['class_declaration', 'interface_declaration', 'function_declaration']:
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
            elif entity_type == 'Interface':
                metadata.update(self._extract_interface_metadata(node, source_code))
            elif entity_type == 'Method':
                metadata.update(self._extract_method_metadata(node, source_code))
            elif entity_type in ['Import', 'Export']:
                metadata.update(self._extract_import_export_metadata(node, source_code))
                
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
                    if member.type in ['method_definition', 'constructor_definition']:
                        method_count += 1
                    elif member.type in ['field_definition', 'public_field_definition']:
                        property_count += 1
        
        metadata.update({
            'method_count': method_count,
            'property_count': property_count
        })
        
        return metadata

    def _extract_function_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to function declarations."""
        metadata = {}
        
        # Extract parameters
        parameters = []
        for child in node.children:
            if child.type == 'formal_parameters':
                param_text = self._get_node_text(child, source_code)
                metadata['parameters'] = param_text
                
                # Count parameters
                param_count = param_text.count(',') + 1 if param_text.strip() != '()' else 0
                metadata['parameter_count'] = param_count
        
        # Check if async
        node_text = self._get_node_text(node, source_code)
        metadata['is_async'] = 'async' in node_text
        
        return metadata

    def _extract_interface_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to interface declarations."""
        metadata = {}
        
        # Count properties/methods in interface
        property_count = 0
        method_count = 0
        
        for child in node.children:
            if child.type == 'object_type':
                for member in child.children:
                    if member.type == 'property_signature':
                        property_count += 1
                    elif member.type == 'method_signature':
                        method_count += 1
        
        metadata.update({
            'property_count': property_count,
            'method_count': method_count
        })
        
        return metadata

    def _extract_method_metadata(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Extract metadata specific to method definitions."""
        metadata = {}
        
        node_text = self._get_node_text(node, source_code)
        
        # Check accessibility
        if 'private' in node_text:
            metadata['accessibility'] = 'private'
        elif 'protected' in node_text:
            metadata['accessibility'] = 'protected'
        elif 'public' in node_text:
            metadata['accessibility'] = 'public'
        
        # Check if static
        metadata['is_static'] = 'static' in node_text
        metadata['is_async'] = 'async' in node_text
        
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
        
        return metadata

    def _create_angular_decorator_entity(self, node: Node, source_code: str, file_path: str) -> Optional[ParsedEntity]:
        """Create entity from Angular decorator node."""
        try:
            decorator_text = self._get_node_text(node, source_code)
            start_line, end_line = self._get_node_line_info(node)
            
            # Extract decorator name from @DecoratorName syntax
            decorator_name = self._extract_decorator_name(node, source_code)
            if not decorator_name:
                return None
            
            # Check if this is an Angular decorator
            if decorator_name not in self.ANGULAR_DECORATORS:
                return None
            
            angular_entity_type = self.ANGULAR_DECORATORS[decorator_name]
            
            # Parse decorator arguments to extract Angular configuration
            angular_config = self._parse_decorator_arguments(node, source_code)
            
            # Create entity name based on selector or class name
            entity_name = self._extract_angular_entity_name(decorator_name, angular_config, node, source_code)
            
            if not entity_name:
                return None
            
            # Create Angular-specific metadata
            metadata = {
                'node_type': 'decorator',
                'decorator_name': decorator_name,
                'angular_type': angular_entity_type,
                'language': 'typescript',
                'framework': 'angular',
                'code_snippet': decorator_text[:500]
            }
            
            # Add Angular-specific configuration to metadata
            metadata.update(angular_config)
            
            return ParsedEntity(
                id=self._generate_entity_id(entity_name, file_path, start_line, 
                                           entity_type=angular_entity_type, line_end=end_line),
                name=entity_name,
                type=angular_entity_type,
                file_path=file_path,
                line_start=start_line,
                line_end=end_line,
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Failed to create Angular decorator entity: {e}")
            return None

    def _extract_decorator_name(self, node: Node, source_code: str) -> Optional[str]:
        """Extract decorator name from @DecoratorName syntax."""
        try:
            # Look for call_expression child which contains the decorator name
            for child in node.children:
                if child.type == 'call_expression':
                    # Get the identifier (decorator name)
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            return self._get_node_text(grandchild, source_code)
                elif child.type == 'identifier':
                    # Simple decorator without arguments like @Injectable
                    return self._get_node_text(child, source_code)
            
            # Fallback: parse from node text
            decorator_text = self._get_node_text(node, source_code)
            if decorator_text.startswith('@'):
                name_part = decorator_text[1:].split('(')[0].strip()
                return name_part
                
        except Exception as e:
            logger.debug(f"Failed to extract decorator name: {e}")
        
        return None

    def _parse_decorator_arguments(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Parse decorator arguments to extract Angular configuration."""
        config = {}
        
        try:
            # Look for call_expression containing arguments
            for child in node.children:
                if child.type == 'call_expression':
                    # Look for arguments (object literal)
                    for grandchild in child.children:
                        if grandchild.type == 'arguments':
                            # Parse the object literal arguments
                            for arg in grandchild.children:
                                if arg.type == 'object':
                                    config.update(self._parse_object_literal(arg, source_code))
                                    
        except Exception as e:
            logger.debug(f"Failed to parse decorator arguments: {e}")
        
        return config

    def _parse_object_literal(self, node: Node, source_code: str) -> Dict[str, Any]:
        """Parse TypeScript object literal to extract key-value pairs."""
        result = {}
        
        try:
            for child in node.children:
                if child.type == 'pair':
                    key_node = None
                    value_node = None
                    
                    # Extract key and value from pair
                    for grandchild in child.children:
                        if grandchild.type in ['property_identifier', 'string']:
                            if key_node is None:
                                key_node = grandchild
                            else:
                                value_node = grandchild
                        elif grandchild.type in ['string', 'array', 'true', 'false', 'template_string']:
                            value_node = grandchild
                    
                    if key_node:
                        key = self._get_node_text(key_node, source_code).strip('\'"')
                        value = self._get_node_text(value_node, source_code) if value_node else ""
                        
                        # Clean up common Angular configuration values
                        if key in ['selector', 'templateUrl', 'styleUrl']:
                            value = value.strip('\'"')
                        elif key == 'standalone':
                            value = value.lower() == 'true'
                        elif key == 'imports':
                            # Parse imports array
                            value = self._parse_imports_array(value_node, source_code) if value_node else []
                        
                        result[key] = value
                        
        except Exception as e:
            logger.debug(f"Failed to parse object literal: {e}")
        
        return result

    def _parse_imports_array(self, node: Node, source_code: str) -> List[str]:
        """Parse Angular imports array from AST node."""
        imports = []
        
        try:
            if node and node.type == 'array':
                for child in node.children:
                    if child.type == 'identifier':
                        imports.append(self._get_node_text(child, source_code))
                        
        except Exception as e:
            logger.debug(f"Failed to parse imports array: {e}")
        
        return imports

    def _extract_angular_entity_name(self, decorator_name: str, config: Dict[str, Any], 
                                   node: Node, source_code: str) -> Optional[str]:
        """Extract appropriate name for Angular entity."""
        try:
            # For Components, prefer selector if available
            if decorator_name == 'Component' and 'selector' in config:
                return config['selector']
            
            # For other decorators or fallback, look for the decorated class name
            # We need to find the class declaration that follows this decorator
            return self._find_decorated_class_name(node, source_code)
                
        except Exception as e:
            logger.debug(f"Failed to extract Angular entity name: {e}")
            return None

    def _find_decorated_class_name(self, decorator_node: Node, source_code: str) -> Optional[str]:
        """Find the class name that this decorator is applied to."""
        try:
            # In tree-sitter, decorators are typically siblings of the class they decorate
            # We need to find the next class_declaration node
            parent = decorator_node.parent
            if parent:
                for sibling in parent.children:
                    if sibling.type == 'export_statement':
                        # Look inside export statement for class
                        for export_child in sibling.children:
                            if export_child.type == 'class_declaration':
                                return self._extract_name_from_node(export_child, source_code)
                    elif sibling.type == 'class_declaration':
                        return self._extract_name_from_node(sibling, source_code)
                        
        except Exception as e:
            logger.debug(f"Failed to find decorated class name: {e}")
        
        return f"angular_entity_{id(decorator_node)}"  # Fallback unique name

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
                        # Create function call relationship with schema-correct properties
                        relationships.append(ParsedRelationship(
                            from_id=caller_entity.id,
                            to_id=f"function_{function_name}",
                            relationship_type="CALLS",
                            metadata={
                                'call_type': 'function_call',
                                'line_number': self._get_node_line_info(node)[0]
                            }
                        ))
                        
            except Exception as e:
                logger.debug(f"Failed to extract function call relationship: {e}")
    
    def _extract_interface_implementation_relationships(self, node: Node, source_code: str, file_path: str,
                                                      entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                                      entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract interface implementation relationships."""
        if node.type == 'class_declaration':
            try:
                class_name = self._extract_name_from_node(node, source_code)
                
                # Look for implements clause
                for child in node.children:
                    if child.type == 'class_heritage':
                        heritage_text = self._get_node_text(child, source_code)
                        
                        if 'implements' in heritage_text:
                            # Extract interface names
                            implements_part = heritage_text.split('implements')[1].strip()
                            interfaces = [iface.strip() for iface in implements_part.split(',')]
                            
                            for interface_name in interfaces:
                                if interface_name and interface_name in entity_lookup:
                                    relationships.append(ParsedRelationship(
                                        from_id=entity_lookup[class_name].id,
                                        to_id=entity_lookup[interface_name].id,
                                        relationship_type="IMPLEMENTS",
                                        metadata={}  # IMPLEMENTS has no properties in schema
                                    ))
                                    
            except Exception as e:
                logger.debug(f"Failed to extract interface implementation: {e}")
    
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
                    relationships.append(ParsedRelationship(
                        from_id=accessor_entity.id,
                        to_id=f"property_{access_text}",
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

    def _extract_angular_template_relationships(self, node: Node, source_code: str, file_path: str,
                                              entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                              entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Extract Angular template and style relationships from decorators."""
        try:
            # Check if this is an Angular decorator
            decorator_name = self._extract_decorator_name(node, source_code)
            if not decorator_name or decorator_name not in self.ANGULAR_DECORATORS:
                return
            
            # Only process Component decorators for template/style relationships
            if decorator_name != 'Component':
                return
            
            # Parse decorator arguments to get Angular configuration
            angular_config = self._parse_decorator_arguments(node, source_code)
            
            # Find the Angular component entity
            component_entity = None
            for entity in entities:
                if (entity.type == 'AngularComponent' and 
                    entity.line_start <= self._get_node_line_info(node)[0] <= entity.line_end):
                    component_entity = entity
                    break
            
            if not component_entity:
                return
            
            # Create template relationship
            if 'templateUrl' in angular_config:
                template_path = angular_config['templateUrl']
                if template_path:
                    # Use original relative path - the extractor will handle resolution patterns
                    clean_template_path = template_path.strip('\'"')
                    
                    relationships.append(ParsedRelationship(
                        from_id=component_entity.id,
                        to_id=f"unresolved:template_{clean_template_path}",  # Use original path
                        relationship_type="USES_TEMPLATE",
                        metadata={
                            'template_path': clean_template_path,
                            'resolved_path': self._resolve_angular_file_path(template_path, file_path),
                            'component_selector': angular_config.get('selector', ''),
                            'component_file_path': file_path  # Add for resolution context
                        }
                    ))
            
            # Handle inline template
            elif 'template' in angular_config:
                relationships.append(ParsedRelationship(
                    from_id=component_entity.id,
                    to_id=f"unresolved:inline_template_{component_entity.id}",
                    relationship_type="USES_TEMPLATE",
                    metadata={
                        'template_path': 'inline',
                        'resolved_path': 'inline', 
                        'component_selector': angular_config.get('selector', '')
                    }
                ))
            
            # Create style relationships
            if 'styleUrl' in angular_config:
                style_path = angular_config['styleUrl']
                if style_path:
                    # Use original relative path - the extractor will handle resolution patterns
                    clean_style_path = style_path.strip('\'"')
                    
                    relationships.append(ParsedRelationship(
                        from_id=component_entity.id,
                        to_id=f"unresolved:style_{clean_style_path}",
                        relationship_type="USES_STYLES",
                        metadata={
                            'style_path': clean_style_path,
                            'resolved_path': self._resolve_angular_file_path(style_path, file_path),
                            'component_selector': angular_config.get('selector', ''),
                            'component_file_path': file_path  # Add for resolution context
                        }
                    ))
            
            # Handle styleUrls array
            elif 'styleUrls' in angular_config:
                style_urls = angular_config['styleUrls']
                if isinstance(style_urls, list):
                    for style_path in style_urls:
                        if style_path:
                            # Use original relative path - the extractor will handle resolution patterns
                            clean_style_path = style_path.strip('\'"')
                            
                            relationships.append(ParsedRelationship(
                                from_id=component_entity.id,
                                to_id=f"unresolved:style_{clean_style_path}",
                                relationship_type="USES_STYLES",
                                metadata={
                                    'style_path': clean_style_path,
                                    'resolved_path': self._resolve_angular_file_path(style_path, file_path),
                                    'component_selector': angular_config.get('selector', ''),
                                    'component_file_path': file_path  # Add for resolution context
                                }
                            ))
            
            # Handle inline styles
            elif 'styles' in angular_config:
                relationships.append(ParsedRelationship(
                    from_id=component_entity.id,
                    to_id=f"unresolved:inline_styles_{component_entity.id}",
                    relationship_type="USES_STYLES",
                    metadata={
                        'style_path': 'inline',
                        'resolved_path': 'inline',
                        'component_selector': angular_config.get('selector', '')
                    }
                ))
                
        except Exception as e:
            logger.debug(f"Failed to extract Angular template relationships: {e}")

    def _resolve_angular_file_path(self, relative_path: str, component_file_path: str) -> str:
        """Resolve Angular template/style file path relative to component file."""
        try:
            from pathlib import Path
            
            # Clean the relative path
            clean_path = relative_path.strip('\'"')
            
            # Get component file directory
            component_dir = Path(component_file_path).parent
            
            # Resolve the relative path
            resolved_path = component_dir / clean_path
            
            # Return normalized path
            return str(resolved_path.resolve())
            
        except Exception as e:
            logger.debug(f"Failed to resolve Angular file path: {e}")
            # Fallback: return the original relative path
            return relative_path.strip('\'"')
    
    def _create_angular_file_resolution_patterns(self, relative_path: str, component_file_path: str) -> List[str]:
        """
        Create multiple path resolution patterns for Angular templates/styles.
        
        This creates patterns that align with how the symbol registry keys are created
        to improve resolution success rate.
        
        Args:
            relative_path: Original relative path from component decorator
            component_file_path: Path to the component file
            
        Returns:
            List of path patterns for resolution
        """
        patterns = []
        
        try:
            from pathlib import Path
            
            # Clean the relative path
            clean_path = relative_path.strip('\'"')
            
            # Pattern 1: Full resolved absolute path
            component_dir = Path(component_file_path).parent
            resolved_path = component_dir / clean_path
            absolute_path = str(resolved_path.resolve())
            patterns.append(absolute_path)
            
            # Pattern 2: Just the filename (for direct name matches)
            filename = Path(clean_path).name
            patterns.append(filename)
            
            # Pattern 3: Relative path as-is (for relative lookups)
            patterns.append(clean_path)
            
            # Pattern 4: Angular project structure relative path
            # If we're in src/app, create a path relative to src/app
            if 'src/app' in component_file_path:
                try:
                    component_path = Path(component_file_path)
                    parts = component_path.parts
                    if 'src' in parts and 'app' in parts:
                        src_idx = parts.index('src')
                        app_idx = parts.index('app')
                        if app_idx > src_idx:
                            # Get relative path from app directory
                            component_rel_dir = '/'.join(parts[app_idx+1:-1])  # exclude 'app' and filename
                            if component_rel_dir:
                                app_relative_path = f"{component_rel_dir}/{clean_path}"
                            else:
                                app_relative_path = clean_path
                            patterns.append(app_relative_path)
                            patterns.append(f"./{app_relative_path}")
                except Exception:
                    pass
            
            # Remove duplicates while preserving order
            unique_patterns = []
            for pattern in patterns:
                if pattern not in unique_patterns:
                    unique_patterns.append(pattern)
                    
            return unique_patterns
            
        except Exception as e:
            logger.debug(f"Failed to create resolution patterns: {e}")
            return [relative_path.strip('\'"')]

    def _traverse_for_relationships(self, node: Node, source_code: str, file_path: str,
                                  entities: List[ParsedEntity], relationships: List[ParsedRelationship],
                                  entity_lookup: Dict[str, ParsedEntity]) -> None:
        """Traverse AST and extract relationships."""
        
        # Look for specific relationship patterns
        if node.type == 'class_declaration':
            self._extract_class_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
            self._extract_interface_implementation_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'decorator':
            self._extract_angular_template_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type in ['import_statement', 'export_statement']:
            self._extract_import_export_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'call_expression':
            self._extract_function_call_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        elif node.type == 'member_expression':
            self._extract_property_access_relationships(node, source_code, file_path, entities, relationships, entity_lookup)
        
        # Recursively process children
        for child in node.children:
            self._traverse_for_relationships(child, source_code, file_path, entities, relationships, entity_lookup)

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
                            metadata={}  # EXTENDS has no properties in schema
                        ))

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
                # Find the Import entity that was created for this node
                import_entity = None
                for entity in entities:
                    if entity.type == 'Import' and entity.line_start == self._get_node_line_info(node)[0]:
                        import_entity = entity
                        break
                
                # Extract imported module path
                if 'from' in node_text:
                    parts = node_text.split('from')
                    if len(parts) > 1:
                        module_path = parts[1].strip().strip('\'"')
                        
                        # Create import relationship - mark external modules as unresolved
                        relationships.append(ParsedRelationship(
                            from_id=file_entity.id,
                            to_id=f"unresolved:module_{module_path}",  # Mark as unresolved
                            relationship_type="IMPORTS",
                            metadata={
                                'module_path': module_path,
                                'is_relative': module_path.startswith('.'),
                                'import_text': parts[0].strip()
                            }
                        ))
                        
                        # If we have an Import entity, create a FILE_CONTAINS_IMPORT relationship
                        if import_entity:
                            relationships.append(ParsedRelationship(
                                from_id=file_entity.id,
                                to_id=import_entity.id,
                                relationship_type="FILE_CONTAINS_IMPORT",
                                metadata={}
                            ))
                        
                        # Extract specific imports
                        import_spec = parts[0].replace('import', '').strip()
                        if '{' in import_spec and '}' in import_spec:
                            # Named imports
                            named_imports = import_spec.split('{')[1].split('}')[0]
                            for named_import in named_imports.split(','):
                                clean_import = named_import.strip()
                                if clean_import:
                                    relationships.append(ParsedRelationship(
                                        from_id=file_entity.id,
                                        to_id=f"unresolved:external_{clean_import}",  # Mark as unresolved
                                        relationship_type="USES", 
                                        metadata={
                                            'usage_type': 'named_import',
                                            'line_number': self._get_node_line_info(node)[0]
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
                            'export_type': 'default_export',
                            'symbol': export_spec
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
                                    'export_type': 'named_export',
                                    'symbol': clean_export
                                }
                            ))
                            
        except Exception as e:
            logger.debug(f"Failed to extract import/export relationships: {e}")
