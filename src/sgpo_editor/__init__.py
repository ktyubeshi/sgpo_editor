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
from sgpo_editor.core import ViewerPOFile
from sgpo_editor.core.database_accessor import DatabaseAccessor

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffStatus",
    "KeyTuple",
    "SGPOFile",
    "ViewerPOFile",
    "DatabaseAccessor",
    "pofile",
    "pofile_from_text",
]
# ViewerPOFileRefactored は sgpo_editor.core にエイリアスとして定義されています
