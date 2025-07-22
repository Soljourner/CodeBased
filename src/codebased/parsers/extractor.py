"""
Entity and relationship extraction coordination for CodeBased.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import ParseResult, ParsedEntity, ParsedRelationship
from .python import PythonASTParser
from ..database.service import DatabaseService
from ..config import CodeBasedConfig

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Coordinates entity extraction from source code."""
    
    def __init__(self, config: CodeBasedConfig, db_service: DatabaseService):
        """
        Initialize entity extractor.
        
        Args:
            config: CodeBased configuration
            db_service: Database service instance
        """
        self.config = config
        self.db_service = db_service
        
        # Initialize parsers
        self.parsers = {
            'python': PythonASTParser(self._get_parser_config())
        }
        
        # Symbol registry for cross-file resolution
        self.symbol_registry: Dict[str, ParsedEntity] = {}
        self.unresolved_references: List[Tuple[ParsedRelationship, str]] = []
    
    def _get_parser_config(self) -> Dict[str, Any]:
        """Get parser configuration from main config."""
        return {
            'file_extensions': self.config.parsing.file_extensions,
            'exclude_patterns': self.config.parsing.exclude_patterns,
            'max_file_size': self.config.parsing.max_file_size,
            'follow_symlinks': self.config.parsing.follow_symlinks,
            'include_docstrings': self.config.parsing.include_docstrings
        }
    
    def extract_from_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Extract entities and relationships from entire directory.
        
        Args:
            directory_path: Root directory to parse
            
        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Starting entity extraction from {directory_path}")
        start_time = time.time()
        
        results = {
            'files_processed': 0,
            'files_failed': 0,
            'entities_extracted': 0,
            'relationships_extracted': 0,
            'errors': [],
            'parse_results': []
        }
        
        try:
            # Two-pass extraction
            parse_results = self._two_pass_extraction(directory_path)
            
            # Store results in database
            self._store_results(parse_results)
            
            # Calculate statistics
            for result in parse_results:
                results['parse_results'].append(result)
                
                if result.errors:
                    results['files_failed'] += 1
                    results['errors'].extend(result.errors)
                else:
                    results['files_processed'] += 1
                
                results['entities_extracted'] += len(result.entities)
                results['relationships_extracted'] += len(result.relationships)
            
            total_time = time.time() - start_time
            logger.info(f"Entity extraction completed in {total_time:.2f}s")
            logger.info(f"Processed {results['files_processed']} files, "
                       f"extracted {results['entities_extracted']} entities, "
                       f"{results['relationships_extracted']} relationships")
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def _two_pass_extraction(self, directory_path: str) -> List[ParseResult]:
        """
        Perform two-pass extraction for cross-file resolution.
        
        Args:
            directory_path: Directory to parse
            
        Returns:
            List of parse results
        """
        directory_path = Path(directory_path)
        parse_results = []
        
        # Find all parseable files
        all_files = []
        for parser in self.parsers.values():
            for file_path in parser._find_parseable_files(directory_path):
                all_files.append(str(file_path))
        
        logger.info(f"Found {len(all_files)} files to parse")
        
        # Pass 1: Extract entities and build symbol registry
        logger.info("Starting Pass 1: Entity extraction and symbol registration")
        pass1_results = self._extract_entities_parallel(all_files)
        
        # Build symbol registry from all entities
        for result in pass1_results:
            for entity in result.entities:
                self._register_symbol(entity)
        
        logger.info(f"Pass 1 completed: {len(self.symbol_registry)} symbols registered")
        
        # Pass 2: Resolve relationships using symbol registry
        logger.info("Starting Pass 2: Relationship resolution")
        pass2_results = self._resolve_relationships(pass1_results)
        
        logger.info("Pass 2 completed: Relationships resolved")
        
        return pass2_results
    
    def _extract_entities_parallel(self, file_paths: List[str]) -> List[ParseResult]:
        """
        Extract entities from files in parallel.
        
        Args:
            file_paths: List of file paths to parse
            
        Returns:
            List of parse results
        """
        results = []
        max_workers = min(4, len(file_paths))  # Limit concurrent parsers
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit parsing tasks
            future_to_file = {}
            for file_path in file_paths:
                parser = self._get_parser_for_file(file_path)
                if parser:
                    future = executor.submit(parser.parse_file, file_path)
                    future_to_file[future] = file_path
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    # Create error result
                    error_result = ParseResult([], [], "", file_path, [str(e)], 0.0)
                    results.append(error_result)
        
        return results
    
    def _resolve_relationships(self, parse_results: List[ParseResult]) -> List[ParseResult]:
        """
        Resolve unresolved relationships using symbol registry.
        
        Args:
            parse_results: Results from first pass
            
        Returns:
            Updated parse results with resolved relationships
        """
        resolved_results = []
        
        for result in parse_results:
            resolved_relationships = []
            
            for relationship in result.relationships:
                # Check if relationship needs resolution
                if relationship.to_id.startswith("unresolved:"):
                    resolved_id = self._resolve_symbol_reference(relationship.to_id)
                    if resolved_id:
                        # Create resolved relationship
                        resolved_rel = ParsedRelationship(
                            from_id=relationship.from_id,
                            to_id=resolved_id,
                            relationship_type=relationship.relationship_type,
                            metadata=relationship.metadata
                        )
                        resolved_relationships.append(resolved_rel)
                    else:
                        # Keep unresolved for external dependencies
                        resolved_relationships.append(relationship)
                else:
                    # Already resolved
                    resolved_relationships.append(relationship)
            
            # Create updated result
            resolved_result = ParseResult(
                entities=result.entities,
                relationships=resolved_relationships,
                file_hash=result.file_hash,
                file_path=result.file_path,
                errors=result.errors,
                parse_time=result.parse_time
            )
            resolved_results.append(resolved_result)
        
        return resolved_results
    
    def _register_symbol(self, entity: ParsedEntity) -> None:
        """
        Register entity in symbol registry.
        
        Args:
            entity: Entity to register
        """
        # Create various lookup keys for the entity
        keys = [entity.name]
        
        # Add qualified names
        if entity.type == "Function" and "class_id" in entity.metadata:
            class_name = self._get_entity_name_by_id(entity.metadata["class_id"])
            if class_name:
                keys.append(f"{class_name}.{entity.name}")
        
        if entity.type == "Class" and "module_id" in entity.metadata:
            module_name = self._get_entity_name_by_id(entity.metadata["module_id"])
            if module_name:
                keys.append(f"{module_name}.{entity.name}")
        
        # Register under all keys
        for key in keys:
            if key not in self.symbol_registry:
                self.symbol_registry[key] = entity
            else:
                # Handle name conflicts by preferring more specific matches
                existing = self.symbol_registry[key]
                if self._is_more_specific(entity, existing):
                    self.symbol_registry[key] = entity
    
    def _resolve_symbol_reference(self, unresolved_ref: str) -> Optional[str]:
        """
        Resolve an unresolved symbol reference.
        
        Args:
            unresolved_ref: Unresolved reference (e.g., "unresolved:ClassName")
            
        Returns:
            Resolved entity ID or None
        """
        if not unresolved_ref.startswith("unresolved:"):
            return unresolved_ref
        
        symbol_name = unresolved_ref[11:]  # Remove "unresolved:" prefix
        
        # Direct lookup
        if symbol_name in self.symbol_registry:
            return self.symbol_registry[symbol_name].id
        
        # Try partial matches for qualified names
        for registered_name, entity in self.symbol_registry.items():
            if registered_name.endswith(f".{symbol_name}") or symbol_name.endswith(f".{registered_name}"):
                return entity.id
        
        return None
    
    def _get_parser_for_file(self, file_path: str) -> Optional[Any]:
        """
        Get appropriate parser for file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Parser instance or None
        """
        for parser in self.parsers.values():
            if parser.can_parse(file_path):
                return parser
        return None
    
    def _get_entity_name_by_id(self, entity_id: str) -> Optional[str]:
        """
        Get entity name by ID from registry.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity name or None
        """
        for entity in self.symbol_registry.values():
            if entity.id == entity_id:
                return entity.name
        return None
    
    def _is_more_specific(self, entity1: ParsedEntity, entity2: ParsedEntity) -> bool:
        """
        Check if entity1 is more specific than entity2.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            True if entity1 is more specific
        """
        # Prefer entities with class/module context over global ones
        weight1 = 0
        weight2 = 0
        
        if "class_id" in entity1.metadata and entity1.metadata["class_id"]:
            weight1 += 2
        if "module_id" in entity1.metadata and entity1.metadata["module_id"]:
            weight1 += 1
        
        if "class_id" in entity2.metadata and entity2.metadata["class_id"]:
            weight2 += 2
        if "module_id" in entity2.metadata and entity2.metadata["module_id"]:
            weight2 += 1
        
        return weight1 > weight2
    
    def _store_results(self, parse_results: List[ParseResult]) -> None:
        """
        Store parse results in database.
        
        Args:
            parse_results: Results to store
        """
        logger.info("Storing extraction results in database...")
        
        try:
            # Prepare batch queries for entities
            entity_queries = []
            relationship_queries = []
            
            for result in parse_results:
                # Store entities
                for entity in result.entities:
                    query = self._create_entity_insert_query(entity)
                    if query:
                        entity_queries.append(query)
                
                # Store relationships
                for relationship in result.relationships:
                    query = self._create_relationship_insert_query(relationship)
                    if query:
                        relationship_queries.append(query)
            
            # Execute in batches
            batch_size = self.config.database.batch_size
            
            # Insert entities in batches
            for i in range(0, len(entity_queries), batch_size):
                batch = entity_queries[i:i + batch_size]
                if not self.db_service.execute_batch(batch):
                    logger.error(f"Failed to insert entity batch {i // batch_size + 1}")
            
            # Insert relationships in batches
            for i in range(0, len(relationship_queries), batch_size):
                batch = relationship_queries[i:i + batch_size]
                if not self.db_service.execute_batch(batch):
                    logger.error(f"Failed to insert relationship batch {i // batch_size + 1}")
            
            logger.info(f"Stored {len(entity_queries)} entities and {len(relationship_queries)} relationships")
            
        except Exception as e:
            logger.error(f"Failed to store results in database: {e}")
    
    def _create_entity_insert_query(self, entity: ParsedEntity) -> Optional[str]:
        """
        Create Cypher query to insert entity.
        
        Args:
            entity: Entity to insert
            
        Returns:
            Cypher query string or None
        """
        try:
            # Escape string values
            def escape_string(value):
                if isinstance(value, str):
                    escaped = value.replace('"', '\\"')
                    return f'"{escaped}"'
                return str(value)
            
            # Build property list based on entity type
            properties = [
                f'id: {escape_string(entity.id)}',
                f'name: {escape_string(entity.name)}'
            ]
            
            # Add type-specific properties
            if entity.type == 'File':
                properties.append(f'path: {escape_string(entity.file_path)}')
            else:
                # Get the file_id from entity metadata
                file_id = entity.metadata.get('file_id', '')
                if file_id:
                    properties.append(f'file_id: {escape_string(file_id)}')
            
            # Add line information based on entity type
            if entity.type in ['Module', 'Class', 'Function']:
                if hasattr(entity, 'line_start') and entity.line_start is not None:
                    properties.append(f'line_start: {entity.line_start}')
                if hasattr(entity, 'line_end') and entity.line_end is not None:
                    properties.append(f'line_end: {entity.line_end}')
            elif entity.type in ['Import', 'Variable']:
                if hasattr(entity, 'line_start') and entity.line_start is not None:
                    properties.append(f'line_number: {entity.line_start}')
            
            # Add metadata properties that match the schema
            schema_properties = {
                'File': ['extension', 'size', 'modified_time', 'hash', 'lines_of_code'],
                'Module': ['docstring'],
                'Class': ['module_id', 'docstring', 'is_abstract'],
                'Function': ['module_id', 'class_id', 'docstring', 'signature', 'return_type', 
                           'is_async', 'is_generator', 'is_property', 'is_staticmethod', 'is_classmethod', 'complexity'],
                'Variable': ['scope_id', 'type_annotation', 'is_global', 'is_constant'],
                'Import': ['module_name', 'alias', 'is_from_import']
            }
            
            allowed_props = schema_properties.get(entity.type, [])
            for key, value in entity.metadata.items():
                if value is not None and key in allowed_props:
                    if isinstance(value, bool):
                        properties.append(f'{key}: {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        properties.append(f'{key}: {value}')
                    else:
                        properties.append(f'{key}: {escape_string(str(value))}')
            
            props_str = ', '.join(properties)
            query = f"CREATE (:{entity.type} {{{props_str}}})"
            
            return query
            
        except Exception as e:
            logger.error(f"Failed to create entity query for {entity.name}: {e}")
            return None
    
    def _create_relationship_insert_query(self, relationship: ParsedRelationship) -> Optional[str]:
        """
        Create Cypher query to insert relationship.
        
        Args:
            relationship: Relationship to insert
            
        Returns:
            Cypher query string or None
        """
        try:
            # Skip unresolved relationships
            if (relationship.from_id.startswith("unresolved:") or 
                relationship.to_id.startswith("unresolved:")):
                return None
            
            # Escape string values
            def escape_string(value):
                if isinstance(value, str):
                    escaped = value.replace('"', '\\"')
                    return f'"{escaped}"'
                return str(value)
            
            # Build relationship properties
            properties = []
            for key, value in relationship.metadata.items():
                if value is not None:
                    if isinstance(value, bool):
                        properties.append(f'{key}: {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        properties.append(f'{key}: {value}')
                    else:
                        properties.append(f'{key}: {escape_string(str(value))}')
            
            props_str = '{' + ', '.join(properties) + '}' if properties else ''
            
            # Create relationship query using Kuzu syntax
            # All our relationship tables are now single-pair, so we can use CREATE
            query = f"""
            MATCH (from_node {{id: {escape_string(relationship.from_id)}}}), 
                  (to_node {{id: {escape_string(relationship.to_id)}}})
            CREATE (from_node)-[:{relationship.relationship_type} {props_str}]->(to_node)
            """
            
            return query.strip()
            
        except Exception as e:
            logger.error(f"Failed to create relationship query: {e}")
            return None