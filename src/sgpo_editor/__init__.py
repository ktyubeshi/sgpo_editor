"""POファイルビューワー"""

from sgpo.core import (DiffEntry, DiffResult, DiffStatus, KeyTuple, SGPOFile,
                       pofile, pofile_from_text)
from sgpo_editor.core import ViewerPOFile

SgPo = SGPOFile  # Alias for backward compatibility

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffStatus",
    "KeyTuple",
    "SGPOFile",
    "SgPo",
    "ViewerPOFile",
    "pofile",
    "pofile_from_text",
]
