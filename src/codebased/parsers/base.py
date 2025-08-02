"""
Base parser infrastructure for CodeBased.
"""

import ast
import os
import hashlib
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Generator, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .file_types import get_file_type

try:
    import tree_sitter
    from tree_sitter import Language, Parser, Node, Tree
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Node = None
    Tree = None

logger = logging.getLogger(__name__)


@dataclass
class ParsedEntity:
    """Represents a parsed code entity."""
    id: str
    name: str
    type: str
    file_path: str
    line_start: int
    line_end: int
    metadata: Dict[str, Any]


@dataclass
class ParsedRelationship:
    """Represents a relationship between parsed entities."""
    from_id: str
    to_id: str
    relationship_type: str
    metadata: Dict[str, Any]


@dataclass
class ParseResult:
    """Result of parsing a file or directory."""
    entities: List[ParsedEntity]
    relationships: List[ParsedRelationship]
    file_hash: str
    file_path: str
    errors: List[str]
    parse_time: float


class BaseParser(ABC):
    """Abstract base class for code parsers."""
    
    SUPPORTED_FILE_TYPES: Set[str] = set()

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize parser with configuration.
        
        Args:
            config: Parser configuration dictionary
        """
        self.config = config or {}
        self.errors: List[str] = []

    def can_parse(self, file_path: str) -> bool:
        """Return True if this parser can handle ``file_path``."""
        file_type = get_file_type(file_path)
        return file_type in self.SUPPORTED_FILE_TYPES
    
    @abstractmethod
    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a single file.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            ParseResult containing entities and relationships
        """
        pass
    
    def parse_directory(self, directory_path: str) -> Generator[ParseResult, None, None]:
        """
        Parse all supported files in a directory.
        
        Args:
            directory_path: Path to directory to parse
            
        Yields:
            ParseResult for each parsed file
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory not found: {directory_path}")
            return
        
        for file_path in self._find_parseable_files(directory_path):
            try:
                result = self.parse_file(str(file_path))
                if result:
                    yield result
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
    
    def _find_parseable_files(self, directory_path: Path) -> Generator[Path, None, None]:
        """
        Find all files that this parser can handle.
        
        Args:
            directory_path: Directory to search
            
        Yields:
            Path objects for parseable files
        """
        exclude_patterns = self.config.get('exclude_patterns', [])
        max_file_size = self.config.get('max_file_size', 1024 * 1024)  # 1MB default
        follow_symlinks = self.config.get('follow_symlinks', False)
        
        for root, dirs, files in os.walk(directory_path, followlinks=follow_symlinks):
            root_path = Path(root)
            
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_exclude(d, exclude_patterns)]
            
            # Process files
            for file_name in files:
                file_path = root_path / file_name
                
                # Skip if excluded
                if self._should_exclude(str(file_path), exclude_patterns):
                    continue
                
                # Skip if too large
                try:
                    if file_path.stat().st_size > max_file_size:
                        logger.debug(f"Skipping large file: {file_path}")
                        continue
                except OSError:
                    continue
                
                # Check if parser can handle this file
                file_type = get_file_type(str(file_path))
                if file_type and file_type in self.SUPPORTED_FILE_TYPES:
                    yield file_path
    
    def _should_exclude(self, path: str, exclude_patterns: List[str]) -> bool:
        """
        Check if path should be excluded based on patterns.
        
        Args:
            path: Path to check
            exclude_patterns: List of exclusion patterns
            
        Returns:
            bool: True if path should be excluded
        """
        import fnmatch
        
        path_obj = Path(path)
        path_name = path_obj.name
        
        # Convert to posix path for consistent pattern matching
        normalized_path = path_obj.as_posix()
        
        for pattern in exclude_patterns:
            # Check filename pattern
            if fnmatch.fnmatch(path_name, pattern):
                return True
            
            # Check full path pattern (handles */dist/*, */build/*, etc.)
            if fnmatch.fnmatch(normalized_path, pattern):
                return True
            
            # Check if any parent directory matches the pattern (for simple directory names)
            for part in path_obj.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        
        return False
    
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
    
    def _generate_entity_id(self, name: str, file_path: str, line_start: int, 
                           entity_type: str = "", line_end: int = None, parent_id: str = "") -> str:
        """
        Generate unique entity ID with enhanced collision resistance.
        
        Args:
            name: Entity name
            file_path: File path
            line_start: Starting line number
            entity_type: Type of entity (Class, Function, etc.)
            line_end: Ending line number (optional)
            parent_id: Parent entity ID for nested entities (optional)
            
        Returns:
            Unique entity ID
        """
        # Normalize file path to handle different path separators
        normalized_path = Path(file_path).as_posix()
        
        # Build identifier with sufficient context to prevent collisions
        identifier_parts = [
            normalized_path,
            entity_type or "unknown",
            name or "anonymous",
            str(line_start)
        ]
        
        # Add line_end if provided for better uniqueness
        if line_end and line_end != line_start:
            identifier_parts.append(str(line_end))
        
        # Add parent context for nested entities
        if parent_id:
            identifier_parts.append(f"parent:{parent_id}")
        
        identifier = ":".join(identifier_parts)
        
        # Use SHA-256 for better collision resistance than MD5
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    
    def _normalize_relationship_metadata(self, relationship: 'ParsedRelationship') -> Dict[str, Any]:
        """
        Normalize relationship metadata to match database schema expectations.
        
        This method should be overridden by parsers to map their metadata
        to the properties expected by the database schema.
        
        Args:
            relationship: Relationship with metadata to normalize
            
        Returns:
            Dictionary with properties that match the schema
        """
        # Default implementation - return empty dict to remove all metadata
        # Subclasses should override this to provide proper mapping
        return {}


class TreeSitterParser(BaseParser):
    """Base class for tree-sitter based parsers."""
    
    TREE_SITTER_LANGUAGE: str = ""  # Override in subclasses
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize tree-sitter parser."""
        super().__init__(config)
        self._language: Optional[Language] = None
        self._parser: Optional[Parser] = None
        
        if not TREE_SITTER_AVAILABLE:
            raise ImportError("tree-sitter not available. Install with: pip install tree-sitter tree_sitter_languages")
        
        self._initialize_parser()
    
    def _initialize_parser(self) -> None:
        """Initialize tree-sitter parser and language."""
        if not self.TREE_SITTER_LANGUAGE:
            raise ValueError(f"{self.__class__.__name__} must define TREE_SITTER_LANGUAGE")
        
        try:
            from .treesitter_setup import ensure_language
            self._language = ensure_language(self.TREE_SITTER_LANGUAGE)
            self._parser = Parser()
            self._parser.set_language(self._language)
            logger.debug(f"Initialized {self.TREE_SITTER_LANGUAGE} parser")
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter parser for {self.TREE_SITTER_LANGUAGE}: {e}")
            raise
    
    def _parse_source_code(self, source_code: str) -> Optional[Tree]:
        """
        Parse source code with tree-sitter.
        
        Args:
            source_code: Source code to parse
            
        Returns:
            Parsed tree or None if parsing failed
        """
        if not self._parser:
            return None
            
        try:
            tree = self._parser.parse(source_code.encode('utf-8'))
            return tree
        except Exception as e:
            logger.error(f"Tree-sitter parsing failed: {e}")
            return None
    
    def _get_node_text(self, node: Node, source_code: str) -> str:
        """
        Extract text content from a tree-sitter node.
        
        Args:
            node: Tree-sitter node
            source_code: Original source code
            
        Returns:
            Text content of the node
        """
        if node is None:
            return ""
        
        try:
            start_byte = node.start_byte
            end_byte = node.end_byte
            return source_code.encode('utf-8')[start_byte:end_byte].decode('utf-8')
        except Exception as e:
            logger.debug(f"Failed to extract node text: {e}")
            return ""
    
    def _get_node_line_info(self, node: Node) -> Tuple[int, int]:
        """
        Get line start and end information for a node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            Tuple of (start_line, end_line) (1-indexed)
        """
        if node is None:
            return (1, 1)
        
        try:
            # Tree-sitter uses 0-indexed lines, convert to 1-indexed
            # Handle both object and tuple return types for compatibility
            start_point = node.start_point
            end_point = node.end_point
            
            if hasattr(start_point, 'row'):
                # Object with row/column attributes
                start_line = start_point.row + 1
                end_line = end_point.row + 1
            else:
                # Tuple format (row, column)
                start_line = start_point[0] + 1
                end_line = end_point[0] + 1
                
            return (start_line, end_line)
        except Exception as e:
            logger.debug(f"Failed to get line info for node: {e}")
            return (1, 1)
    
    def _traverse_tree(self, node: Node, source_code: str, entities: List[ParsedEntity], 
                      relationships: List[ParsedRelationship], file_path: str) -> None:
        """
        Traverse tree-sitter AST and extract entities/relationships.
        
        Args:
            node: Current tree-sitter node
            source_code: Original source code
            entities: List to append entities to
            relationships: List to append relationships to
            file_path: Path to source file
        """
        # This is meant to be overridden by specific language parsers
        # Default implementation just traverses children
        for child in node.children:
            self._traverse_tree(child, source_code, entities, relationships, file_path)
    
    @abstractmethod
    def _extract_entities_from_node(self, node: Node, source_code: str, file_path: str) -> List[ParsedEntity]:
        """
        Extract entities from a specific tree-sitter node.
        Must be implemented by subclasses.
        
        Args:
            node: Tree-sitter node to process
            source_code: Original source code
            file_path: Path to source file
            
        Returns:
            List of extracted entities
        """
        pass
    
    @abstractmethod
    def _extract_relationships_from_node(self, node: Node, source_code: str, 
                                       entities: List[ParsedEntity], file_path: str) -> List[ParsedRelationship]:
        """
        Extract relationships from a specific tree-sitter node.
        Must be implemented by subclasses.
        
        Args:
            node: Tree-sitter node to process
            source_code: Original source code
            entities: Previously extracted entities
            file_path: Path to source file
            
        Returns:
            List of extracted relationships
        """
        pass
    
    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a file using tree-sitter.
        
        Args:
            file_path: Path to file to parse
            
        Returns:
            ParseResult with entities and relationships
        """
        start_time = time.time()
        entities = []
        relationships = []
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            file_hash = self._calculate_file_hash(file_path)
            
            # Parse with tree-sitter
            tree = self._parse_source_code(source_code)
            if tree is None:
                errors.append("Failed to parse with tree-sitter")
                return ParseResult(entities, relationships, file_hash, file_path, errors, time.time() - start_time)
            
            # Extract entities and relationships from AST
            root_node = tree.root_node
            entities = self._extract_entities_from_node(root_node, source_code, file_path)
            relationships = self._extract_relationships_from_node(root_node, source_code, entities, file_path)
            
        except Exception as e:
            error_msg = f"Failed to parse {file_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            file_hash = self._calculate_file_hash(file_path) if os.path.exists(file_path) else ""
        
        parse_time = time.time() - start_time
        return ParseResult(entities, relationships, file_hash, file_path, errors, parse_time)


class FileTraversal:
    """Utility class for traversing and filtering files."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize file traversal with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
    
    def get_python_files(self, root_path: str) -> List[str]:
        """
        Get all Python files in directory tree.
        
        Args:
            root_path: Root directory to search
            
        Returns:
            List of Python file paths
        """
        python_files = []
        root_path = Path(root_path)
        
        file_extensions = self.config.get('file_extensions', ['.py'])
        exclude_patterns = self.config.get('exclude_patterns', [])
        max_file_size = self.config.get('max_file_size', 1024 * 1024)
        follow_symlinks = self.config.get('follow_symlinks', False)
        
        for file_path in root_path.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Check file extension
            if file_path.suffix not in file_extensions:
                continue
            
            # Skip excluded files
            if self._should_exclude(str(file_path), exclude_patterns):
                continue
            
            # Skip large files
            try:
                if file_path.stat().st_size > max_file_size:
                    logger.debug(f"Skipping large file: {file_path}")
                    continue
            except OSError:
                continue
            
            # Skip symbolic links if configured
            if not follow_symlinks and file_path.is_symlink():
                continue
            
            python_files.append(str(file_path))
        
        return sorted(python_files)
    
    def _should_exclude(self, path: str, exclude_patterns: List[str]) -> bool:
        """Check if path matches any exclusion pattern."""
        import fnmatch
        
        path_obj = Path(path)
        
        # Check filename and full path
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_obj.name, pattern):
                return True
            if fnmatch.fnmatch(str(path_obj), pattern):
                return True
            # Check if any parent directory matches pattern
            for parent in path_obj.parents:
                if fnmatch.fnmatch(parent.name, pattern):
                    return True
        
        return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get file metadata information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file metadata
        """
        file_path = Path(file_path)
        
        try:
            stat = file_path.stat()
            
            info = {
                'path': str(file_path),
                'name': file_path.name,
                'stem': file_path.stem,
                'suffix': file_path.suffix,
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'is_symlink': file_path.is_symlink(),
                'exists': file_path.exists(),
                'is_readable': os.access(file_path, os.R_OK)
            }
            
            # Calculate hash if file is readable and not too large
            if info['is_readable'] and info['size'] <= self.config.get('max_file_size', 1024 * 1024):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    info['hash'] = hashlib.sha256(content).hexdigest()
                    
                    # Count lines of code for text files
                    if file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                        try:
                            text_content = content.decode('utf-8', errors='ignore')
                            lines = text_content.split('\n')
                            # Count non-empty, non-comment lines
                            loc = sum(1 for line in lines 
                                     if line.strip() and not line.strip().startswith('#'))
                            info['lines_of_code'] = loc
                            info['total_lines'] = len(lines)
                        except:
                            info['lines_of_code'] = 0
                            info['total_lines'] = 0
                    
                except Exception as e:
                    logger.debug(f"Failed to process file content {file_path}: {e}")
                    info['hash'] = ""
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return {
                'path': str(file_path),
                'name': file_path.name,
                'error': str(e)
            }