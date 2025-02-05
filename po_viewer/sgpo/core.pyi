from __future__ import annotations

from enum import Enum
from os import PathLike
from typing import Any, Dict, List, Optional, Union

from polib import POEntry, POFile
from pydantic import BaseModel

from .duplicate_checker import DuplicateEntry


class DiffStatus(str, Enum):
    """差分の状態を表すEnum"""
    NEW = "new"
    REMOVED = "removed"
    MODIFIED = "modified"


class KeyTuple(BaseModel):
    """POファイルのエントリを一意に識別するためのキー"""
    msgctxt: str
    msgid: str


class DiffEntry(BaseModel):
    """POファイルのエントリの差分情報"""
    key: KeyTuple
    status: DiffStatus
    old_value: Optional[str]
    new_value: Optional[str]


class DiffResult(BaseModel):
    """POファイル間の差分結果"""
    new_entries: list[DiffEntry]
    removed_entries: list[DiffEntry]
    modified_entries: list[DiffEntry]
    def __bool__(self) -> bool: ...


class SGPOFile(POFile):
    """SmartGit用のPOファイル操作クラス"""
    META_DATA_BASE_DICT: Dict[str, str]

    def __init__(self) -> None: ...

    @classmethod
    def from_file(cls, filename: str) -> SGPOFile: ...

    @classmethod
    def from_text(cls, text: str) -> SGPOFile: ...

    @classmethod
    def _create_instance(cls, source: Union[str, PathLike[str]]) -> SGPOFile: ...

    def import_unknown(self, unknown: SGPOFile) -> None: ...

    def import_mismatch(self, mismatch: SGPOFile) -> None: ...

    def import_pot(self, pot: SGPOFile) -> None: ...

    def delete_extracted_comments(self) -> None: ...

    def find_by_key(self, msgctxt: str, msgid: str) -> Optional[POEntry]: ...

    def sort(
        self,
        *,
        key: Optional[Any] = None,
        reverse: bool = False,
    ) -> None: ...

    def format(self) -> None: ...

    def save(
        self,
        fpath: Optional[str] = None,
        repr_method: str = "__unicode__",
        newline: Optional[str] = "\n",
    ) -> None: ...

    def get_key_list(self) -> list[KeyTuple]: ...

    def check_duplicates(self) -> List[DuplicateEntry]: ...

    def diff(self, other: SGPOFile) -> DiffResult: ...

    @staticmethod
    def _filter_po_metadata(meta_dict: Dict[str, str]) -> Dict[str, str]: ...

    def _po_entry_to_sort_key(self, po_entry: POEntry) -> str: ...

    @staticmethod
    def _po_entry_to_legacy_key(po_entry: POEntry) -> str: ...

    @staticmethod
    def _po_entry_to_key_tuple(po_entry: POEntry) -> KeyTuple: ...

    @staticmethod
    def _multi_keys_filter(text: str) -> str: ...

    @staticmethod
    def _validate_filename(filename: str) -> bool: ...


def pofile(filename: str) -> SGPOFile: ...
def pofile_from_text(text: str) -> SGPOFile: ...

# ignore linter errors
# These errors are ignored using noqa because they don't conform to formatter behavior.
# E301 - blank-line-between-methods (E301)
# E302 - blank-lines-top-level (E302)
