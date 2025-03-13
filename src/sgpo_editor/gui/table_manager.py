from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set, Union

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.search import SearchCriteria

"""Table Management Module

This module provides functionality for displaying and managing table entries from PO files.
"""

# 循環インポートを避けるために型アノテーションを文字列で指定
POEntry = Any  # 実際の型は循環インポートを避けるため文字列で指定

logger = logging.getLogger(__name__)


class TableManager:
    """Table Management Class"""

    def __init__(
        self,
        table: QTableWidget,
        get_current_po: Optional[Callable[[], Optional[ViewerPOFile]]] = None,
    ) -> None:
        """Initialize

        Args:
            table: Target table widget to manage
            get_current_po: Callback to get the current PO file
        """
        self.table = table
        self._display_entries: List[str] = []
        self._current_sort_column: int = 0
        self._current_sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
        self._current_filter_text: str = ""
        self._current_search_text: str = ""
        self._get_current_po = get_current_po
        # Entry cache
        self._entry_cache: Dict[str, POEntry] = {}
        # 列幅の初期値を設定
        self._default_column_widths = [80, 120, 200, 200, 100]
        # 列の表示/非表示設定
        self._hidden_columns: Set[int] = set()
        # 列名の定義
        self._column_names = [
            "Entry Number",
            "msgctxt",
            "msgid",
            "msgstr",
            "Status",
        ]

        # Initial table setup
        self._setup_table()

    def _setup_table(self) -> None:
        """Initial table setup"""
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(self._column_names)
        
        # すべての列をInteractiveモードに設定（ユーザーが列幅を調整可能）
        for i in range(5):
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Interactive
            )
        
        # 保存された列幅を読み込む、なければデフォルト値を使用
        self._load_column_widths()
        
        # 保存された列の表示/非表示設定を読み込む
        self._load_column_visibility()
        
        # 列幅の変更イベントを接続
        self.table.horizontalHeader().sectionResized.connect(self._on_section_resized)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Performance optimization settings
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)
        
        # 列幅の自動調整を無効化（ユーザーが設定した列幅を維持するため）
        self.table.horizontalHeader().setStretchLastSection(False)

        # Enable sorting
        # Note: Do not use setSortingEnabled(True) (conflicts with custom sort
        # logic)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)

        # Default sort settings
        self._current_sort_column = 0  # Entry number column
        self._current_sort_order = Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(
            self._current_sort_column, self._current_sort_order
        )

    def _on_header_clicked(self, logical_index: int) -> None:
        """Process header click event"""
        # Get current sort order
        if self._current_sort_column == logical_index:
            # Toggle ascending/descending if same column
            new_order = (
                Qt.SortOrder.DescendingOrder
                if self._current_sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            # Default to ascending order for different column
            new_order = Qt.SortOrder.AscendingOrder

        # Update sort indicator
        self.table.horizontalHeader().setSortIndicator(logical_index, new_order)
        self._current_sort_column = logical_index
        self._current_sort_order = new_order

        # Execute sort process if PO file exists
        po_file = self._get_current_po() if self._get_current_po else None
        if po_file:
            # フィルタ条件を取得
            # SearchCriteriaではfilter_keywordにNoneは許容されないため、空文字列を使用
            criteria = SearchCriteria(
                filter=self._current_filter_text,
                filter_keyword=self._current_search_text,  # 初期化時に空文字列として設定済み
                match_mode="部分一致",
            )

            # 現在のフィルタ条件を保持したままソートを実行
            entries = po_file.get_filtered_entries(
                filter_text=self._current_filter_text,
                filter_keyword=self._current_search_text,
            )

            # テーブルを更新
            self.update_table(entries, criteria, logical_index, new_order)

    def update_table(
        self,
        entries: Optional[List[POEntry]],
        criteria: Optional[SearchCriteria] = None,
        sort_column: Optional[int] = None,
        sort_order: Optional[Qt.SortOrder] = None,
    ) -> List[POEntry]:
        """Update table

        Args:
            entries: List of entries to display
            criteria: Search criteria (contains filter_text and filter_keyword)
            sort_column: Sort column (maintains current setting if omitted)
            sort_order: Sort order (maintains current setting if omitted)

        Returns:
            List of entries displayed
        """
        if not entries:
            self.table.setRowCount(0)
            self._display_entries = []
            self._entry_cache.clear()
            return []

        if sort_column is not None:
            self._current_sort_column = sort_column
        if sort_order is not None:
            self._current_sort_order = sort_order

        # 現在のフィルタ条件を保存
        if criteria:
            self._current_filter_text = criteria.filter
            self._current_search_text = criteria.filter_keyword

        # エントリのキーを保存
        self._display_entries = [entry.key for entry in entries]

        # Update cache
        self._entry_cache = {entry.key: entry for entry in entries}

        # Sort
        sorted_entries = self._sort_entries(
            entries, self._current_sort_column, self._current_sort_order
        )

        # テーブルを更新
        self._update_table_contents(sorted_entries)

        return sorted_entries

    def _on_section_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """列幅が変更されたときに呼び出される
        
        Args:
            logical_index: 変更された列のインデックス
            old_size: 変更前のサイズ
            new_size: 変更後のサイズ
        """
        # 列幅を保存
        self._save_column_widths()
    
    def _save_column_widths(self) -> None:
        """現在の列幅を設定ファイルに保存"""
        settings = QSettings("SGPOEditor", "TableSettings")
        column_widths = {}
        
        # 各列の幅を取得
        for i in range(self.table.columnCount()):
            column_widths[str(i)] = self.table.columnWidth(i)
        
        # JSON形式で保存
        settings.setValue("column_widths", json.dumps(column_widths))
    
    def _load_column_widths(self) -> None:
        """保存された列幅を読み込み、テーブルに適用"""
        settings = QSettings("SGPOEditor", "TableSettings")
        column_widths_json = settings.value("column_widths", "")
        
        if column_widths_json:
            try:
                column_widths = json.loads(column_widths_json)
                # 保存された列幅を適用
                for col_idx_str, width in column_widths.items():
                    col_idx = int(col_idx_str)
                    if 0 <= col_idx < self.table.columnCount():
                        self.table.setColumnWidth(col_idx, int(width))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"列幅の設定読み込みに失敗しました: {e}")
                self._apply_default_column_widths()
        else:
            # 保存された設定がない場合はデフォルト値を適用
            self._apply_default_column_widths()
    
    def _apply_default_column_widths(self) -> None:
        """デフォルトの列幅を適用"""
        for i, width in enumerate(self._default_column_widths):
            if i < self.table.columnCount():
                self.table.setColumnWidth(i, width)
    
    def toggle_column_visibility(self, column_index: int) -> None:
        """列の表示/非表示を切り替える
        
        Args:
            column_index: 列インデックス
        """
        if 0 <= column_index < self.table.columnCount():
            # 現在の状態を確認
            current_visible = not self.table.isColumnHidden(column_index)
            
            if column_index in self._hidden_columns:
                # 非表示の列を表示にする
                self.table.setColumnHidden(column_index, False)
                self._hidden_columns.remove(column_index)
                logger.debug(f"列 {column_index} を表示に設定しました")
            else:
                # 表示中の列を非表示にする
                self.table.setColumnHidden(column_index, True)
                self._hidden_columns.add(column_index)
                logger.debug(f"列 {column_index} を非表示に設定しました")
            
            # 設定を保存
            self._save_column_visibility()
    
    def is_column_visible(self, column_index: int) -> bool:
        """列が表示されているか確認する
        
        Args:
            column_index: 列インデックス
            
        Returns:
            列が表示されている場合はTrue、非表示の場合はFalse
        """
        # 内部の_hidden_columnsセットと実際のテーブルの状態を両方確認
        in_hidden_set = column_index in self._hidden_columns
        is_hidden_in_table = self.table.isColumnHidden(column_index)
        
        # もし不整合があれば、テーブルの状態を優先して_hidden_columnsを更新
        if in_hidden_set != is_hidden_in_table:
            if is_hidden_in_table:
                self._hidden_columns.add(column_index)
            else:
                if column_index in self._hidden_columns:
                    self._hidden_columns.remove(column_index)
        
        return not is_hidden_in_table
    
    def get_column_name(self, column_index: int) -> str:
        """列名を取得する
        
        Args:
            column_index: 列インデックス
            
        Returns:
            列名
        """
        if 0 <= column_index < len(self._column_names):
            return self._column_names[column_index]
        return ""
    
    def get_column_count(self) -> int:
        """列数を取得する
        
        Returns:
            列数
        """
        return len(self._column_names)
    
    def _save_column_visibility(self) -> None:
        """列の表示/非表示設定を保存する"""
        settings = QSettings("SGPOEditor", "TableSettings")
        # 非表示の列インデックスをリストとして保存
        hidden_columns = list(self._hidden_columns)
        settings.setValue("hidden_columns", json.dumps(hidden_columns))
        # 設定を確実に保存するためにsync()を呼び出す
        settings.sync()
    
    def _load_column_visibility(self) -> None:
        """列の表示/非表示設定を読み込む"""
        settings = QSettings("SGPOEditor", "TableSettings")
        hidden_columns_json = settings.value("hidden_columns", "")
        
        # 初期化：すべての列を表示状態にする
        self._hidden_columns = set()
        for i in range(self.table.columnCount()):
            self.table.setColumnHidden(i, False)
        
        if hidden_columns_json:
            try:
                hidden_columns = json.loads(hidden_columns_json)
                self._hidden_columns = set(int(col) for col in hidden_columns)
                
                # 列の表示/非表示を設定
                for col in self._hidden_columns:
                    if 0 <= col < self.table.columnCount():
                        self.table.setColumnHidden(col, True)
                        logger.debug(f"列 {col} を非表示に設定しました")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"列の表示/非表示設定の読み込みに失敗しました: {e}")
                self._hidden_columns = set()
    
    def _sort_entries(
        self, entries: List[POEntry], column: int, order: Qt.SortOrder
    ) -> List[POEntry]:
        """Sort entries

        Args:
            entries: List of entries to sort
            column: Sort column
            order: Sort order

        Returns:
            Sorted entry list
        """

        def get_key_func(col: int) -> Callable[[POEntry], Union[str, int]]:
            if col == 0:  # Entry number
                return lambda entry: entry.position
            elif col == 1:  # msgctxt
                return lambda entry: entry.msgctxt or ""
            elif col == 2:  # msgid
                return lambda entry: entry.msgid or ""
            elif col == 3:  # msgstr
                return lambda entry: entry.msgstr or ""
            elif col == 4:  # Status

                def status_key(entry: POEntry) -> int:
                    if entry.obsolete:
                        return 3
                    elif entry.fuzzy:
                        return 1
                    elif not entry.msgstr:
                        return 0
                    return 2

                return status_key
            return lambda entry: ""

        key_func = get_key_func(column)
        reverse = order == Qt.SortOrder.DescendingOrder
        return sorted(entries, key=key_func, reverse=reverse)

    def _update_table_contents(self, entries: List[POEntry]) -> None:
        """Update table contents"""
        # Temporarily disable table updates for better drawing performance
        self.table.setUpdatesEnabled(False)

        try:
            # Update table
            self.table.setRowCount(len(entries))

            # サンプルエントリの表示（最大3件）
            if len(entries) > 0:
                print("表示するエントリのサンプル:")
                for i, entry in enumerate(entries[:3]):
                    print(
                        f"  エントリ {i + 1}: msgid={entry.msgid[:30] if entry.msgid else ''}... msgstr={entry.msgstr[:30] if entry.msgstr else ''}..."
                    )

            for i, entry in enumerate(entries):
                # Entry number
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

                # Status
                try:
                    # エントリの型情報をログ出力
                    if i < 3:  # 最初の数行だけログ出力
                        logger.debug(
                            f"Entry type: {type(entry)}, has get_status: {hasattr(entry, 'get_status')}"
                        )

                    # 状態取得方法を決定
                    if hasattr(entry, "get_status") and callable(
                        getattr(entry, "get_status")
                    ):
                        # get_statusメソッドがあれば使用
                        status = entry.get_status()
                        logger.debug(
                            f"Get status by method: {status}"
                        ) if i < 3 else None
                    elif hasattr(entry, "obsolete") and entry.obsolete:
                        status = "廃止済み"
                    elif hasattr(entry, "fuzzy") and entry.fuzzy:
                        status = "ファジー"
                    elif hasattr(entry, "msgstr") and not entry.msgstr:
                        status = "未翻訳"
                    elif hasattr(entry, "msgstr") and entry.msgstr:
                        status = "翻訳済み"
                    else:
                        # 型情報を詳細ログ出力
                        logger.debug(f"Unknown entry state: {entry}")
                        status = ""
                except Exception as e:
                    logger.error(f"エントリの状態取得中にエラー: {e}")
                    status = ""

                # 状態列を表示
                status_item = QTableWidgetItem(status)
                self.table.setItem(i, 4, status_item)

        except Exception as e:
            logger.error(f"テーブル更新中にエラーが発生: {str(e)}")
            raise
        finally:
            # Resume table updates
            self.table.setUpdatesEnabled(True)

        # Update sort indicator
        self.table.horizontalHeader().setSortIndicator(
            self._current_sort_column, self._current_sort_order
        )

    def _get_filter_conditions(self) -> tuple[Optional[str], Optional[str]]:
        """現在のフィルタ条件を取得

        Returns:
            フィルタテキストとキーワードのタプル
        """
        return (self._current_filter_text, self._current_search_text)

    def get_display_entries(self) -> List[str]:
        """Get list of entry keys currently displayed

        Returns:
            List of entry keys currently displayed
        """
        return self._display_entries

    def select_row(self, row: int) -> None:
        """Select specified row

        Args:
            row: Row to select
        """
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.table.setCurrentCell(row, 0)

    def get_key_at_row(self, row: int) -> Optional[str]:
        """Get entry key at specified row

        Args:
            row: Row index

        Returns:
            Entry key (None if not exists)
        """
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def find_row_by_key(self, key: str) -> int:
        """Get row index from entry key

        Args:
            key: Entry key

        Returns:
            Row index (-1 if not found)
        """
        # Early return if key is not in display entries
        if key not in self._display_entries:
            return -1

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                return row
        return -1
