"""
Incremental update system for CodeBased using file hashing.
"""

import os
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

from .extractor import EntityExtractor
from .base import ParseResult
from ..database.service import DatabaseService
from ..config import CodeBasedConfig

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """Manages incremental updates of the code graph."""
    
    def __init__(self, config: CodeBasedConfig, db_service: DatabaseService):
        """
        Initialize incremental updater.
        
        Args:
            config: CodeBased configuration
            db_service: Database service instance
        """
        self.config = config
        self.db_service = db_service
        self.extractor = EntityExtractor(config, db_service)
        
        # Hash storage for change detection
        self.file_hashes: Dict[str, str] = {}
        self._load_file_hashes()
    
    def update_graph(self, directory_path: str = None) -> Dict[str, Any]:
        """
        Perform incremental update of the code graph.
        
        Args:
            directory_path: Directory to update (defaults to project root)
            
        Returns:
            Dictionary with update results
        """
        if directory_path is None:
            directory_path = self.config.project_root
        
        logger.info(f"Starting incremental update for {directory_path}")
        start_time = time.time()
        
        results = {
            'total_files': 0,
            'files_added': 0,
            'files_modified': 0,
            'files_removed': 0,
            'files_unchanged': 0,
            'entities_added': 0,
            'entities_updated': 0,
            'entities_removed': 0,
            'relationships_added': 0,
            'relationships_updated': 0,
            'relationships_removed': 0,
            'errors': [],
            'update_time': 0.0
        }
        
        try:
            # Detect changes
            changes = self._detect_changes(directory_path)
            results.update(changes)
            
            # Process changes
            if changes['added'] or changes['modified'] or changes['removed']:
                self._process_changes(changes, results)
            else:
                logger.info("No changes detected - skipping update")
            
            # Update file hashes
            self._save_file_hashes()
            
            results['update_time'] = time.time() - start_time
            logger.info(f"Incremental update completed in {results['update_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def force_full_update(self, directory_path: str = None) -> Dict[str, Any]:
        """
        Force a complete rebuild of the code graph.
        
        Args:
            directory_path: Directory to update (defaults to project root)
            
        Returns:
            Dictionary with update results
        """
        if directory_path is None:
            directory_path = self.config.project_root
        
        logger.info(f"Starting full update for {directory_path}")
        start_time = time.time()
        
        try:
            # Clear existing graph data
            logger.info("Clearing existing graph data...")
            if not self.db_service.clear_graph():
                logger.error("Failed to clear graph data")
                return {'errors': ['Failed to clear graph data'], 'update_time': 0.0}
            
            # Clear file hashes
            self.file_hashes.clear()
            
            # Perform full extraction
            extraction_results = self.extractor.extract_from_directory(directory_path)
            
            # Update file hashes from extraction results
            for result in extraction_results['parse_results']:
                if result.file_hash:
                    self.file_hashes[result.file_path] = result.file_hash
            
            # Save updated hashes
            self._save_file_hashes()
            
            # Transform extraction results to update results format
            results = {
                'total_files': extraction_results['files_processed'] + extraction_results['files_failed'],
                'files_added': extraction_results['files_processed'],
                'files_modified': 0,
                'files_removed': 0,
                'files_unchanged': 0,
                'entities_added': extraction_results['entities_extracted'],
                'entities_updated': 0,
                'entities_removed': 0,
                'relationships_added': extraction_results['relationships_extracted'],
                'relationships_updated': 0,
                'relationships_removed': 0,
                'errors': extraction_results['errors'],
                'update_time': time.time() - start_time
            }
            
            logger.info(f"Full update completed in {results['update_time']:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Full update failed: {e}")
            return {
                'errors': [str(e)],
                'update_time': time.time() - start_time
            }
    
    def _detect_changes(self, directory_path: str) -> Dict[str, Any]:
        """
        Detect file changes since last update.
        
        Args:
            directory_path: Directory to scan for changes
            
        Returns:
            Dictionary with change information
        """
        logger.info("Detecting file changes...")
        
        changes = {
            'added': [],
            'modified': [],
            'removed': [],
            'unchanged': [],
            'total_files': 0
        }
        
        directory_path = Path(directory_path)
        current_files = set()
        
        # Find all current parseable files
        for parser in self.extractor.parsers.values():
            for file_path in parser._find_parseable_files(directory_path):
                file_path_str = str(file_path)
                current_files.add(file_path_str)
                
                # Calculate current file hash
                current_hash = self._calculate_file_hash(file_path_str)
                
                if file_path_str not in self.file_hashes:
                    # New file
                    changes['added'].append(file_path_str)
                elif self.file_hashes[file_path_str] != current_hash:
                    # Modified file
                    changes['modified'].append(file_path_str)
                else:
                    # Unchanged file
                    changes['unchanged'].append(file_path_str)
        
        # Find removed files
        for stored_file in self.file_hashes:
            if stored_file not in current_files:
                changes['removed'].append(stored_file)
        
        changes['total_files'] = len(current_files)
        
        logger.info(f"Change detection completed: "
                   f"{len(changes['added'])} added, "
                   f"{len(changes['modified'])} modified, "
                   f"{len(changes['removed'])} removed, "
                   f"{len(changes['unchanged'])} unchanged")
        
        return changes
    
    def _process_changes(self, changes: Dict[str, Any], results: Dict[str, Any]) -> None:
        """
        Process detected changes and update the graph.
        
        Args:
            changes: Change information from detection
            results: Results dictionary to update
        """
        # Remove entities from removed files
        if changes['removed']:
            logger.info(f"Processing {len(changes['removed'])} removed files...")
            self._remove_files_from_graph(changes['removed'], results)
        
        # Process added and modified files
        files_to_parse = changes['added'] + changes['modified']
        if files_to_parse:
            logger.info(f"Processing {len(files_to_parse)} added/modified files...")
            
            # Remove old entities from modified files
            if changes['modified']:
                self._remove_files_from_graph(changes['modified'], results)
            
            # Parse and add new entities
            parse_results = []
            for file_path in files_to_parse:
                parser = self.extractor._get_parser_for_file(file_path)
                if parser:
                    try:
                        result = parser.parse_file(file_path)
                        parse_results.append(result)
                        
                        # Update file hash
                        if result.file_hash:
                            self.file_hashes[file_path] = result.file_hash
                            
                    except Exception as e:
                        logger.error(f"Failed to parse {file_path}: {e}")
                        results['errors'].append(f"Parse error in {file_path}: {e}")
            
            # Resolve relationships using two-pass system
            if parse_results:
                resolved_results = self.extractor._resolve_relationships(parse_results)
                self.extractor._store_results(resolved_results)
                
                # Update statistics
                for result in resolved_results:
                    if result.file_path in changes['added']:
                        results['entities_added'] += len(result.entities)
                        results['relationships_added'] += len(result.relationships)
                    else:  # Modified
                        results['entities_updated'] += len(result.entities)
                        results['relationships_updated'] += len(result.relationships)
        
        # Update counts
        results['files_added'] = len(changes['added'])
        results['files_modified'] = len(changes['modified'])
        results['files_removed'] = len(changes['removed'])
        results['files_unchanged'] = len(changes['unchanged'])
        results['total_files'] = changes['total_files']
    
    def _remove_files_from_graph(self, file_paths: List[str], results: Dict[str, Any]) -> None:
        """
        Remove entities and relationships for given files from the graph.
        
        Args:
            file_paths: List of file paths to remove
            results: Results dictionary to update
        """
        for file_path in file_paths:
            try:
                # Get entities to remove
                entities_query = f"""
                MATCH (n {{file_path: "{file_path}"}})
                RETURN n.id AS id, 'Entity' AS type
                """
                
                entities_result = self.db_service.execute_query(entities_query)
                if entities_result:
                    entity_ids = [entity['id'] for entity in entities_result]
                    
                    # Remove relationships first
                    if entity_ids:
                        for entity_id in entity_ids:
                            rel_query = f"""
                            MATCH (n {{id: "{entity_id}"}})-[r]-()
                            DELETE r
                            """
                            self.db_service.execute_query(rel_query)
                            results['relationships_removed'] += 1
                    
                    # Remove entities
                    for entity_id in entity_ids:
                        entity_query = f"""
                        MATCH (n {{id: "{entity_id}"}})
                        DELETE n
                        """
                        self.db_service.execute_query(entity_query)
                        results['entities_removed'] += 1
                
                # Remove from file hashes
                if file_path in self.file_hashes:
                    del self.file_hashes[file_path]
                
            except Exception as e:
                logger.error(f"Failed to remove {file_path} from graph: {e}")
                results['errors'].append(f"Removal error for {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hexadecimal hash string
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _load_file_hashes(self) -> None:
        """Load file hashes from database."""
        try:
            query = "MATCH (f:File) RETURN f.path AS path, f.hash AS hash"
            result = self.db_service.execute_query(query)
            
            if result:
                # Handle both dictionary and list-like result formats
                self.file_hashes = {}
                for row in result:
                    if isinstance(row, dict):
                        path = row.get('path')
                        hash_val = row.get('hash')
                    else:
                        # Assume list-like access [path, hash]
                        try:
                            path = row[0] if len(row) > 0 else None
                            hash_val = row[1] if len(row) > 1 else None
                        except (IndexError, TypeError):
                            continue
                    
                    if path and hash_val:
                        self.file_hashes[path] = hash_val
                        
                logger.debug(f"Loaded {len(self.file_hashes)} file hashes from database")
            else:
                logger.debug("No file hashes found in database")
                
        except Exception as e:
            logger.error(f"Failed to load file hashes: {e}")
            self.file_hashes = {}
    
    def _save_file_hashes(self) -> None:
        """Save file hashes to database."""
        try:
            # File entities should already be created with hashes
            # This is mainly for backup/verification
            logger.debug(f"File hashes tracked for {len(self.file_hashes)} files")
            
        except Exception as e:
            logger.error(f"Failed to save file hashes: {e}")
    
    def get_update_status(self) -> Dict[str, Any]:
        """
        Get current update status and statistics.
        
        Returns:
            Dictionary with status information
        """
        try:
            stats = self.db_service.get_stats()
            
            status = {
                'last_update': None,  # TODO: Store timestamp in database
                'tracked_files': len(self.file_hashes),
                'database_stats': stats,
                'health': self.db_service.health_check()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get update status: {e}")
            return {
                'error': str(e),
                'tracked_files': len(self.file_hashes)
            }
    
    def cleanup_orphaned_entities(self) -> Dict[str, int]:
        """
        Remove entities that reference non-existent files.
        
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Starting cleanup of orphaned entities...")
        cleanup_stats = {'entities_removed': 0, 'relationships_removed': 0}
        
        try:
            # Find entities with file paths that no longer exist
            query = """
            MATCH (n)
            WHERE exists(n.file_path) AND n.file_path IS NOT NULL
            RETURN DISTINCT n.file_path AS file_path
            """
            
            result = self.db_service.execute_query(query)
            if result:
                existing_files = set()
                for parser in self.extractor.parsers.values():
                    directory_path = Path(self.config.project_root)
                    for file_path in parser._find_parseable_files(directory_path):
                        existing_files.add(str(file_path))
                
                orphaned_files = []
                for row in result:
                    file_path = row['file_path']
                    if file_path not in existing_files and not Path(file_path).exists():
                        orphaned_files.append(file_path)
                
                # Remove orphaned entities
                if orphaned_files:
                    logger.info(f"Found {len(orphaned_files)} orphaned files")
                    for file_path in orphaned_files:
                        # Remove entities and relationships for this file
                        remove_query = f"""
                        MATCH (n {{file_path: "{file_path}"}})
                        DETACH DELETE n
                        """
                        
                        entities_before = self.db_service.get_stats()['nodes']
                        self.db_service.execute_query(remove_query)
                        entities_after = self.db_service.get_stats()['nodes']
                        
                        cleanup_stats['entities_removed'] += entities_before - entities_after
                        
                        # Remove from file hashes
                        if file_path in self.file_hashes:
                            del self.file_hashes[file_path]
                
                logger.info(f"Cleanup completed: removed {cleanup_stats['entities_removed']} orphaned entities")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            cleanup_stats['error'] = str(e)
        
        return cleanup_stats