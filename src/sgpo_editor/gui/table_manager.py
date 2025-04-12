from __future__ import annotations

import json
import logging
from typing import Callable, Dict, List, Optional, Set, Union

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.models.entry import EntryModel

"""Table Management Module

This module provides functionality for displaying and managing table entries from PO files.
"""

# 循環インポートを避けるために型アノテーションを文字列で指定
# POEntry = Any  # 実際の型は循環インポートを避けるため文字列で指定

logger = logging.getLogger(__name__)

# 列名とインデックスのマッピング
COLUMN_MAP = {
    0: "position",
    1: "context",
    2: "msgid",
    3: "msgstr",
    4: "status",
    5: "score",
}

# 逆引きマップを追加
COLUMN_INDEX_MAP: Dict[str, int] = {v: k for k, v in COLUMN_MAP.items()}


class TableManager:
    """Table Management Class"""

    def __init__(
        self,
        table: QTableWidget,
        entry_cache_manager: EntryCacheManager,
        get_current_po: Optional[Callable[[], Optional[ViewerPOFileRefactored]]] = None,
        sort_request_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Initialize

        Args:
            table: Target table widget to manage
            entry_cache_manager: EntryCacheManager instance
            get_current_po: Callback to get the current PO file
            sort_request_callback: Callback to handle table sort requests
        """
        self.table = table
        self.entry_cache_manager = entry_cache_manager
        self._current_sort_column: int = 0
        self._current_sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
        self._current_filter_text: str = ""
        self._current_search_text: str = ""
        self._get_current_po = get_current_po
        # 列幅の初期値を設定
        self._default_column_widths = [80, 120, 200, 200, 100, 80]
        # ソート要求コールバックを保存
        self._sort_request_callback = sort_request_callback
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

        # デフォルトのソート状態は ViewerPOFileRefactored が管理する
        # self._current_sort_column = 0  # Entry number column
        # self._current_sort_order = Qt.SortOrder.AscendingOrder
        # self.table.horizontalHeader().setSortIndicator(
        #     self._current_sort_column, self._current_sort_order
        # )
        
        # ソート要求シグナル
        # self.sort_criteria_changed = Signal(str, str) # PyQtシグナルは使えない

    def _on_header_clicked(self, logical_index: int) -> None:
        """Process header click event
        
        ヘッダーがクリックされたときにソート要求を通知します。
        実際のソート処理は ViewerPOFileRefactored に移譲されました。
        """
        # Get current sort order
        current_column_name = self.get_column_name(logical_index)
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

        # Update sort indicator in the UI
        self.table.horizontalHeader().setSortIndicator(logical_index, new_order)
        self._current_sort_column = logical_index
        self._current_sort_order = new_order

        # ソート順序を文字列に変換
        sort_order_str = "ASC" if new_order == Qt.SortOrder.AscendingOrder else "DESC"
        
        # 対応する ViewerPOFileRefactored の列名を取得
        # このマッピングは要確認
        column_name_map = {
            "Entry Number": "position",
            "msgid": "msgid",
            "msgstr": "msgstr",
            "Status": "status", # Status は EntryModel の computed field なので直接ソートできない可能性あり
            "Score": "score",
        }
        sort_column_name = column_name_map.get(current_column_name, "position")

        # ソート要求を通知 (コールバックを使用)
        po_file = self._get_current_po() if self._get_current_po else None
        if po_file:
            # 直接 ViewerPOFile のメソッドを呼ぶのではなく、
            # MainWindow 経由で処理を依頼する
            # 例: self.sort_requested.emit(sort_column_name, sort_order_str)
            # ここでは MainWindow 側の処理に任せるためコメントアウト
            # po_file.set_sort_criteria(sort_column_name, sort_order_str)
            # self.update_table(po_file.get_filtered_entries(update_filter=True))
            # テーブル更新トリガーは MainWindow が行う想定
            logger.debug(f"TableManager: ソート要求 - Column: {sort_column_name}, Order: {sort_order_str}")
            # ここでシグナルを発行するか、MainWindowに通知する仕組みが必要
            # if hasattr(self.table.parent(), "request_table_sort_update"): # MainWindowにメソッドがあると仮定
            #     self.table.parent().request_table_sort_update(sort_column_name, sort_order_str)
            # else:
            #     logger.warning("MainWindow に request_table_sort_update メソッドが見つかりません。")
            # 保存されたコールバックを呼び出す
            if self._sort_request_callback:
                self._sort_request_callback(sort_column_name, sort_order_str)
            else:
                logger.warning("ソート要求コールバックが設定されていません。")

    def update_table(
        self,
        entries: List[EntryModel],
        criteria: Optional[SearchCriteria] = None,
    ) -> List[EntryModel]:
        """テーブルを更新する

        Args:
            entries: 表示するエントリのリスト (既にソート済みであること)
            criteria: 検索条件 (フィルタテキストとキーワードを含む)

        Returns:
            表示されたエントリのリスト

        キャッシュ管理:
            このメソッドはキャッシュを直接操作しません。
            キャッシュの更新は EntryCacheManager が担当します。
            行とキーのマッピングは update_table 呼び出し前に
            EntryCacheManager.add_row_key_mapping で設定されている想定です。
        """
        logger.debug(f"TableManager.update_table: 開始 (表示予定エントリ数: {len(entries)}件)")

        # 現在の列の表示/非表示状態を内部状態と同期
        self._sync_column_visibility()

        # 引数の entries が空の場合も想定
        if not entries:
            logger.debug("TableManager.update_table: エントリが空のため、テーブルをクリア")
            self.table.setRowCount(0)
            return []

        # 現在のフィルタ条件を保存 (これは維持)
        if criteria:
            self._current_filter_text = criteria.filter
            self._current_search_text = criteria.filter_keyword

        # ソート処理は不要 (sorted_entries = entries をそのまま使う)
        sorted_entries = entries
        logger.debug(f"TableManager.update_table: 表示するソート済みエントリ数: {len(sorted_entries)}件")

        # テーブルの更新を一時停止して効率的に更新
        logger.debug("TableManager.update_table: テーブル更新を一時停止")
        self.table.setUpdatesEnabled(False)
        try:
            # テーブルを更新
            logger.debug("TableManager.update_table: テーブル内容を更新")
            self._update_table_contents(sorted_entries) # ここでソート済みリストを渡す
            logger.debug("TableManager.update_table: テーブル内容の更新完了")
        finally:
            # 必ず更新を再開
            logger.debug("TableManager.update_table: テーブル更新を再開")
            self.table.setUpdatesEnabled(True)
            # 表示を強制的に更新
            logger.debug("TableManager.update_table: 表示を強制的に更新")
            self.table.viewport().update()
            # テーブルのレイアウトを更新
            logger.debug("TableManager.update_table: テーブルのレイアウトを更新")
            self.table.updateGeometry()
            # テーブルを再描画
            logger.debug("TableManager.update_table: テーブルを再描画")
            self.table.repaint()

        logger.debug(f"TableManager.update_table: 完了: {len(sorted_entries)}件表示")

        return sorted_entries

    def _on_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ) -> None:
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
                        if (
                            isinstance(column_count, int)
                            and 0 <= col_idx < column_count
                        ):
                            # 最小幅を10ピクセルとして設定
                            actual_width = max(int(width), 10)
                            self.table.setColumnWidth(col_idx, actual_width)
                            logger.debug(
                                f"列 {col_idx} ({self.get_column_name(col_idx)}) の幅を設定: {actual_width}px"
                            )
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
        column_count = self.table.columnCount()
        if not isinstance(column_count, int):
            logger.warning("TableManager._apply_default_column_widths: 列数が整数ではありません。処理をスキップします。")
            return

        for i, width in enumerate(self._default_column_widths):
            if i < column_count:
                # 幅【0にしないように最小値を10に設定
                actual_width = max(width, 10)
                self.table.setColumnWidth(i, actual_width)
                logger.debug(
                    f"列 {i} ({self.get_column_name(i)}) のデフォルト幅を設定: {actual_width}px"
                )

    def toggle_column_visibility(self, column_index: int) -> None:
        """列の表示/非表示を切り替える

        引数の列インデックスに対応する列の表示/非表示状態を反転させます。
        変更は設定ファイルに保存され、アプリケーション再起動後も維持されます。

        Args:
            column_index: 列インデックス
        """
        column_count = self.table.columnCount()
        if not isinstance(column_count, int):
            logger.warning("TableManager.toggle_column_visibility: 列数が整数ではありません。処理をスキップします。")
            return

        if 0 <= column_index < column_count:
            # 現在の状態を取得
            is_hidden = self.table.isColumnHidden(column_index)

            # 状態を反転
            new_hidden_state = not is_hidden

            # 内部の_hidden_columnsセットを更新
            if new_hidden_state:
                self._hidden_columns.add(column_index)
                logger.debug(
                    f"列 {column_index} ({self.get_column_name(column_index)}) を非表示に設定します"
                )
            else:
                self._hidden_columns.discard(column_index)
                logger.debug(
                    f"列 {column_index} ({self.get_column_name(column_index)}) を表示に設定します"
                )

            # 設定を保存
            self._save_column_visibility()

            # すべての列の表示/非表示状態を再確認して適用（同期を確保）
            self._apply_column_visibility()

            # テーブルの更新を最適化
            self.table.setUpdatesEnabled(False)
            try:
                # テーブルの視覚的更新を確実に行う
                self.table.horizontalHeader().updateGeometry()
                self.table.viewport().update()
                self.table.updateGeometry()
                self.table.repaint()
            finally:
                # 必ず更新を再開
                self.table.setUpdatesEnabled(True)

            # デバッグ情報
            logger.debug(
                f"列 {column_index} ({self.get_column_name(column_index)}) の表示状態を切り替えました: {'非表示' if new_hidden_state else '表示'}"
            )

            # 実際に適用されたかを検証
            actual_state = self.table.isColumnHidden(column_index)
            if actual_state != new_hidden_state:
                logger.warning(
                    f"列 {column_index} の表示状態が期待通りに設定されていません。期待値: {new_hidden_state}, 実際: {actual_state}"
                )

    def is_column_visible(self, column_index: int) -> bool:
        """指定された列が表示されているか確認する

        Args:
            column_index: 列インデックス

        Returns:
            列が表示されている場合はTrue、非表示の場合はFalse
        """
        # 列インデックスの範囲をチェック
        column_count = self.table.columnCount()
        if not isinstance(column_count, int) or not (0 <= column_index < column_count):
            return False

        return not self.table.isColumnHidden(column_index)

    def _sync_column_visibility(self) -> None:
        """内部の非表示列セットとGUIの列表示状態を同期する"""
        logger.debug("TableManager._sync_column_visibility: 開始")
        self._hidden_columns = set()
        column_count = self.table.columnCount()
        if not isinstance(column_count, int):
            logger.warning("TableManager._sync_column_visibility: 列数が整数ではありません。処理をスキップします。")
            return

        for i in range(column_count):
            if self.table.isColumnHidden(i):
                self._hidden_columns.add(i)

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
        """現在の列数を取得する

        Returns:
            列数
        """
        # デフォルト値は0列
        column_count = self.table.columnCount()
        if not isinstance(column_count, int):
            logger.warning("TableManager.get_column_count: 列数が整数ではありません。0を返します。")
            return 0
        return column_count

    def _save_column_visibility(self) -> None:
        """列の表示/非表示設定を保存する"""
        settings = QSettings("SGPOEditor", "TableSettings")
        # 非表示の列インデックスをリストとして保存
        hidden_columns = list(self._hidden_columns)
        settings.setValue("hidden_columns", json.dumps(hidden_columns))
        logger.debug(f"保存された非表示列: {hidden_columns}")

    def _apply_column_visibility(self) -> None:
        """現在の非表示列セットをテーブルに適用"""
        # self._hidden_columns に基づいて、テーブルの列の表示/非表示を設定
        logger.debug(f"TableManager._apply_column_visibility: 非表示列を適用: {self._hidden_columns}")
        column_count = self.table.columnCount()
        if not isinstance(column_count, int):
            logger.warning("TableManager._apply_column_visibility: 列数が整数ではありません。処理をスキップします。")
            return

        for i in range(column_count):
            is_hidden = i in self._hidden_columns
            self.table.setColumnHidden(i, is_hidden)

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

    def _update_table_contents(self, entries: List[EntryModel]) -> None:
        """テーブルの内容を更新する

        Args:
            entries: 表示するエントリのリスト
        """
        logger.debug(f"TableManager._update_table_contents: {len(entries)}件のエントリでテーブル内容を更新開始")
        self.table.setUpdatesEnabled(False)
        try:
            # 行数を一度に設定
            self.table.setRowCount(len(entries))
            
            # テーブル内容をクリア (setRowCountですでに行はクリアされるため不要な場合が多い)
            # self.table.clearContents()

            # 各行のデータを設定
            for row, entry in enumerate(entries):
                # 各列のアイテムを作成・設定
                item0 = QTableWidgetItem(str(entry.position))
                item0.setData(Qt.ItemDataRole.UserRole, entry.key) # キーを行データとして保存
                item0.setFlags(item0.flags() & ~Qt.ItemFlag.ItemIsEditable) # 編集不可
                self.table.setItem(row, 0, item0)

                item1 = QTableWidgetItem(entry.msgctxt or "")
                item1.setFlags(item1.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, item1)

                item2 = QTableWidgetItem(entry.msgid or "")
                item2.setFlags(item2.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, item2)

                item3 = QTableWidgetItem(entry.msgstr or "")
                # msgstr 列のみ編集可能とする場合
                # item3.setFlags(item3.flags() | Qt.ItemFlag.ItemIsEditable)
                item3.setFlags(item3.flags() & ~Qt.ItemFlag.ItemIsEditable) # 一旦編集不可
                self.table.setItem(row, 3, item3)

                # ステータス列
                status = entry.get_status()
                item4 = QTableWidgetItem(status)
                item4.setFlags(item4.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # 色付け
                # item4.setForeground(self._get_status_color(status))
                self.table.setItem(row, 4, item4)
                
                # スコア列
                score_text = f"{entry.score:.2f}" if entry.score is not None else "N/A"
                item5 = QTableWidgetItem(score_text)
                item5.setFlags(item5.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 5, item5)

                # 行とキーのマッピングを CacheManager に登録
                self.entry_cache_manager.add_row_key_mapping(row, entry.key)

            # 列幅の自動調整 (必要に応じて)
            # self.table.resizeColumnsToContents()

            logger.debug(f"TableManager._update_table_contents: テーブル内容更新完了")
        finally:
            self.table.setUpdatesEnabled(True)

    def _get_status_color(self, status: str) -> QColor:
        """ステータスに基づいて色を取得する"""
        # このメソッドは実装が必要です。
        # 現在の実装は単に黒色を返すだけです。
        return QColor(0, 0, 0)

    def _get_filter_conditions(self) -> tuple[Optional[str], Optional[str]]:
        """現在のフィルタ条件を取得

        Returns:
            フィルタテキストとキーワードのタプル
        """
        return (self._current_filter_text, self._current_search_text)

    def get_display_entries(self) -> List[str]:
        """Return keys of displayed entries (Now managed by CacheManager)

        Returns:
            List of entry keys currently displayed
        """
        # return self._display_entries
        # このメソッドは CacheManager へのアクセス方法が決まるまで未実装とするか、
        # CacheManager から取得するように変更する必要がある。
        # 現状は空リストを返す。
        logger.warning("TableManager.get_display_entries is deprecated, use EntryCacheManager")
        return []

    def select_row(self, row: int) -> None:
        """Select specified row

        Args:
            row: Row to select
        """
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.table.setCurrentCell(row, 0)

    def get_key_at_row(self, row: int) -> Optional[str]:
        """Return the entry key at the specified row index.

        Args:
            row: Row index

        Returns:
            Entry key (None if not exists)
        """
        # if 0 <= row < len(self._display_entries):
        #     return self._display_entries[row]
        # return None
        return self.entry_cache_manager.get_key_for_row(row)

    def find_row_by_key(self, key: str) -> int:
        """Find the row index corresponding to the given entry key.

        Args:
            key: Entry key

        Returns:
            Row index (-1 if not found)
        """
        # EntryCacheManager のメソッドを使用
        return self.entry_cache_manager.find_row_by_key(key)

    def get_column_index(self, column_name: str) -> Optional[int]:
        """列名から列インデックスを取得する"""
        return self.COLUMN_INDEX_MAP.get(column_name)
