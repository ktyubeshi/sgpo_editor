from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from PySide6.QtCore import Qt
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

        # Initial table setup
        self._setup_table()

    def _setup_table(self) -> None:
        """Initial table setup"""
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Entry Number",
            "msgctxt",
            "msgid",
            "msgstr",
            "Status",
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Performance optimization settings
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)

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
