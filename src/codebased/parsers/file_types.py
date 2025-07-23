"""
File type detection for CodeBased.
"""

from pathlib import Path
from typing import Dict, Optional

# Mapping of file extensions to file types
# This can be extended to support more languages
FILE_TYPE_MAPPINGS: Dict[str, str] = {
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    # JavaScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    # TypeScript
    ".ts": "typescript",
    ".tsx": "typescript",
    # HTML
    ".html": "html",
    ".htm": "html",
    # CSS
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    # Angular
    ".ts": "angular",
    ".html": "angular",
    # Node.js
    ".js": "nodejs",
    # JSON
    ".json": "json",
    # YAML
    ".yml": "yaml",
    ".yaml": "yaml",
    # Markdown
    ".md": "markdown",
    # Docker
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
    extension = path.suffix

    # Handle files with no extension like 'Dockerfile'
    if not extension and path.name in FILE_TYPE_MAPPINGS:
        return FILE_TYPE_MAPPINGS[path.name]

    if extension in FILE_TYPE_MAPPINGS:
        return FILE_TYPE_MAPPINGS[extension]

    return None
