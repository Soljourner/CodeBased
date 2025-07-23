"""
Parser registry for CodeBased.
"""

from typing import Dict, Type
from .base import BaseParser
from .python import PythonASTParser
from .javascript import JavaScriptParser
from .html import HTMLParser
from .css import CSSParser
from .typescript import TypeScriptParser
from .angular import AngularParser
from .nodejs import NodeJSParser

# Parser registry mapping file types to parser classes
PARSER_REGISTRY: Dict[str, Type[BaseParser]] = {
    "python": PythonASTParser,
    "javascript": JavaScriptParser,
    "html": HTMLParser,
    "css": CSSParser,
    "typescript": TypeScriptParser,
    "angular": AngularParser,
    "nodejs": NodeJSParser,
}


def get_parser(file_type: str) -> Type[BaseParser] | None:
    """
    Get the parser class for a given file type.

    Args:
        file_type: The file type to get the parser for.

    Returns:
        The parser class, or None if no parser is found.
    """
    return PARSER_REGISTRY.get(file_type)
