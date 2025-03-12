from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from sgpo_editor.core.viewer_po_file import ViewerPOFile

"""Table Management Module

This module provides functionality for displaying and managing table entries from PO files.
"""

# 循環インポートを避けるために型アノテーションを文字列に変更

logger = logging.getLogger(__name__)


class TableManager:
    """Table Management Class"""

    def __init__(
        self,
        table: QTableWidget,
        get_current_po: Callable[[], Optional["ViewerPOFile"]] = None,
    ) -> None:
        """Initialize

        Args:
            table: Target table widget to manage
            get_current_po: Callback to get the current PO file
        """
        super().__init__()
        self.table = table
        self._display_entries: List[str] = []
        self._current_sort_column: Optional[int] = None
        self._current_sort_order: Optional[Qt.SortOrder] = None
        self._current_filter_text: Optional[str] = None
        self._current_search_text: Optional[str] = None
        self._get_current_po = get_current_po
        # Entry cache
        self._entry_cache: Dict[str, Any] = {}

        # Initial table setup
        self._setup_table()

    def _setup_table(self) -> None:
        """Initial table setup"""
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Entry Number", "msgctxt", "msgid", "msgstr", "Status"]
        )
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
            from sgpo_editor.gui.widgets.search import SearchCriteria

            criteria = SearchCriteria(
                filter=self._current_filter_text,
                filter_keyword=self._current_search_text,
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
        entries: Optional[List[Any]],
        criteria=None,
        sort_column: int = None,
        sort_order: Qt.SortOrder = None,
    ) -> List[Any]:
        """Update table

        Args:
            entries: List of entries to display
            criteria: Search criteria (contains filter_text and filter_keyword)
            sort_column: Sort column (maintains current setting if omitted)
            sort_order: Sort order (maintains current setting if omitted)

        Returns:
            List of entries displayed (None if no entries)
        """
        import logging

        logging.getLogger(__name__)

        # デバッグログ
        print(f"テーブル更新開始: entries={len(entries) if entries else 0}件")
        if criteria:
            print(
                f"フィルタ条件: filter={
                    criteria.filter}, keyword={
                    criteria.filter_keyword}"
            )

        if not entries:
            print("エントリが空のため、テーブルをクリアします")
            self.table.setRowCount(0)
            self._display_entries = []
            self._entry_cache.clear()  # Clear cache
            return None

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
        print(f"表示エントリキー数: {len(self._display_entries)}件")

        # Update cache
        self._entry_cache = {entry.key: entry for entry in entries}
        print(f"キャッシュ更新: {len(self._entry_cache)}件")

        # Sort
        if (
            self._current_sort_column is not None
            and self._current_sort_order is not None
        ):
            print(
                f"ソート実行: column={
                    self._current_sort_column}, order={
                    self._current_sort_order}"
            )
            entries = self._sort_entries(
                entries, self._current_sort_column, self._current_sort_order
            )

        # Temporarily disable table updates for better drawing performance
        print("テーブル更新を一時停止")
        self.table.setUpdatesEnabled(False)

        try:
            # Update table
            print(f"テーブル行数設定: {len(entries)}行")
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
                status = entry.get_status() if hasattr(entry, "get_status") else ""
                status_item = QTableWidgetItem(status)
                self.table.setItem(i, 4, status_item)

            print(f"テーブル更新完了: {len(entries)}行設定済み")

        except Exception as e:
            print(f"テーブル更新中にエラーが発生: {str(e)}")
            import traceback

            traceback.print_exc()
            raise
        finally:
            # Resume table updates
            print("テーブル更新を再開")
            self.table.setUpdatesEnabled(True)

        # Update sort indicator
        if (
            self._current_sort_column is not None
            and self._current_sort_order is not None
        ):
            self.table.horizontalHeader().setSortIndicator(
                self._current_sort_column, self._current_sort_order
            )

        print(f"テーブル更新処理完了: {len(entries)}件表示")
        return entries

    def _get_filter_conditions(self) -> tuple[Optional[str], Optional[str]]:
        """現在のフィルタ条件を取得

        Returns:
            フィルタテキストとキーワードのタプル
        """
        return (self._current_filter_text, self._current_search_text)

    def _sort_entries(
        self, entries: List[Any], column: int, order: Qt.SortOrder
    ) -> List[Any]:
        """Sort entries

        Args:
            entries: List of entries to sort
            column: Sort column
            order: Sort order

        Returns:
            Sorted entry list
        """
        if column == 0:  # Entry number

            def key_func(entry):
                return entry.position

        elif column == 1:  # msgctxt

            def key_func(entry):
                return entry.msgctxt or ""

        elif column == 2:  # msgid

            def key_func(entry):
                return entry.msgid or ""

        elif column == 3:  # msgstr

            def key_func(entry):
                return entry.msgstr or ""

        elif column == 4:  # Status
            # Status priority: Untranslated > Fuzzy > Translated > Obsolete
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
