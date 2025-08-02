"""
HTML parser for CodeBased with Angular template support.
"""

import time
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any

from .base import BaseParser, ParsedEntity, ParsedRelationship, ParseResult

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    """HTML parser with Angular template support."""

    SUPPORTED_FILE_TYPES = {"html", "htm", "angular_template"}

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse an HTML file and extract Angular template features.

        Args:
            file_path: Path to HTML file

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
            file_entity = self._create_html_file_entity(file_path, content)
            entities.append(file_entity)

            # Extract Angular template features
            self._extract_angular_features(file_entity, content, relationships)

        except Exception as e:
            error_msg = f"Failed to parse {file_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            file_hash = ""

        parse_time = time.time() - start_time
        return ParseResult(entities, relationships, file_hash, file_path, errors, parse_time)

    def _create_html_file_entity(self, file_path: str, content: str) -> ParsedEntity:
        """Create a File entity for an HTML file with enhanced metadata."""
        lines = content.splitlines()
        file_stats = os.stat(file_path)
        path_obj = Path(file_path)
        
        # Detect if this is an Angular template
        is_angular_template = self._detect_angular_template(content)
        
        metadata = {
            'full_path': file_path,
            'extension': path_obj.suffix,
            'size': file_stats.st_size,
            'lines_of_code': len(lines),
            'language': 'html',
            'framework': 'angular' if is_angular_template else None,
            'is_template': True,
            'template_type': 'angular' if is_angular_template else 'html'
        }
        
        # Add Angular-specific metadata
        if is_angular_template:
            metadata.update(self._extract_angular_metadata(content))

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

    def _detect_angular_template(self, content: str) -> bool:
        """Detect if HTML content contains Angular template syntax."""
        angular_patterns = [
            r'\*ng[A-Z][a-zA-Z]*',  # *ngIf, *ngFor, etc.
            r'\[.*?\]',             # Property binding [property]
            r'\(.*?\)',             # Event binding (event)
            r'\{\{.*?\}\}',         # Interpolation {{value}}
            r'#[a-zA-Z][a-zA-Z0-9]*',  # Template reference variables #var
            r'mat-[a-z-]+',         # Angular Material components
            r'app-[a-z-]+',         # Custom Angular components
        ]
        
        for pattern in angular_patterns:
            if re.search(pattern, content):
                return True
        return False

    def _extract_angular_metadata(self, content: str) -> Dict[str, Any]:
        """Extract Angular-specific metadata from template content."""
        metadata = {}
        
        # Count Angular directives
        directives = set()
        for match in re.finditer(r'\*ng[A-Z][a-zA-Z]*', content):
            directives.add(match.group())
        metadata['angular_directives'] = list(directives)
        
        # Count property bindings
        property_bindings = len(re.findall(r'\[.*?\]', content))
        metadata['property_bindings'] = property_bindings
        
        # Count event bindings
        event_bindings = len(re.findall(r'\(.*?\)', content))
        metadata['event_bindings'] = event_bindings
        
        # Count interpolations
        interpolations = len(re.findall(r'\{\{.*?\}\}', content))
        metadata['interpolations'] = interpolations
        
        # Extract custom component usage
        custom_components = set()
        for match in re.finditer(r'<(app-[a-z-]+)', content):
            custom_components.add(match.group(1))
        metadata['custom_components'] = list(custom_components)
        
        # Extract material components
        material_components = set()
        for match in re.finditer(r'<(mat-[a-z-]+)', content):
            material_components.add(match.group(1))
        metadata['material_components'] = list(material_components)
        
        return metadata

    def _extract_angular_features(self, file_entity: ParsedEntity, content: str, 
                                relationships: List[ParsedRelationship]) -> None:
        """Extract Angular template features and create relationships."""
        
        # Extract custom component dependencies
        custom_components = re.findall(r'<(app-[a-z-]+)', content)
        for component_tag in set(custom_components):
            # Create relationship to potential component
            relationships.append(ParsedRelationship(
                from_id=file_entity.id,
                to_id=f"unresolved:angular_component_{component_tag}",
                relationship_type="USES_COMPONENT",
                metadata={
                    'component_tag': component_tag,
                    'usage_type': 'template_reference'
                }
            ))
        
        # Note: Additional relationships like template variable usage,
        # event handler connections, etc. could be added here
