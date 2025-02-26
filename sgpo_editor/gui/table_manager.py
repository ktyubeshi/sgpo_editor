"""テーブル管理モジュール

このモジュールは、POファイルのエントリを表示・管理するテーブルに関する機能を提供します。
"""

import logging
from typing import Optional, List, Any, Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

from sgpo_editor.core.viewer_po_file import ViewerPOFile

logger = logging.getLogger(__name__)


class TableManager:
    """テーブル管理クラス"""

    def __init__(self, table: QTableWidget, get_current_po: Callable[[], Optional[ViewerPOFile]] = None) -> None:
        """初期化

        Args:
            table: 管理対象のテーブルウィジェット
            get_current_po: 現在のPOファイルを取得するコールバック
        """
        super().__init__()
        self.table = table
        self._display_entries: List[str] = []
        self._current_sort_column: Optional[int] = None
        self._current_sort_order: Optional[Qt.SortOrder] = None
        self._get_current_po = get_current_po
        # エントリのキャッシュ
        self._entry_cache: Dict[str, Any] = {}
        
        # テーブルの初期設定
        self._setup_table()
        
    def _setup_table(self) -> None:
        """テーブルの初期設定"""
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["エントリ番号", "msgctxt", "msgid", "msgstr", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # パフォーマンス最適化のための設定
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)
        
        # ソートを有効化
        # 注意: setSortingEnabled(True)は使用しない（カスタムソートロジックと競合するため）
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        
        # デフォルトのソート設定
        self._current_sort_column = 0  # エントリ番号列
        self._current_sort_order = Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(self._current_sort_column, self._current_sort_order)
        
    def _on_header_clicked(self, logical_index: int) -> None:
        """ヘッダーがクリックされたときの処理"""
        # 現在のソート順を取得
        if self._current_sort_column == logical_index:
            # 同じ列なら昇順/降順を切り替え
            new_order = (
                Qt.SortOrder.DescendingOrder
                if self._current_sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            # 異なる列なら昇順をデフォルトとする
            new_order = Qt.SortOrder.AscendingOrder
            
        # ソートインジケータを更新
        self.table.horizontalHeader().setSortIndicator(logical_index, new_order)
        self._current_sort_column = logical_index
        self._current_sort_order = new_order
        
        # POファイルが存在する場合はソート処理を実行
        po_file = self._get_current_po() if self._get_current_po else None
        if po_file:
            self.update_table(po_file, logical_index, new_order)
        
    def update_table(self, po_file: Optional[ViewerPOFile], sort_column: int = None, 
                     sort_order: Qt.SortOrder = None) -> None:
        """テーブルの更新

        Args:
            po_file: POファイル
            sort_column: ソート列（省略時は現在の設定を維持）
            sort_order: ソート順序（省略時は現在の設定を維持）
        """
        if not po_file:
            self.table.setRowCount(0)
            self._display_entries = []
            self._entry_cache.clear()  # キャッシュをクリア
            return

        if sort_column is not None:
            self._current_sort_column = sort_column
        if sort_order is not None:
            self._current_sort_order = sort_order

        # 表示するエントリの取得
        entries = po_file.get_filtered_entries()
        self._display_entries = [entry.key for entry in entries]
        
        # キャッシュ更新
        self._entry_cache = {entry.key: entry for entry in entries}
        
        # ソート
        if self._current_sort_column is not None and self._current_sort_order is not None:
            entries = self._sort_entries(entries, self._current_sort_column, self._current_sort_order)

        # 描画パフォーマンス向上のためにテーブル更新を一時的に停止
        self.table.setUpdatesEnabled(False)
        
        try:
            # テーブルの更新
            self.table.setRowCount(len(entries))
            for i, entry in enumerate(entries):
                # エントリ番号
                item = QTableWidgetItem(str(entry.position + 1))
                item.setData(Qt.ItemDataRole.UserRole, entry.key)
                self.table.setItem(i, 0, item)
                
                # msgctxt
                msgctxt = entry.msgctxt if entry.msgctxt else ""
                self.table.setItem(i, 1, QTableWidgetItem(msgctxt))
                
                # msgid
                msgid = entry.msgid if entry.msgid else ""
                self.table.setItem(i, 2, QTableWidgetItem(msgid))
                
                # msgstr
                msgstr = entry.msgstr if entry.msgstr else ""
                self.table.setItem(i, 3, QTableWidgetItem(msgstr))
                
                # 状態
                status = entry.get_status() if hasattr(entry, 'get_status') else ""
                status_item = QTableWidgetItem(status)
                self.table.setItem(i, 4, status_item)
        finally:
            # テーブル更新を再開
            self.table.setUpdatesEnabled(True)
            
        # ソートインジケータを更新
        if self._current_sort_column is not None and self._current_sort_order is not None:
            self.table.horizontalHeader().setSortIndicator(
                self._current_sort_column, self._current_sort_order
            )

    def _sort_entries(self, entries: List[Any], column: int, order: Qt.SortOrder) -> List[Any]:
        """エントリをソートする

        Args:
            entries: ソート対象のエントリリスト
            column: ソート列
            order: ソート順序

        Returns:
            ソート後のエントリリスト
        """
        if column == 0:  # エントリ番号
            key_func = lambda entry: entry.position
        elif column == 1:  # msgctxt
            key_func = lambda entry: entry.msgctxt or ""
        elif column == 2:  # msgid
            key_func = lambda entry: entry.msgid or ""
        elif column == 3:  # msgstr
            key_func = lambda entry: entry.msgstr or ""
        elif column == 4:  # 状態
            # 状態の優先順位: 未翻訳 > あいまい > 翻訳済み > 廃止
            def status_key(entry):
                if entry.obsolete:
                    return 3
                elif entry.fuzzy:
                    return 1
                elif not entry.msgstr:
                    return 0
                else:
                    return 2
            key_func = status_key
        else:
            return entries

        reverse = order == Qt.SortOrder.DescendingOrder
        sorted_entries = sorted(entries, key=key_func, reverse=reverse)
        return sorted_entries
        
    def get_display_entries(self) -> List[str]:
        """表示中のエントリキーのリストを取得する

        Returns:
            表示中のエントリキーのリスト
        """
        return self._display_entries

    def select_row(self, row: int) -> None:
        """指定された行を選択する

        Args:
            row: 選択する行
        """
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.table.setCurrentCell(row, 0)

    def get_key_at_row(self, row: int) -> Optional[str]:
        """指定された行のエントリキーを取得する

        Args:
            row: 行インデックス

        Returns:
            エントリキー（存在しない場合はNone）
        """
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def find_row_by_key(self, key: str) -> int:
        """エントリキーから行インデックスを取得する

        Args:
            key: エントリキー

        Returns:
            行インデックス（見つからない場合は-1）
        """
        # キーがディスプレイエントリに含まれていない場合は早期リターン
        if key not in self._display_entries:
            return -1
            
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                return row
        return -1
