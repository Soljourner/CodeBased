"""
Base parser infrastructure for CodeBased.
"""

import ast
import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Generator, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .file_types import get_file_type

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
        
        path_name = Path(path).name
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_name, pattern) or fnmatch.fnmatch(path, pattern):
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
    
    def _generate_entity_id(self, name: str, file_path: str, line_start: int) -> str:
        """
        Generate unique entity ID.
        
        Args:
            name: Entity name
            file_path: File path
            line_start: Starting line number
            
        Returns:
            Unique entity ID
        """
        identifier = f"{file_path}:{name}:{line_start}"
        return hashlib.md5(identifier.encode()).hexdigest()


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