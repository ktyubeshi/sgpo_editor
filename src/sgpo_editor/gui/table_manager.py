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
        # 現在の列の表示/非表示状態を内部状態と同期
        self._sync_column_visibility()
        
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
        # Score列の場合は専用のソート関数を使用
        if column == 5:  # Score column
            return self._sort_entries_by_score(entries, order)
            
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
        
    def _sort_entries_by_score(self, entries: List[POEntry], order: Qt.SortOrder) -> List[POEntry]:
        """Sort entries by score
        
        Args:
            entries: List of entries to sort
            order: Sort order
            
        Returns:
            Sorted entry list by score
        """
        # まず、スコアを持つエントリとNoneのエントリに分ける
        entries_with_score = []
        entries_without_score = []
        
        for entry in entries:
            if hasattr(entry, "overall_quality_score") and callable(
                getattr(entry, "overall_quality_score")
            ):
                score = entry.overall_quality_score()
                if score is not None:
                    entries_with_score.append((entry, score))
                else:
                    entries_without_score.append(entry)
            else:
                entries_without_score.append(entry)
        
        # スコアを持つエントリをソート
        reverse = order == Qt.SortOrder.DescendingOrder
        sorted_entries_with_score = sorted(entries_with_score, key=lambda x: x[1], reverse=reverse)
        
        # 結果を結合（スコアなしのエントリは常に最後）
        result = [entry for entry, _ in sorted_entries_with_score] + entries_without_score
        
        return result

    def _update_table_contents(self, entries: List[POEntry]) -> None:
        """Update table contents"""
        # Temporarily disable table updates for better drawing performance
        self.table.setUpdatesEnabled(False)
        
        # 列のヘッダーラベルが正しく設定されているか確認
        if self.table.columnCount() == len(self._column_names):
            self.table.setHorizontalHeaderLabels(self._column_names)
            
        # 内部状態の列の表示/非表示状態を保存
        hidden_columns_backup = self._hidden_columns.copy()
        logger.debug(f"更新前の非表示列バックアップ: {hidden_columns_backup}")
        
        # 各列の現在の表示状態をログ出力
        for i in range(self.table.columnCount()):
            logger.debug(f"更新前の列 {i} ({self.get_column_name(i)}) の状態: hidden={self.table.isColumnHidden(i)}")

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
                
                # Score列を追加
                score_item = QTableWidgetItem()
                score = None
                
                # overall_quality_scoreメソッドがあればスコアを取得
                if hasattr(entry, "overall_quality_score") and callable(
                    getattr(entry, "overall_quality_score")
                ):
                    score = entry.overall_quality_score()
                
                if score is not None:
                    # スコアを文字列として表示
                    score_item.setText(str(score))
                    # データをソート用に保持（整数として）
                    score_item.setData(Qt.ItemDataRole.UserRole, score)
                    
                    # スコアに応じて背景色を設定
                    if score >= 80:  # 良好
                        score_item.setBackground(QColor(200, 255, 200))  # 薄緑
                    elif score >= 60:  # 普通
                        score_item.setBackground(QColor(255, 255, 200))  # 薄黄
                    else:  # 要改善
                        score_item.setBackground(QColor(255, 200, 200))  # 薄赤
                else:
                    # スコアがない場合は「-」を表示
                    score_item.setText("-")
                    # ソート時に未評価が最後に来るように値を設定
                    score_item.setData(Qt.ItemDataRole.UserRole, -1)
                
                self.table.setItem(i, 5, score_item)

        except Exception as e:
            logger.error(f"テーブル更新中にエラーが発生: {str(e)}")
            raise
        finally:
            # 小さな遅延を入れてテーブルの描画を確実にする
            import time
            time.sleep(0.01)
            
            # 列のヘッダーラベルが正しく設定されているか再確認
            if self.table.columnCount() == len(self._column_names):
                self.table.setHorizontalHeaderLabels(self._column_names)
            
            # 内部状態を復元
            self._hidden_columns = hidden_columns_backup
            logger.debug(f"復元する非表示列: {self._hidden_columns}")
            
            # 内部状態に基づいて列の表示/非表示状態を確実に適用
            self._apply_column_visibility()
            
            # 列ヘッダーの全高を取得し、再設定
            header_height = self.table.horizontalHeader().height()
            self.table.horizontalHeader().setFixedHeight(header_height)
            
            # Resume table updates
            self.table.setUpdatesEnabled(True)
            
            # テーブルの更新を促す
            self.table.horizontalHeader().updateGeometry()
            self.table.horizontalHeader().viewport().update()
            self.table.repaint()
            
            # 各列の更新後の表示状態をログ出力
            for i in range(self.table.columnCount()):
                logger.debug(f"更新後の列 {i} ({self.get_column_name(i)}) の状態: hidden={self.table.isColumnHidden(i)}")

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
