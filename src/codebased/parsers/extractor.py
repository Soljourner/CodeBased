"""
Entity and relationship extraction coordination for CodeBased.
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import ParseResult, ParsedEntity, ParsedRelationship
from .registry import PARSER_REGISTRY
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
        
        # Initialize parsers dynamically from registry
        self.parsers = {}
        parser_config = self._get_parser_config()
        for name, parser_cls in PARSER_REGISTRY.items():
            try:
                self.parsers[name] = parser_cls(parser_config)
            except Exception as e:  # pragma: no cover - initialization failure
                logger.error(f"Failed to initialize parser '{name}': {e}")
        
        # Symbol registry for cross-file resolution
        self.symbol_registry: Dict[str, ParsedEntity] = {}
        self.unresolved_references: List[Tuple[ParsedRelationship, str]] = []
    
    def _get_parser_config(self) -> Dict[str, Any]:
        """Get parser configuration from main config."""
        return {
            # Note: file_extensions not passed - each parser uses its own SUPPORTED_FILE_TYPES
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
        
        # Deduplicate files to prevent multiple parsers processing the same file
        unique_files = list(set(all_files))
        logger.info(f"Found {len(all_files)} total files, {len(unique_files)} unique files to parse")
        
        # Pass 1: Extract entities and build symbol registry
        logger.info("Starting Pass 1: Entity extraction and symbol registration")
        pass1_results = self._extract_entities_parallel(unique_files)
        
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
                    resolved_id = self._resolve_symbol_reference(relationship.to_id, relationship.metadata)
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
        Register entity in symbol registry with enhanced lookup patterns.
        
        Args:
            entity: Entity to register
        """
        # Create various lookup keys for the entity
        keys = [entity.name]
        
        # Add file-based lookups for File entities
        if entity.type == "File":
            # Register by full file path
            keys.append(f"file:{entity.file_path}")
            
            # Register by relative path patterns for templates/styles
            from pathlib import Path
            file_path = Path(entity.file_path)
            
            # Add relative path from different base directories
            if file_path.suffix in ['.html', '.htm']:
                keys.append(f"template:{file_path.name}")
                keys.append(f"template:./{file_path.name}")
                
                # Add relative paths for Angular resolution
                if str(file_path).find('src/app') != -1:
                    # Extract path relative to src/app
                    parts = file_path.parts
                    if 'src' in parts and 'app' in parts:
                        src_idx = parts.index('src')
                        app_idx = parts.index('app')
                        if app_idx > src_idx:
                            rel_path = '/'.join(parts[app_idx:])
                            keys.append(f"template:./{rel_path}")
                
                # CRITICAL: Also register the absolute path for direct resolution
                keys.append(f"template:{entity.file_path}")
            
            elif file_path.suffix in ['.css', '.scss', '.sass']:
                keys.append(f"style:{file_path.name}")
                keys.append(f"style:./{file_path.name}")
                
                # Add relative paths for Angular resolution
                if str(file_path).find('src/app') != -1:
                    parts = file_path.parts
                    if 'src' in parts and 'app' in parts:
                        src_idx = parts.index('src')
                        app_idx = parts.index('app')
                        if app_idx > src_idx:
                            rel_path = '/'.join(parts[app_idx:])
                            keys.append(f"style:./{rel_path}")
                
                # CRITICAL: Also register the absolute path for direct resolution
                keys.append(f"style:{entity.file_path}")
            
            # Register TypeScript/JavaScript modules
            elif file_path.suffix in ['.ts', '.js', '.tsx', '.jsx']:
                # Register as module import target
                module_name = file_path.stem  # filename without extension
                keys.append(f"module:{module_name}")
                
                # Add relative import paths
                if str(file_path).find('src/app') != -1:
                    parts = file_path.parts
                    if 'src' in parts and 'app' in parts:
                        src_idx = parts.index('src')
                        app_idx = parts.index('app')
                        if app_idx > src_idx:
                            rel_path = '/'.join(parts[app_idx:-1])  # exclude filename
                            if rel_path:
                                keys.append(f"module:./{rel_path}/{module_name}")
        
        # Add qualified names for class/function entities
        if entity.type == "Function" and "class_id" in entity.metadata:
            class_name = self._get_entity_name_by_id(entity.metadata["class_id"])
            if class_name:
                keys.append(f"{class_name}.{entity.name}")
        
        if entity.type == "Class" and "module_id" in entity.metadata:
            module_name = self._get_entity_name_by_id(entity.metadata["module_id"])
            if module_name:
                keys.append(f"{module_name}.{entity.name}")
        
        # Add entity type-specific keys
        if entity.type in ["AngularComponent", "AngularService", "AngularDirective"]:
            keys.append(f"angular:{entity.type}:{entity.name}")
            
            # For Angular components, also register by selector
            if entity.type == "AngularComponent" and "selector" in entity.metadata:
                selector = entity.metadata["selector"]
                keys.append(f"selector:{selector}")
        
        # Register under all keys
        for key in keys:
            if key not in self.symbol_registry:
                self.symbol_registry[key] = entity
            else:
                # Handle name conflicts by preferring more specific matches
                existing = self.symbol_registry[key]
                if self._is_more_specific(entity, existing):
                    self.symbol_registry[key] = entity
    
    def _resolve_symbol_reference(self, unresolved_ref: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Resolve an unresolved symbol reference using enhanced lookup patterns.
        
        Args:
            unresolved_ref: Unresolved reference (e.g., "unresolved:module_angular/core")
            metadata: Optional metadata from relationship for context
            
        Returns:
            Resolved entity ID or None
        """
        if not unresolved_ref.startswith("unresolved:"):
            return unresolved_ref
        
        symbol_name = unresolved_ref[11:]  # Remove "unresolved:" prefix
        metadata = metadata or {}
        
        # Handle different types of unresolved references
        if symbol_name.startswith("module_"):
            # Module import resolution
            module_path = symbol_name[7:]  # Remove "module_" prefix
            return self._resolve_module_reference(module_path)
            
        elif symbol_name.startswith("template_"):
            # Template file resolution
            template_path = symbol_name[9:]  # Remove "template_" prefix
            component_file_path = metadata.get('component_file_path')
            return self._resolve_template_reference(template_path, component_file_path)
            
        elif symbol_name.startswith("style_"):
            # Style file resolution
            style_path = symbol_name[6:]  # Remove "style_" prefix
            component_file_path = metadata.get('component_file_path')
            return self._resolve_style_reference(style_path, component_file_path)
            
        elif symbol_name.startswith("export_"):
            # Export resolution - these remain external for now
            return None
            
        elif symbol_name.startswith("external_"):
            # External symbol resolution - these remain external for now
            return None
        
        # Direct entity name lookup
        if symbol_name in self.symbol_registry:
            return self.symbol_registry[symbol_name].id
        
        # Try qualified name matches
        for registered_name, entity in self.symbol_registry.items():
            if registered_name.endswith(f".{symbol_name}") or symbol_name.endswith(f".{registered_name}"):
                return entity.id
        
        return None
    
    def _resolve_module_reference(self, module_path: str) -> Optional[str]:
        """
        Resolve a module import reference to a File entity.
        
        Args:
            module_path: Module path like "@angular/core" or "./app.component"
            
        Returns:
            Resolved File entity ID or None
        """
        # Skip external npm modules (start with @ or known libraries)
        if (module_path.startswith('@') or 
            module_path in ['rxjs', 'lodash', 'moment', 'axios'] or
            module_path.startswith('node_modules')):
            return None
        
        # Try direct module lookup
        module_key = f"module:{module_path}"
        if module_key in self.symbol_registry:
            return self.symbol_registry[module_key].id
        
        # Try without leading ./
        if module_path.startswith('./'):
            clean_path = module_path[2:]
            module_key = f"module:{clean_path}"
            if module_key in self.symbol_registry:
                return self.symbol_registry[module_key].id
        
        # Try looking for file directly
        file_key = f"file:{module_path}"
        if file_key in self.symbol_registry:
            return self.symbol_registry[file_key].id
            
        return None
    
    def _resolve_template_reference(self, template_path: str, component_file_path: str = None) -> Optional[str]:
        """
        Resolve a template path reference to an HTML File entity.
        
        Args:
            template_path: Template path like "./app.component.html"
            component_file_path: Optional path to the component file for context
            
        Returns:
            Resolved File entity ID or None
        """
        # Create multiple resolution patterns to try
        patterns_to_try = self._create_template_resolution_patterns(template_path, component_file_path)
        
        for pattern in patterns_to_try:
            # Try template-specific lookup
            template_key = f"template:{pattern}"
            if template_key in self.symbol_registry:
                logger.debug(f"Resolved template reference '{template_path}' to entity via pattern: {pattern}")
                return self.symbol_registry[template_key].id
            
            # Try direct file path lookup
            file_key = f"file:{pattern}"
            if file_key in self.symbol_registry:
                logger.debug(f"Resolved template reference '{template_path}' to file entity via pattern: {pattern}")
                return self.symbol_registry[file_key].id
                
        logger.debug(f"Failed to resolve template reference: {template_path}. Tried patterns: {patterns_to_try}")
        return None
    
    def _resolve_style_reference(self, style_path: str, component_file_path: str = None) -> Optional[str]:
        """
        Resolve a style path reference to a CSS File entity.
        
        Args:
            style_path: Style path like "./app.component.scss"
            component_file_path: Optional path to the component file for context
            
        Returns:
            Resolved File entity ID or None
        """
        # Create multiple resolution patterns to try
        patterns_to_try = self._create_style_resolution_patterns(style_path, component_file_path)
        
        for pattern in patterns_to_try:
            # Try style-specific lookup
            style_key = f"style:{pattern}"
            if style_key in self.symbol_registry:
                logger.debug(f"Resolved style reference '{style_path}' to entity via pattern: {pattern}")
                return self.symbol_registry[style_key].id
            
            # Try direct file path lookup
            file_key = f"file:{pattern}"
            if file_key in self.symbol_registry:
                logger.debug(f"Resolved style reference '{style_path}' to file entity via pattern: {pattern}")
                return self.symbol_registry[file_key].id
                
        logger.debug(f"Failed to resolve style reference: {style_path}. Tried patterns: {patterns_to_try}")
        return None
    
    def _create_template_resolution_patterns(self, template_path: str, component_file_path: str = None) -> List[str]:
        """
        Create multiple resolution patterns for template path resolution.
        
        Args:
            template_path: Original template path (can be relative or absolute)
            component_file_path: Optional path to the component file for context
            
        Returns:
            List of patterns to try for resolution
        """
        patterns = []
        from pathlib import Path
        
        # Pattern 1: Original path as-is (handles both relative and absolute)
        patterns.append(template_path)
        
        # Pattern 2: If we have component context, resolve relative to component
        if component_file_path and not os.path.isabs(template_path):
            try:
                component_dir = Path(component_file_path).parent
                resolved_path = component_dir / template_path
                absolute_resolved = str(resolved_path.resolve())
                patterns.append(absolute_resolved)
                
                # Also add the normalized version
                patterns.append(str(resolved_path.as_posix()))
            except Exception as e:
                logger.debug(f"Failed to resolve template path relative to component: {e}")
        
        # Pattern 3: Normalized absolute path (if it looks like an absolute path)
        if os.path.isabs(template_path):
            normalized_path = Path(template_path).as_posix()
            patterns.append(normalized_path)
            
            # Pattern 4: Just the filename from absolute path
            filename = Path(template_path).name
            patterns.append(filename)
            
            # Pattern 5: Relative patterns for absolute paths
            # Extract relative path from src/app onwards
            parts = Path(template_path).parts
            if 'src' in parts and 'app' in parts:
                src_idx = parts.index('src')
                app_idx = parts.index('app') 
                if app_idx > src_idx:
                    rel_from_app = '/'.join(parts[app_idx:])
                    patterns.append(f"./{rel_from_app}")
                    patterns.append(rel_from_app)
        else:
            # Pattern 4: Without leading ./
            if template_path.startswith('./'):
                clean_path = template_path[2:]
                patterns.append(clean_path)
            
            # Pattern 5: Just the filename
            filename = Path(template_path).name
            patterns.append(filename)
            
            # Pattern 6: With leading ./
            if not template_path.startswith('./'):
                patterns.append(f"./{template_path}")
        
        # Remove duplicates while preserving order
        unique_patterns = []
        for pattern in patterns:
            if pattern not in unique_patterns:
                unique_patterns.append(pattern)
                
        return unique_patterns
    
    def _create_style_resolution_patterns(self, style_path: str, component_file_path: str = None) -> List[str]:
        """
        Create multiple resolution patterns for style path resolution.
        
        Args:
            style_path: Original style path (can be relative or absolute)
            component_file_path: Optional path to the component file for context
            
        Returns:
            List of patterns to try for resolution
        """
        patterns = []
        from pathlib import Path
        
        # Pattern 1: Original path as-is (handles both relative and absolute)
        patterns.append(style_path)
        
        # Pattern 2: If we have component context, resolve relative to component
        if component_file_path and not os.path.isabs(style_path):
            try:
                component_dir = Path(component_file_path).parent
                resolved_path = component_dir / style_path
                absolute_resolved = str(resolved_path.resolve())
                patterns.append(absolute_resolved)
                
                # Also add the normalized version
                patterns.append(str(resolved_path.as_posix()))
            except Exception as e:
                logger.debug(f"Failed to resolve style path relative to component: {e}")
        
        # Pattern 3: Normalized absolute path (if it looks like an absolute path)
        if os.path.isabs(style_path):
            normalized_path = Path(style_path).as_posix()
            patterns.append(normalized_path)
            
            # Pattern 4: Just the filename from absolute path
            filename = Path(style_path).name
            patterns.append(filename)
            
            # Pattern 5: Relative patterns for absolute paths
            # Extract relative path from src/app onwards
            parts = Path(style_path).parts
            if 'src' in parts and 'app' in parts:
                src_idx = parts.index('src')
                app_idx = parts.index('app') 
                if app_idx > src_idx:
                    rel_from_app = '/'.join(parts[app_idx:])
                    patterns.append(f"./{rel_from_app}")
                    patterns.append(rel_from_app)
        else:
            # Pattern 4: Without leading ./
            if style_path.startswith('./'):
                clean_path = style_path[2:]
                patterns.append(clean_path)
            
            # Pattern 5: Just the filename
            filename = Path(style_path).name
            patterns.append(filename)
            
            # Pattern 6: With leading ./
            if not style_path.startswith('./'):
                patterns.append(f"./{style_path}")
        
        # Remove duplicates while preserving order
        unique_patterns = []
        for pattern in patterns:
            if pattern not in unique_patterns:
                unique_patterns.append(pattern)
                
        return unique_patterns
    
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
            
            # Deduplicate entities by ID before creating queries
            seen_entity_ids = set()
            unique_entities = []
            for result in parse_results:
                for entity in result.entities:
                    if entity.id not in seen_entity_ids:
                        seen_entity_ids.add(entity.id)
                        unique_entities.append(entity)
            
            logger.info(f"Deduplicating entities: {sum(len(r.entities) for r in parse_results)} total -> {len(unique_entities)} unique")
            
            for entity in unique_entities:
                query = self._create_entity_insert_query(entity)
                if query:
                    entity_queries.append(query)
            
            # Process relationships separately to maintain parser access
            for result in parse_results:
                # Get the parser for this file to access normalization
                parser = self._get_parser_for_file(result.file_path)
                
                # Store relationships
                for relationship in result.relationships:
                    # Normalize relationship if parser has the method
                    if parser and hasattr(parser, '_normalize_relationship_metadata'):
                        normalized_rel = ParsedRelationship(
                            from_id=relationship.from_id,
                            to_id=relationship.to_id,
                            relationship_type=relationship.relationship_type,
                            metadata=parser._normalize_relationship_metadata(relationship)
                        )
                        query = self._create_relationship_insert_query(normalized_rel)
                    else:
                        query = self._create_relationship_insert_query(relationship)
                    if query:
                        relationship_queries.append(query)
                    else:
                        logger.debug(f"No query generated for relationship: {relationship.relationship_type} from {relationship.from_id[:8]}... to {relationship.to_id[:8]}...")
            
            # Execute in batches
            batch_size = self.config.database.batch_size
            
            # Insert entities in batches with retry logic
            for i in range(0, len(entity_queries), batch_size):
                batch = entity_queries[i:i + batch_size]
                if not self.db_service.execute_batch(batch):
                    logger.error(f"Failed to insert entity batch {i // batch_size + 1}")
                    # Try individual insertion for failed batch
                    success_count = 0
                    for query in batch:
                        try:
                            if self.db_service.execute_query(query):
                                success_count += 1
                        except Exception as e:
                            logger.debug(f"Individual entity query failed: {e}")
                    logger.info(f"Recovered {success_count}/{len(batch)} entities from failed batch")
            
            # Insert relationships in batches with retry logic
            logger.info(f"Inserting {len(relationship_queries)} relationships in batches")
            for i in range(0, len(relationship_queries), batch_size):
                batch = relationship_queries[i:i + batch_size]
                # Log first query for debugging
                if i == 0 and batch:
                    logger.debug(f"Sample relationship query: {batch[0][:200]}...")
                if not self.db_service.execute_batch(batch):
                    logger.error(f"Failed to insert relationship batch {i // batch_size + 1}")
                    # Try individual insertion for failed batch
                    success_count = 0
                    for query in batch:
                        try:
                            if self.db_service.execute_query(query):
                                success_count += 1
                        except Exception as e:
                            logger.debug(f"Individual relationship query failed: {e}")
                    logger.info(f"Recovered {success_count}/{len(batch)} relationships from failed batch")
            
            logger.info(f"Stored {len(entity_queries)} entities and {len(relationship_queries)} relationships")
            
        except Exception as e:
            logger.error(f"Failed to store results in database: {e}")
    
    def _escape_cypher_string(self, value: str) -> str:
        """
        Escape special characters for Cypher queries.
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string safe for Cypher queries
        """
        if not isinstance(value, str):
            return str(value)
        
        # Escape in order: backslashes first, then quotes, then other special chars
        escaped = (value
                  .replace('\\', '\\\\')  # Escape backslashes first
                  .replace('"', '\\"')    # Escape double quotes
                  .replace("'", "\\'")    # Escape single quotes
                  .replace('\n', '\\n')   # Escape newlines
                  .replace('\r', '\\r')   # Escape carriage returns
                  .replace('\t', '\\t'))  # Escape tabs
        
        return escaped
    
    def _sanitize_external_entity_name(self, name: str, entity_type: str = None) -> str:
        """
        Sanitize external entity names to prevent collisions.
        
        Args:
            name: The entity name to sanitize
            entity_type: Optional entity type for context
            
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

    def _create_entity_insert_query(self, entity: ParsedEntity) -> Optional[str]:
        """
        Create Cypher query to insert entity.
        
        Args:
            entity: Entity to insert
            
        Returns:
            Cypher query string or None
        """
        try:
            # Escape string values using improved escaping
            def escape_string(value):
                if isinstance(value, str):
                    escaped = self._escape_cypher_string(value)
                    return f'"{escaped}"'
                return str(value)
            
            # Sanitize external entity names to prevent collisions
            entity_name = entity.name
            if entity.type in ['ExternalFunction', 'ExternalProperty', 'ExternalModule', 
                               'ExternalExport', 'ExternalSymbol', 'ExternalReference']:
                entity_name = self._sanitize_external_entity_name(entity_name, entity.type)
            
            # Build property list based on entity type
            properties = [
                f'id: {escape_string(entity.id)}',
                f'name: {escape_string(entity_name)}'
            ]
            
            # Add type-specific properties
            if entity.type == 'File':
                properties.append(f'path: {escape_string(entity.file_path)}')
                # Debug logging for File entities
                logger.debug(f"Creating File entity query: id={entity.id}, name={entity_name}, path={entity.file_path}")
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
                logger.debug(f"Skipping unresolved relationship: {relationship.relationship_type} from {relationship.from_id} to {relationship.to_id}")
                return None
            
            # Escape string values using improved escaping
            def escape_string(value):
                if isinstance(value, str):
                    escaped = self._escape_cypher_string(value)
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
            # Format the query on a single line to avoid parsing issues
            from_id_escaped = escape_string(relationship.from_id)
            to_id_escaped = escape_string(relationship.to_id)
            
            if props_str:
                query = f"MATCH (from_node {{id: {from_id_escaped}}}), (to_node {{id: {to_id_escaped}}}) CREATE (from_node)-[:{relationship.relationship_type} {props_str}]->(to_node)"
            else:
                query = f"MATCH (from_node {{id: {from_id_escaped}}}), (to_node {{id: {to_id_escaped}}}) CREATE (from_node)-[:{relationship.relationship_type}]->(to_node)"
            
            return query.strip()
            
        except Exception as e:
            logger.error(f"Failed to create relationship query: {e}")
            return None