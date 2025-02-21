import polib
from .core import (
    DiffEntry,
    DiffResult,
    DiffStatus,
    KeyTuple,
    SGPOFile,
    pofile,
    pofile_from_text,
)

SgPo = SGPOFile  # Alias for backward compatibility
POEntry = polib.POEntry  # Re-export POEntry from polib

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffStatus",
    "KeyTuple",
    "SGPOFile",
    "SgPo",
    "POEntry",
    "pofile",
    "pofile_from_text",
]
