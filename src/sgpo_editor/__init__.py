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

SgPo = SGPOFile  # Alias for backward compatibility

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffStatus",
    "KeyTuple",
    "SGPOFile",
    "SgPo",
    "ViewerPOFile",
    "ViewerPOFileRefactored",
    "pofile",
    "pofile_from_text",
]
