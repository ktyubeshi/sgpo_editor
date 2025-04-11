"""sgpoのアダプタークラス

このモジュールは、sgpoライブラリを使用するためのアダプタークラスを提供します。
"""

import sgpo
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Iterator, Protocol

from sgpo_editor.core.po_interface import POEntry, POFile, POFileFactory


class SGPOEntryProtocol(Protocol):
    """sgpoのPOEntryオブジェクトのプロトコル"""
    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    flags: List[str]
    obsolete: bool
    occurrences: List[tuple]
    msgid_plural: Optional[str]
    msgstr_plural: Dict[int, str]
    comment: Optional[str]
    tcomment: Optional[str]


class SgpoEntry(POEntry):
    """sgpoのPOEntryアダプター"""

    def __init__(self, entry: Any):  # type: ignore
        """初期化

        Args:
            entry: sgpoのPOEntryオブジェクト
        """
        self._entry = entry

    @property
    def msgid(self) -> str:
        """メッセージID"""
        return self._entry.msgid

    @msgid.setter
    def msgid(self, value: str) -> None:
        """メッセージIDを設定"""
        self._entry.msgid = value

    @property
    def msgstr(self) -> str:
        """翻訳文"""
        return self._entry.msgstr

    @msgstr.setter
    def msgstr(self, value: str) -> None:
        """翻訳文を設定"""
        self._entry.msgstr = value

    @property
    def msgctxt(self) -> Optional[str]:
        """メッセージコンテキスト"""
        return getattr(self._entry, "msgctxt", None)

    @msgctxt.setter
    def msgctxt(self, value: Optional[str]) -> None:
        """メッセージコンテキストを設定"""
        self._entry.msgctxt = value

    @property
    def flags(self) -> List[str]:
        """フラグリスト"""
        return self._entry.flags

    @flags.setter
    def flags(self, value: List[str]) -> None:
        """フラグリストを設定"""
        self._entry.flags = value

    @property
    def obsolete(self) -> bool:
        """廃止フラグ"""
        return self._entry.obsolete

    @obsolete.setter
    def obsolete(self, value: bool) -> None:
        """廃止フラグを設定"""
        self._entry.obsolete = value

    @property
    def comment(self) -> Optional[str]:
        """コメント"""
        return getattr(self._entry, "comment", None)

    @comment.setter
    def comment(self, value: Optional[str]) -> None:
        """コメントを設定"""
        self._entry.comment = value

    @property
    def tcomment(self) -> Optional[str]:
        """翻訳者コメント"""
        return getattr(self._entry, "tcomment", None)

    @tcomment.setter
    def tcomment(self, value: Optional[str]) -> None:
        """翻訳者コメントを設定"""
        self._entry.tcomment = value

    @property
    def occurrences(self) -> List[tuple]:
        """出現位置"""
        return self._entry.occurrences

    @occurrences.setter
    def occurrences(self, value: List[tuple]) -> None:
        """出現位置を設定"""
        self._entry.occurrences = value

    @property
    def fuzzy(self) -> bool:
        """ファジーフラグ"""
        return "fuzzy" in self._entry.flags

    @fuzzy.setter
    def fuzzy(self, value: bool) -> None:
        """ファジーフラグを設定"""
        if value and "fuzzy" not in self._entry.flags:
            self._entry.flags.append("fuzzy")
        elif not value and "fuzzy" in self._entry.flags:
            self._entry.flags.remove("fuzzy")

    @property
    def msgid_plural(self) -> Optional[str]:
        """複数形のメッセージID"""
        return getattr(self._entry, "msgid_plural", None)

    @msgid_plural.setter
    def msgid_plural(self, value: Optional[str]) -> None:
        """複数形のメッセージIDを設定"""
        self._entry.msgid_plural = value

    @property
    def msgstr_plural(self) -> Dict[int, str]:
        """複数形の翻訳文"""
        return getattr(self._entry, "msgstr_plural", {})

    @msgstr_plural.setter
    def msgstr_plural(self, value: Dict[int, str]) -> None:
        """複数形の翻訳文を設定"""
        self._entry.msgstr_plural = value

    def get_native_entry(self) -> SGPOEntryProtocol:
        """ネイティブのPOEntryオブジェクトを取得"""
        return self._entry


