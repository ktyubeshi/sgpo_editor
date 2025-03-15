"""polibのアダプタークラス

このモジュールは、polibライブラリを使用するためのアダプタークラスを提供します。
"""

import polib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from sgpo_editor.core.po_interface import POEntry, POFile, POFileFactory


class PolibEntry(POEntry):
    """polibのPOEntryアダプター"""
    
    def __init__(self, entry: polib.POEntry):
        """初期化
        
        Args:
            entry: polibのPOEntryオブジェクト
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
        return getattr(self._entry, 'msgctxt', None)
        
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
        return getattr(self._entry, 'comment', None)
        
    @comment.setter
    def comment(self, value: Optional[str]) -> None:
        """コメントを設定"""
        self._entry.comment = value
        
    @property
    def tcomment(self) -> Optional[str]:
        """翻訳者コメント"""
        return getattr(self._entry, 'tcomment', None)
        
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
        return 'fuzzy' in self._entry.flags
        
    @fuzzy.setter
    def fuzzy(self, value: bool) -> None:
        """ファジーフラグを設定"""
        if value and 'fuzzy' not in self._entry.flags:
            self._entry.flags.append('fuzzy')
        elif not value and 'fuzzy' in self._entry.flags:
            self._entry.flags.remove('fuzzy')
            
    def get_native_entry(self) -> polib.POEntry:
        """ネイティブのPOEntryオブジェクトを取得"""
        return self._entry


class PolibFile(POFile):
    """polibのPOFileアダプター"""
    
    def __init__(self, pofile: polib.POFile):
        """初期化
        
        Args:
            pofile: polibのPOFileオブジェクト
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
        if isinstance(entry, PolibEntry):
            self._pofile.append(entry.get_native_entry())
        else:
            # 他の実装からのエントリを変換する必要がある場合
            # ここで変換処理を行う
            raise TypeError("PolibEntryオブジェクトが必要です")
        
    def save(self, fpath: Optional[str] = None) -> None:
        """POファイルを保存"""
        self._pofile.save(fpath=fpath)
        
    def find(self, st: str, by: str = 'msgid', include_obsolete_entries: bool = False) -> Optional[POEntry]:
        """エントリを検索"""
        entry = self._pofile.find(st, by=by, include_obsolete_entries=include_obsolete_entries)
        if entry:
            return PolibEntry(entry)
        return None
        
    def translated_entries(self) -> List[POEntry]:
        """翻訳済みエントリを取得"""
        return [PolibEntry(entry) for entry in self._pofile.translated_entries()]
        
    def untranslated_entries(self) -> List[POEntry]:
        """未翻訳エントリを取得"""
        return [PolibEntry(entry) for entry in self._pofile.untranslated_entries()]
        
    def fuzzy_entries(self) -> List[POEntry]:
        """ファジーエントリを取得"""
        return [PolibEntry(entry) for entry in self._pofile.fuzzy_entries()]
        
    def obsolete_entries(self) -> List[POEntry]:
        """廃止済みエントリを取得"""
        return [PolibEntry(entry) for entry in self._pofile.obsolete_entries()]
        
    def __len__(self) -> int:
        """エントリ数を取得"""
        return len(self._pofile)
        
    def __iter__(self) -> Any:
        """イテレータ"""
        for entry in self._pofile:
            yield PolibEntry(entry)
            
    def get_native_file(self) -> polib.POFile:
        """ネイティブのPOFileオブジェクトを取得"""
        return self._pofile


class PolibFactory(POFileFactory):
    """polibのPOFileファクトリ"""
    
    def create_entry(self, **kwargs) -> POEntry:
        """POエントリを作成"""
        entry = polib.POEntry(**kwargs)
        return PolibEntry(entry)
        
    def create_file(self) -> POFile:
        """POファイルを作成"""
        pofile = polib.POFile()
        pofile.metadata = {
            "Project-Id-Version": "",
            "Report-Msgid-Bugs-To": "",
            "POT-Creation-Date": "",
            "PO-Revision-Date": "",
            "Last-Translator": "",
            "Language-Team": "",
            "Language": "",
            "MIME-Version": "1.0",
            "Content-Type": "text/plain; charset=UTF-8",
            "Content-Transfer-Encoding": "8bit",
            "Plural-Forms": "nplurals=1; plural=0;",
        }
        return PolibFile(pofile)
        
    def load_file(self, file_path: Union[str, Path]) -> POFile:
        """POファイルを読み込む"""
        file_path_str = str(file_path)
        
        # BOMの検出
        with open(file_path, "rb") as f:
            header = f.read(10)
            
        if header.startswith(b"\xde\xbb\xbf"):  # UTF-8 BOM
            with open(file_path, encoding="utf-8-sig") as f:
                postr = f.read()
            pofile = polib.pofile(postr)
        else:
            pofile = polib.pofile(file_path_str, encoding="utf-8")
            
        return PolibFile(pofile) 