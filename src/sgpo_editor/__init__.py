"""POファイルビューワー"""

from sgpo.core import (
    DiffEntry,
    DiffResult,
    DiffStatus,
    KeyTuple,
    SGPOFile,
    pofile,
    pofile_from_text,
)
from sgpo_editor.core.viewer_po_file_refactored import (
    ViewerPOFileRefactored as ViewerPOFile,
)
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor

SgPo = SGPOFile  # Alias for backward compatibility

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffStatus",
    "KeyTuple",
    "SGPOFile",
    "SgPo",
    "ViewerPOFile",
    "EntryCacheManager",
    "DatabaseAccessor",
    "pofile",
    "pofile_from_text",
]
