"""Utilities for ensuring tree-sitter languages are available."""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache

from tree_sitter import Language

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def ensure_language(lang: str) -> Language:
    """Return a :class:`Language` instance for ``lang``.

    If the language is not available via ``tree_sitter_languages``, this
    function attempts to load a shared library named ``{lang}.so`` placed in
    the same directory as this file.
    """
    try:
        import warnings
        with warnings.catch_warnings():
            # Suppress the FutureWarning from tree_sitter_languages
            warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter_languages")
            ts_langs = importlib.import_module("tree_sitter_languages")
            return ts_langs.get_language(lang)
    except Exception as e:  # pragma: no cover - fallback path
        logger.debug("tree_sitter_languages not usable: %s", e)

    so_path = __name__.replace(".", "/")
    so_path = f"{__file__[:-3]}_{lang}.so"
    try:
        # Handle both old and new Language constructor APIs
        try:
            # Try new API first
            import ctypes
            lib = ctypes.cdll.LoadLibrary(so_path)
            lang_func = getattr(lib, f"tree_sitter_{lang}")
            return Language(lang_func())
        except:
            # Fallback to old API
            return Language(so_path)
    except Exception as e:
        logger.error("Tree-sitter language '%s' not installed: %s", lang, e)
        raise
