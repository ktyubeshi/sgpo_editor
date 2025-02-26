"""Table Management Module

This module provides functionality for displaying and managing table entries from PO files.
"""

import logging
from typing import Optional, List, Any, Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

from sgpo_editor.core.viewer_po_file import ViewerPOFile

logger = logging.getLogger(__name__)


class TableManager:
    """Table Management Class"""

    def __init__(self, table: QTableWidget, get_current_po: Callable[[], Optional[ViewerPOFile]] = None) -> None:
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
        self._get_current_po = get_current_po
        # Entry cache
        self._entry_cache: Dict[str, Any] = {}
        
        # Initial table setup
        self._setup_table()
        
    def _setup_table(self) -> None:
        """Initial table setup"""
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Entry Number", "msgctxt", "msgid", "msgstr", "Status"])
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
        
        # Performance optimization settings
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)
        
        # Enable sorting
        # Note: Do not use setSortingEnabled(True) (conflicts with custom sort logic)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        
        # Default sort settings
        self._current_sort_column = 0  # Entry number column
        self._current_sort_order = Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(self._current_sort_column, self._current_sort_order)
        
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
            self.update_table(po_file, logical_index, new_order)
        
    def update_table(self, po_file: Optional[ViewerPOFile], sort_column: int = None, 
                     sort_order: Qt.SortOrder = None, filter_text: str = None,
                     filter_keyword: str = None) -> List[Any]:
        """Update table

        Args:
            po_file: PO file
            sort_column: Sort column (maintains current setting if omitted)
            sort_order: Sort order (maintains current setting if omitted)
            filter_text: Filter text ("All", "Translated", "Untranslated", "Fuzzy")
            filter_keyword: Filter keyword
            
        Returns:
            List of entries displayed (None if no PO file)
        """
        if not po_file:
            self.table.setRowCount(0)
            self._display_entries = []
            self._entry_cache.clear()  # Clear cache
            return None

        if sort_column is not None:
            self._current_sort_column = sort_column
        if sort_order is not None:
            self._current_sort_order = sort_order

        # Get entries to display
        entries = po_file.get_filtered_entries(
            filter_text=filter_text,
            filter_keyword=filter_keyword
        )
        self._display_entries = [entry.key for entry in entries]
        
        # Update cache
        self._entry_cache = {entry.key: entry for entry in entries}
        
        # Sort
        if self._current_sort_column is not None and self._current_sort_order is not None:
            entries = self._sort_entries(entries, self._current_sort_column, self._current_sort_order)

        # Temporarily disable table updates for better drawing performance
        self.table.setUpdatesEnabled(False)
        
        try:
            # Update table
            self.table.setRowCount(len(entries))
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
                status = entry.get_status() if hasattr(entry, 'get_status') else ""
                status_item = QTableWidgetItem(status)
                self.table.setItem(i, 4, status_item)
            
        finally:
            # Resume table updates
            self.table.setUpdatesEnabled(True)
            
        # Update sort indicator
        if self._current_sort_column is not None and self._current_sort_order is not None:
            self.table.horizontalHeader().setSortIndicator(
                self._current_sort_column, self._current_sort_order
            )
            
        return entries

    def _sort_entries(self, entries: List[Any], column: int, order: Qt.SortOrder) -> List[Any]:
        """Sort entries

        Args:
            entries: List of entries to sort
            column: Sort column
            order: Sort order

        Returns:
            Sorted entry list
        """
        if column == 0:  # Entry number
            key_func = lambda entry: entry.position
        elif column == 1:  # msgctxt
            key_func = lambda entry: entry.msgctxt or ""
        elif column == 2:  # msgid
            key_func = lambda entry: entry.msgid or ""
        elif column == 3:  # msgstr
            key_func = lambda entry: entry.msgstr or ""
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
