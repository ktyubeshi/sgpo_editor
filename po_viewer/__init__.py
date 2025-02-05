"""POファイルビューワー"""
from .core import ViewerPOFile
from .sgpo.core import (
    DiffEntry,
    DiffResult,
    DiffStatus,
    KeyTuple,
    SGPOFile,
    pofile,
    pofile_from_text,
)

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
