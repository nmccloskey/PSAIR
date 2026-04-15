"""
Core manual-building and validation utilities for PSAIR.
"""

from .index import (
    ManualFile,
    TreeNode,
    build_manual_index,
    extract_md_title,
    numeric_sort_key,
    read_text_safely,
    render_generated_tree_text,
    search_manual,
)
from .outline import (
    build_manual_outline,
    ensure_manual_outline,
)
from .chars import (
    Finding,
    CharScanResult,
    check_manual_chars,
)
from .pdf import (
    build_manual_pdf,
)

__all__ = [
    "ManualFile",
    "TreeNode",
    "Finding",
    "CharScanResult",
    "build_manual_index",
    "extract_md_title",
    "numeric_sort_key",
    "read_text_safely",
    "render_generated_tree_text",
    "search_manual",
    "build_manual_outline",
    "ensure_manual_outline",
    "check_manual_chars",
    "build_manual_pdf",
]