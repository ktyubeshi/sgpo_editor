"""POファイル操作のための抽象インターフェース

このモジュールは、POファイル操作のための抽象クラスを提供します。
sgpoとpolibの両方に対応できるようにするためのインターフェースです。
"""

import abc
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union


class POEntry(abc.ABC):
    """POエントリの抽象クラス"""

    @property
    @abc.abstractmethod
    def msgid(self) -> str:
        """メッセージID"""
        pass

    @msgid.setter
    @abc.abstractmethod
    def msgid(self, value: str) -> None:
        """メッセージIDを設定"""
        pass

    @property
    @abc.abstractmethod
    def msgstr(self) -> str:
        """翻訳文"""
        pass

    @msgstr.setter
    @abc.abstractmethod
    def msgstr(self, value: str) -> None:
        """翻訳文を設定"""
        pass

    @property
    @abc.abstractmethod
    def msgctxt(self) -> Optional[str]:
        """メッセージコンテキスト"""
        pass

    @msgctxt.setter
    @abc.abstractmethod
    def msgctxt(self, value: Optional[str]) -> None:
        """メッセージコンテキストを設定"""
        pass

    @property
    @abc.abstractmethod
    def flags(self) -> List[str]:
        """フラグリスト"""
        pass

    @flags.setter
    @abc.abstractmethod
    def flags(self, value: List[str]) -> None:
        """フラグリストを設定"""
        pass

    @property
    @abc.abstractmethod
    def obsolete(self) -> bool:
        """廃止フラグ"""
        pass

    @obsolete.setter
    @abc.abstractmethod
    def obsolete(self, value: bool) -> None:
        """廃止フラグを設定"""
        pass

    @property
    @abc.abstractmethod
    def comment(self) -> Optional[str]:
        """コメント"""
        pass

    @comment.setter
    @abc.abstractmethod
    def comment(self, value: Optional[str]) -> None:
        """コメントを設定"""
        pass

    @property
    @abc.abstractmethod
    def tcomment(self) -> Optional[str]:
        """翻訳者コメント"""
        pass

    @tcomment.setter
    @abc.abstractmethod
    def tcomment(self, value: Optional[str]) -> None:
        """翻訳者コメントを設定"""
        pass

    @property
    @abc.abstractmethod
    def occurrences(self) -> List[tuple]:
        """出現位置"""
        pass

    @occurrences.setter
    @abc.abstractmethod
    def occurrences(self, value: List[tuple]) -> None:
        """出現位置を設定"""
        pass

    @property
    @abc.abstractmethod
    def fuzzy(self) -> bool:
        """ファジーフラグ"""
        pass

    @fuzzy.setter
    @abc.abstractmethod
    def fuzzy(self, value: bool) -> None:
        """ファジーフラグを設定"""
        pass

    @property
    @abc.abstractmethod
    def msgid_plural(self) -> Optional[str]:
        """複数形のメッセージID"""
        pass

    @msgid_plural.setter
    @abc.abstractmethod
    def msgid_plural(self, value: Optional[str]) -> None:
        """複数形のメッセージIDを設定"""
        pass

    @property
    @abc.abstractmethod
    def msgstr_plural(self) -> Dict[int, str]:
        """複数形の翻訳文"""
        pass

    @msgstr_plural.setter
    @abc.abstractmethod
    def msgstr_plural(self, value: Dict[int, str]) -> None:
        """複数形の翻訳文を設定"""
        pass


class POFile(abc.ABC):
    """POファイルの抽象クラス"""

    @property
    @abc.abstractmethod
    def metadata(self) -> Dict[str, str]:
        """メタデータ"""
        pass

    @metadata.setter
    @abc.abstractmethod
    def metadata(self, value: Dict[str, str]) -> None:
        """メタデータを設定"""
        pass

    @abc.abstractmethod
    def append(self, entry: POEntry) -> None:
        """エントリを追加"""
        pass

    @abc.abstractmethod
    def save(self, fpath: Optional[str] = None) -> None:
        """POファイルを保存"""
        pass

    @abc.abstractmethod
    def find(
        self, st: str, by: str = "msgid", include_obsolete_entries: bool = False
    ) -> Optional[POEntry]:
        """エントリを検索"""
        pass

    @abc.abstractmethod
    def translated_entries(self) -> List[POEntry]:
        """翻訳済みエントリを取得"""
        pass

    @abc.abstractmethod
    def untranslated_entries(self) -> List[POEntry]:
        """未翻訳エントリを取得"""
        pass

    @abc.abstractmethod
    def fuzzy_entries(self) -> List[POEntry]:
        """ファジーエントリを取得"""
        pass

    @abc.abstractmethod
    def obsolete_entries(self) -> List[POEntry]:
        """廃止済みエントリを取得"""
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        """エントリ数を取得"""
        pass

    @abc.abstractmethod
    def __iter__(self) -> Iterator[POEntry]:
        """イテレータ"""
        pass


class POFileFactory(abc.ABC):
    """POファイルファクトリの抽象クラス"""

    @abc.abstractmethod
    def create_entry(self, **kwargs) -> POEntry:
        """POエントリを作成"""
        pass

    @abc.abstractmethod
    def create_file(self) -> POFile:
        """POファイルを作成"""
        pass

    @abc.abstractmethod
    def load_file(self, file_path: Union[str, Path]) -> POFile:
        """POファイルを読み込む"""
        pass
