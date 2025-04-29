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
from sgpo_editor.core import ViewerPOFile, ViewerPOFileRefactored
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
    "ViewerPOFileRefactored",  # 後方互換性のため維持
    "DatabaseAccessor",
    "pofile",
    "pofile_from_text",
]
