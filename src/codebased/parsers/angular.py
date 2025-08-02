"""
Angular parser for CodeBased.
"""

import time
import logging
from typing import List, Dict, Any

from .base import BaseParser, ParsedEntity, ParsedRelationship, ParseResult

logger = logging.getLogger(__name__)


class AngularParser(BaseParser):
    """Basic Angular parser."""

    SUPPORTED_FILE_TYPES = {"angular"}

    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse an Angular file.

        This delegates to the TypeScript parser since all Angular parsing
        logic is implemented there.

        Args:
            file_path: Path to Angular file

        Returns:
            ParseResult with entities and relationships
        """
        # Import here to avoid circular imports
        from .typescript import TypeScriptParser
        
        # Create TypeScript parser instance and delegate
        ts_parser = TypeScriptParser(self.config)
        return ts_parser.parse_file(file_path)
