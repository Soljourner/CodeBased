"""
File type detection for CodeBased.
"""

from pathlib import Path
from typing import Dict, Optional

# Mapping of file extensions to file types
# This can be extended to support more languages
# Patterns for more specific detection (checked before extension mapping)
FILE_TYPE_PATTERNS: Dict[str, str] = {
    # Angular component / module / service files
    ".component.ts": "angular",
    ".module.ts": "angular",
    ".service.ts": "angular",
    ".guard.ts": "angular",
    ".pipe.ts": "angular",
    ".component.html": "angular",
    ".component.css": "angular",
}

# Basic extension mapping
FILE_TYPE_MAPPINGS: Dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    "Dockerfile": "dockerfile",
}


def get_file_type(file_path: str) -> Optional[str]:
    """
    Detect the file type of a file based on its extension.

    Args:
        file_path: The path to the file.

    Returns:
        The file type as a string, or None if the file type is not supported.
    """
    path = Path(file_path)
    name_lower = path.name.lower()

    # Check specific patterns first
    for pattern, ftype in FILE_TYPE_PATTERNS.items():
        if name_lower.endswith(pattern):
            return ftype

    extension = path.suffix.lower()

    # Handle files with no extension like 'Dockerfile'
    if not extension and path.name in FILE_TYPE_MAPPINGS:
        return FILE_TYPE_MAPPINGS[path.name]

    if extension in FILE_TYPE_MAPPINGS:
        return FILE_TYPE_MAPPINGS[extension]

    return None