class SgpoFile(POFile):
    """sgpoのPOFileアダプター"""

    def __init__(self, pofile: sgpo.SGPOFile):
        """初期化

        Args:
            pofile: sgpoのPOFileオブジェクト
        """
        self._pofile = pofile

    @property
    def metadata(self) -> Dict[str, str]:
        """メタデータ"""
        return self._pofile.metadata

    @metadata.setter
    def metadata(self, value: Dict[str, str]) -> None:
        """メタデータを設定"""
        self._pofile.metadata = value

    def append(self, entry: POEntry) -> None:
        """エントリを追加"""
        if isinstance(entry, SgpoEntry):
            native_entry = entry.get_native_entry()  # type: ignore
            self._pofile.append(native_entry)  # type: ignore
        else:
            # 他の実装からのエントリを変換する必要がある場合
            # ここで変換処理を行う
            raise TypeError("SgpoEntryオブジェクトが必要です")

    def save(self, fpath: Optional[str] = None) -> None:
        """POファイルを保存

        注意: SGPOFileのsaveメソッドを呼び出す前にformat()メソッドが呼ばれないようにします。
        format()メソッドはメタデータを上書きしてしまうため、直接saveメソッドを呼び出します。
        """
        self._pofile.save(fpath=fpath)

    def find(
        self, st: str, by: str = "msgid", include_obsolete_entries: bool = False
    ) -> Optional[POEntry]:
        """エントリを検索"""
        entry = self._pofile.find(
            st, by=by, include_obsolete_entries=include_obsolete_entries
        )
        if entry:
            return SgpoEntry(entry)
        return None

    def translated_entries(self) -> List[POEntry]:
        """翻訳済みエントリを取得"""
        return [SgpoEntry(entry) for entry in self._pofile.translated_entries()]

    def untranslated_entries(self) -> List[POEntry]:
        """未翻訳エントリを取得"""
        return [SgpoEntry(entry) for entry in self._pofile.untranslated_entries()]

    def fuzzy_entries(self) -> List[POEntry]:
        """ファジーエントリを取得"""
        return [SgpoEntry(entry) for entry in self._pofile.fuzzy_entries()]

    def obsolete_entries(self) -> List[POEntry]:
        """廃止済みエントリを取得"""
        return [SgpoEntry(entry) for entry in self._pofile.obsolete_entries()]

    def __len__(self) -> int:
        """エントリ数を取得"""
        return len(self._pofile)

    def __iter__(self) -> Iterator[SgpoEntry]:
        """イテレータ"""
        for entry in self._pofile:
            yield SgpoEntry(entry)

    def get_native_file(self) -> sgpo.SGPOFile:
        """ネイティブのPOFileオブジェクトを取得"""
        return self._pofile


class SgpoFactory(POFileFactory):
    """sgpoのPOFileファクトリ"""

    def create_entry(self, **kwargs) -> POEntry:
        """POエントリを作成"""
        # sgpoはPOEntryを直接作成する方法を提供していないため、
        # polibのPOEntryを作成してから変換する
        import polib

        entry = polib.POEntry(**kwargs)
        return SgpoEntry(entry)

    def create_file(self) -> POFile:
        """POファイルを作成"""
        pofile = sgpo.SGPOFile()
        # SGPOFileのデフォルトメタデータを使用
        return SgpoFile(pofile)

    def load_file(self, file_path: Union[str, Path]) -> POFile:
        """POファイルを読み込む"""
        file_path_str = str(file_path)
        pofile = sgpo.pofile(file_path_str)
        return SgpoFile(pofile)
