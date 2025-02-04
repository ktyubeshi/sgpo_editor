"""GUIアプリケーション用のPOファイル操作モジュール"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..gui.models.entry import EntryModel
from ..gui.models.stats import StatsModel
from ..sgpo.core import SGPOFile


class ViewerPOFile:
    """GUIアプリケーション用のPOファイル操作クラス

    GUIアプリケーションで必要なPOファイルの操作機能を提供します。
    内部的にはSGPOFileを使用してPOファイルの操作を行います。
    """

    def __init__(self, file_path: Optional[str | Path] = None) -> None:
        """POファイルを読み込む

        Args:
            file_path: POファイルのパス
        """
        self._sgpo = SGPOFile()
        self.file_path = None
        self.modified = False

        if file_path:
            self.load(file_path)

    def load(self, file_path: str | Path) -> None:
        """POファイルを読み込む

        Args:
            file_path: POファイルのパス
        """
        self.file_path = Path(file_path)
        self._sgpo.load(str(file_path))
        self.modified = False

    def get_entries(self, filter_type: Optional[str] = None) -> List[EntryModel]:
        """エントリを取得する

        Args:
            filter_type: フィルタータイプ（translated/untranslated/fuzzy）

        Returns:
            エントリのリスト
        """
        entries = []
        for entry in self._sgpo:
            if filter_type == "translated" and not entry.translated():
                continue
            if filter_type == "untranslated" and entry.translated():
                continue
            if filter_type == "fuzzy" and "fuzzy" not in entry.flags:
                continue

            entries.append(EntryModel.from_po_entry(entry))

        return entries

    def update_entry(self, entry: EntryModel) -> None:
        """エントリを更新する

        Args:
            entry: 更新するエントリ
        """
        po_entry = self._sgpo.find_by_key(entry.msgctxt or "", entry.msgid)
        if po_entry:
            po_entry.msgstr = entry.msgstr
            po_entry.flags = ["fuzzy"] if entry.fuzzy else []
            self.modified = True

    def search_entries(self, query: str) -> List[EntryModel]:
        """エントリを検索する

        Args:
            query: 検索クエリ

        Returns:
            検索結果のエントリリスト
        """
        entries = []
        for entry in self._sgpo:
            if (query.lower() in entry.msgid.lower() or
                query.lower() in entry.msgstr.lower() or
                (entry.msgctxt and query.lower() in entry.msgctxt.lower())):
                entries.append(EntryModel.from_po_entry(entry))
        return entries

    def get_stats(self) -> StatsModel:
        """統計情報を取得する

        Returns:
            統計情報
        """
        total = len(self._sgpo)
        translated = len([e for e in self._sgpo if e.translated()])
        fuzzy = len([e for e in self._sgpo if "fuzzy" in e.flags])
        untranslated = total - translated

        progress = (translated / total * 100) if total > 0 else 0

        return StatsModel(
            file_name=self.file_path.name if self.file_path else "",
            total=total,
            translated=translated,
            untranslated=untranslated,
            fuzzy=fuzzy,
            progress=progress
        )

    def save(self, file_path: Optional[str | Path] = None) -> None:
        """POファイルを保存する

        Args:
            file_path: 保存先のパス

        Raises:
            ValueError: 保存先のパスが指定されていない場合
        """
        if not file_path and not self.file_path:
            raise ValueError("保存先のパスが指定されていません")

        save_path = Path(file_path) if file_path else self.file_path
        self._sgpo.save(str(save_path))
        self.file_path = save_path
        self.modified = False
