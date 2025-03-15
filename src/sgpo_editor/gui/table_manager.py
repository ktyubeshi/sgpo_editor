from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set, Union

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.i18n import translate

"""Table Management Module

This module provides functionality for displaying and managing table entries from PO files.
"""

# 循環インポートを避けるために型アノテーションを文字列で指定
# POEntry = Any  # 実際の型は循環インポートを避けるため文字列で指定

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
        self._entry_cache: Dict[str, EntryModel] = {}
        # 列幅の初期値を設定
        self._default_column_widths = [80, 120, 200, 200, 100, 80]
        # 列の表示/非表示設定
        self._hidden_columns: Set[int] = set()
        # 列名の定義
        self._column_names = [
            "Entry Number",
            "msgctxt",
            "msgid",
            "msgstr",
            "Status",
            "Score",
        ]

        # Initial table setup
        self._setup_table()

    def _setup_table(self) -> None:
        """Initial table setup"""
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(self._column_names)
        
        # すべての列をInteractiveモードに設定（ユーザーが列幅を調整可能）
        for i in range(6):
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
        entries: Optional[List[EntryModel]],
        criteria: Optional[SearchCriteria] = None,
        sort_column: Optional[int] = None,
        sort_order: Optional[Qt.SortOrder] = None,
    ) -> List[EntryModel]:
        """Update table

        Args:
            entries: List of entries to display
            criteria: Search criteria (contains filter_text and filter_keyword)
            sort_column: Sort column (maintains current setting if omitted)
            sort_order: Sort order (maintains current setting if omitted)

        Returns:
            List of entries displayed
        """
        logger.debug("TableManager.update_table: 開始")
        
        # 現在の列の表示/非表示状態を内部状態と同期
        self._sync_column_visibility()
        
        if not entries:
            logger.debug("TableManager.update_table: エントリが空のため、テーブルをクリア")
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
        logger.debug(f"TableManager.update_table: 表示エントリ数: {len(self._display_entries)}件")

        # Update cache - 既存のキャッシュを更新するだけでなく、完全に置き換える
        self._entry_cache = {entry.key: entry for entry in entries}
        logger.debug(f"TableManager.update_table: キャッシュを更新: {len(self._entry_cache)}件")

        # Sort
        logger.debug(f"TableManager.update_table: エントリをソート column={self._current_sort_column}, order={self._current_sort_order}")
        if self._current_sort_column == 5:  # Score column
            sorted_entries = self._sort_entries_by_score(
                entries, self._current_sort_order
            )
        else:
            sorted_entries = self._sort_entries(
                entries, self._current_sort_column, self._current_sort_order
            )
        logger.debug(f"TableManager.update_table: ソート完了: {len(sorted_entries)}件")

        # テーブルの更新を一時停止して効率的に更新
        logger.debug(f"TableManager.update_table: テーブル更新を一時停止")
        self.table.setUpdatesEnabled(False)
        try:
            # テーブルを更新
            logger.debug(f"TableManager.update_table: テーブル内容を更新")
            self._update_table_contents(sorted_entries)
            logger.debug(f"TableManager.update_table: テーブル内容の更新完了")
        finally:
            # 必ず更新を再開
            logger.debug(f"TableManager.update_table: テーブル更新を再開")
            self.table.setUpdatesEnabled(True)
            # 表示を強制的に更新
            logger.debug(f"TableManager.update_table: 表示を強制的に更新")
            self.table.viewport().update()
            # テーブルのレイアウトを更新
            logger.debug(f"TableManager.update_table: テーブルのレイアウトを更新")
            self.table.updateGeometry()
            # テーブルを再描画
            logger.debug(f"TableManager.update_table: テーブルを再描画")
            self.table.repaint()
            
        logger.debug(f"TableManager.update_table: 完了: {len(sorted_entries)}件表示")

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
        
        # 各列の幅を取得（最小幅10ピクセルを保証）
        for i in range(self.table.columnCount()):
            width = self.table.columnWidth(i)
            # 0幅の列は保存しない（最小10ピクセルとする）
            if width < 10:
                width = 10
            column_widths[str(i)] = width
            logger.debug(f"列 {i} ({self.get_column_name(i)}) の幅を保存: {width}px")
        
        # JSON形式で保存
        settings.setValue("column_widths", json.dumps(column_widths))
    
    def _load_column_widths(self) -> None:
        """保存された列幅を読み込み、テーブルに適用"""
        settings = QSettings("SGPOEditor", "TableSettings")
        column_widths_json = settings.value("column_widths", "")
        
        if column_widths_json:
            try:
                column_widths = json.loads(column_widths_json)
                # 保存された列幅を適用（最小幅10ピクセルを保証）
                for col_idx_str, width in column_widths.items():
                    col_idx = int(col_idx_str)
                    # テスト環境ではtable.columnCountがMagicMockになるため、
                    # 直接比較せずにtry-exceptで囲む
                    try:
                        # 列数の範囲内かチェック
                        column_count = self.table.columnCount()
                        if isinstance(column_count, int) and 0 <= col_idx < column_count:
                            # 最小幅を10ピクセルとして設定
                            actual_width = max(int(width), 10)
                            self.table.setColumnWidth(col_idx, actual_width)
                            logger.debug(f"列 {col_idx} ({self.get_column_name(col_idx)}) の幅を設定: {actual_width}px")
                    except (TypeError, ValueError):
                        # テスト環境ではエラーが発生する可能性があるが無視
                        # 最小幅を10ピクセルとして設定
                        actual_width = max(int(width), 10)
                        self.table.setColumnWidth(col_idx, actual_width)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"列幅の設定読み込みに失敗しました: {e}")
                self._apply_default_column_widths()
        else:
            # 保存された設定がない場合はデフォルト値を適用
            self._apply_default_column_widths()
    
    def _apply_default_column_widths(self) -> None:
        """デフォルトの列幅を適用"""
        # 列幅の初期値を再設定
        self._default_column_widths = [100, 100, 200, 200, 150, 80]
        
        logger.debug(f"デフォルト列幅を適用: {self._default_column_widths}")
        for i, width in enumerate(self._default_column_widths):
            if i < self.table.columnCount():
                # 幅【0にしないように最小値を10に設定
                actual_width = max(width, 10)
                self.table.setColumnWidth(i, actual_width)
                logger.debug(f"列 {i} ({self.get_column_name(i)}) のデフォルト幅を設定: {actual_width}px")
    
    def toggle_column_visibility(self, column_index: int) -> None:
        """列の表示/非表示を切り替える
        
        Args:
            column_index: 列インデックス
        """
        if 0 <= column_index < self.table.columnCount():
            # 現在の状態を取得
            is_hidden = self.table.isColumnHidden(column_index)
            
            # 状態を反転
            new_hidden_state = not is_hidden
            
            # 内部の_hidden_columnsセットを更新
            if new_hidden_state:
                self._hidden_columns.add(column_index)
                logger.debug(f"列 {column_index} ({self.get_column_name(column_index)}) を非表示に設定します")
            else:
                self._hidden_columns.discard(column_index)
                logger.debug(f"列 {column_index} ({self.get_column_name(column_index)}) を表示に設定します")
            
            # 設定を保存
            self._save_column_visibility()
            
            # すべての列の表示/非表示状態を再確認して適用（同期を確保）
            self._apply_column_visibility()
            
            # 小さな遅延を入れてテーブルの描画を確実にする
            import time
            time.sleep(0.01)
            
            # テーブルの更新を促す
            self.table.horizontalHeader().updateGeometry()
            self.table.setUpdatesEnabled(False)
            self.table.setUpdatesEnabled(True)
            self.table.horizontalHeader().viewport().update()
            self.table.repaint()
            
            # デバッグ情報
            print(f"列 {column_index} ({self.get_column_name(column_index)}) の表示状態を切り替えました: {'非表示' if new_hidden_state else '表示'}")
    
    def is_column_visible(self, column_index: int) -> bool:
        """列が表示されているか確認する
        
        Args:
            column_index: 列インデックス
            
        Returns:
            列が表示されている場合はTrue、非表示の場合はFalse
        """
        # 実際のテーブルの状態を確認
        is_hidden_in_table = self.table.isColumnHidden(column_index)
        return not is_hidden_in_table
    
    def _sync_column_visibility(self) -> None:
        """内部の_hidden_columnsセットとテーブルの表示/非表示状態を同期する"""
        # テーブルの状態を確認し、内部状態を更新
        try:
            column_count = self.table.columnCount()
            if isinstance(column_count, int):
                for i in range(column_count):
                    is_hidden = self.table.isColumnHidden(i)
                    if is_hidden:
                        self._hidden_columns.add(i)
                    elif i in self._hidden_columns:
                        self._hidden_columns.remove(i)
        except (TypeError, ValueError):
            # テスト環境では列数の取得に失敗する可能性があるため、
            # デフォルトの列数（6列）を使用
            for i in range(len(self._column_names)):
                try:
                    is_hidden = self.table.isColumnHidden(i)
                    if is_hidden:
                        self._hidden_columns.add(i)
                    elif i in self._hidden_columns:
                        self._hidden_columns.remove(i)
                except (TypeError, ValueError):
                    # テスト環境ではエラーが発生する可能性があるが処理を続行
                    pass
    
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
        logger.debug(f"保存された非表示列: {hidden_columns}")
        
    def _apply_column_visibility(self) -> None:
        """内部状態(_hidden_columns)に基づいて列の表示/非表示状態を適用する"""
        # 列数を取得
        column_count = self.table.columnCount()
        
        # 各列に対して表示/非表示を設定
        logger.debug(f"列の表示/非表示状態を適用: 列数={column_count}, 非表示列={self._hidden_columns}")
        
        # まず一時的に全列表示
        for i in range(column_count):
            self.table.setColumnHidden(i, False)
        
        # 内部状態に基づいて非表示設定を適用
        for i in range(column_count):
            # 列が非表示リストに含まれるか確認
            is_hidden = i in self._hidden_columns
            
            # 実際の表示状態を取得
            current_gui_hidden = self.table.isColumnHidden(i)
            
            # 内部状態とGUIの状態が異なる場合、同期させる
            if current_gui_hidden != is_hidden:
                logger.debug(f"列 {i} ({self.get_column_name(i)}) の表示状態を修正: {current_gui_hidden} -> {is_hidden}")
                self.table.setColumnHidden(i, is_hidden)
                
        # デバッグ出力
        for i in range(column_count):
            logger.debug(f"列 {i} ({self.get_column_name(i)}) の状態: 内部={i in self._hidden_columns}, GUI={self.table.isColumnHidden(i)}")
    
    def _load_column_visibility(self) -> None:
        """列の表示/非表示設定を読み込む"""
        settings = QSettings("SGPOEditor", "TableSettings")
        hidden_columns_json = settings.value("hidden_columns", "")
        
        # 初期化：すべての列を表示状態にする
        self._hidden_columns = set()
        
        # テスト環境ではtable.columnCountがMagicMockになるため、try-exceptで囲む
        try:
            column_count = self.table.columnCount()
            if isinstance(column_count, int):
                for i in range(column_count):
                    self.table.setColumnHidden(i, False)
        except (TypeError, ValueError):
            # テスト環境では列数の取得に失敗する可能性があるため、
            # デフォルトの列数（6列）を使用
            for i in range(len(self._column_names)):
                self.table.setColumnHidden(i, False)
        
        if hidden_columns_json:
            try:
                hidden_columns = json.loads(hidden_columns_json)
                self._hidden_columns = set(int(col) for col in hidden_columns)
                
                # 列の表示/非表示を設定
                for col in self._hidden_columns:
                    try:
                        # 列数の範囲内かチェック
                        column_count = self.table.columnCount()
                        if isinstance(column_count, int) and 0 <= col < column_count:
                            self.table.setColumnHidden(col, True)
                            logger.debug(f"列 {col} を非表示に設定しました")
                    except (TypeError, ValueError):
                        # テスト環境ではエラーが発生する可能性があるが処理を続行
                        self.table.setColumnHidden(col, True)
                        logger.debug(f"列 {col} を非表示に設定しました")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"列の表示/非表示設定の読み込みに失敗しました: {e}")
                self._hidden_columns = set()
    
    def _sort_entries(
        self, entries: List[EntryModel], column: int, order: Qt.SortOrder
    ) -> List[EntryModel]:
        """Sort entries

        Args:
            entries: List of entries to sort
            column: Sort column
            order: Sort order

        Returns:
            Sorted entry list
        """
        # Score列の場合は専用のソート関数を使用
        if column == 5:  # Score column
            return self._sort_entries_by_score(entries, order)
            
        def get_key_func(col: int) -> Callable[[EntryModel], Union[str, int]]:
            if col == 0:  # Entry number
                return lambda entry: entry.position
            elif col == 1:  # msgctxt
                return lambda entry: entry.msgctxt or ""
            elif col == 2:  # msgid
                return lambda entry: entry.msgid or ""
            elif col == 3:  # msgstr
                return lambda entry: entry.msgstr or ""
            elif col == 4:  # Status

                def status_key(entry: EntryModel) -> int:
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
        
    def _sort_entries_by_score(
        self, entries: List[EntryModel], order: Qt.SortOrder
    ) -> List[EntryModel]:
        """スコアでエントリをソートする

        Args:
            entries: ソートするエントリのリスト
            order: ソート順序

        Returns:
            ソートされたエントリリスト
        """
        def score_key(entry: EntryModel) -> tuple:
            # スコアがNoneの場合は常に最後に来るようにする
            if entry.score is None:
                # 第1要素が1ならNoneのエントリ（後ろに配置）
                return (1, 0)
            else:
                # 第1要素が0なら通常のエントリ（前に配置）
                # 第2要素は実際のスコア値
                return (0, entry.score if order == Qt.SortOrder.AscendingOrder else -entry.score)

        # タプルによるソート: 第1要素でまず比較し、同じ場合は第2要素で比較
        return sorted(entries, key=score_key)

    def _update_table_contents(self, entries: List[EntryModel]) -> None:
        """テーブルの内容を更新する

        Args:
            entries: 表示するエントリのリスト
        """
        logger.debug(f"TableManager._update_table_contents: 開始 entries={len(entries)}件")
        
        # テーブルの行数を設定
        self.table.setRowCount(len(entries))
        
        # 各エントリをテーブルに追加
        for row, entry in enumerate(entries):
            # エントリ番号
            item = QTableWidgetItem(str(entry.position))
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            self.table.setItem(row, 0, item)
            
            # msgctxt
            item = QTableWidgetItem(entry.msgctxt or "")
            self.table.setItem(row, 1, item)
            
            # msgid
            item = QTableWidgetItem(entry.msgid)
            self.table.setItem(row, 2, item)
            
            # msgstr
            item = QTableWidgetItem(entry.msgstr)
            self.table.setItem(row, 3, item)
            
            # ステータス
            status = "Fuzzy" if entry.fuzzy else "Translated" if entry.msgstr else "Untranslated"
            item = QTableWidgetItem(status)
            
            # ステータスに応じて背景色を設定
            if entry.fuzzy:
                item.setBackground(QColor(255, 255, 200))  # 薄い黄色
            elif not entry.msgstr:
                item.setBackground(QColor(255, 200, 200))  # 薄い赤色
            else:
                item.setBackground(QColor(200, 255, 200))  # 薄い緑色
            
            self.table.setItem(row, 4, item)
            
            # スコア（仮の実装）
            score = "N/A"
            item = QTableWidgetItem(score)
            self.table.setItem(row, 5, item)
        
        # 列の表示/非表示を適用
        self._apply_column_visibility()
        
        # テーブルの表示を強制的に更新
        self.table.viewport().update()
        self.table.updateGeometry()
        self.table.repaint()
        
        logger.debug(f"TableManager._update_table_contents: 完了")

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
