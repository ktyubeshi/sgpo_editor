"""エントリリストのファサードモジュール

このモジュールは、エントリリスト表示に関連する操作をカプセル化するファサードクラスを提供する。
複雑なシグナルフローを単純化し、責務を明確にすることを目的としている。
"""

import logging
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtWidgets import QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager  # 新APIに準拠

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.widgets.search import SearchWidget

logger = logging.getLogger(__name__)


class EntryListFacade(QObject):
    """エントリリスト表示に関連する操作をカプセル化するファサードクラス

    このクラスは、エントリリストの表示、検索、選択などの操作に関するシンプルなインターフェイスを提供します。
    内部的には TableManager および SearchWidget と連携して動作します。

    責務:
        1. テーブル表示の更新と管理
        2. エントリの検索とフィルタリング
        3. エントリ選択状態の管理
        4. ViewerPOFileとテーブル表示の同期

    パターン適用:
        - ファサードパターン: 複雑なテーブル操作とPOファイルアクセスに対する
          シンプルなインターフェイスを提供
        - オブザーバーパターン: テーブル選択やフィルタ変更をシグナルで通知

    EventHandlerとの関係:
        - EventHandlerのテーブル関連処理をこのクラスに段階的に移行
        - EventHandlerが行レベルのイベント処理に集中するのに対し、
          このクラスはテーブル全体の状態管理と操作に特化

    キャッシュ連携:
        - ViewerPOFileのキャッシュ (_force_filter_update) と連携し、
          テーブル更新時にフィルタリング結果を最新化
        - TableManagerの内部キャッシュ (_entry_cache) を活用して表示パフォーマンスを最適化

    改善可能点:
        - テーブル状態の永続化 (選択位置、スクロール位置等)
        - 非同期データロードと表示の分離
        - 列の表示設定とカスタマイズのインターフェース統合
    """

    # シグナル定義
    entry_selected = Signal(int)  # エントリ選択時に発行。引数はエントリ番号
    filter_changed = Signal()  # フィルタ条件が変更された時に発行

    def __init__(
        self,
        table: QTableWidget,
        table_manager: TableManager,
        search_widget: SearchWidget,
        entry_cache_manager: EntryCacheManager,
        get_current_po: Callable[[], Optional[ViewerPOFile]],
    ) -> None:
        """初期化

        Args:
            table: テーブルウィジェット
            table_manager: テーブル管理クラス
            search_widget: 検索ウィジェット
            entry_cache_manager: エントリキャッシュマネージャー
            get_current_po: 現在のPOファイルを取得する関数
        """
        super().__init__()
        self._table = table
        self._table_manager = table_manager
        self._search_widget = search_widget
        self._entry_cache_manager = entry_cache_manager
        self._get_current_po = get_current_po

        # プリフェッチタイマー
        self._prefetch_timer = QTimer()
        self._prefetch_timer.setSingleShot(True)
        self._prefetch_timer.timeout.connect(self._prefetch_entries)

        # テーブルのセル選択シグナルを接続
        self._table.cellClicked.connect(self._on_cell_clicked)

        # テーブルのスクロールイベントを接続してプリフェッチをトリガー
        self._table.verticalScrollBar().valueChanged.connect(
            lambda: self._prefetch_timer.start(100)  # スクロール完了後にプリフェッチ
        )

        # 検索ウィジェットのシグナルを接続 (update_filter は不要になり、直接 update_table を呼ぶ)
        self._search_widget.filter_changed.connect(
            self.update_table
        )  # update_table に接続

    def update_table(self) -> None:
        import traceback
        logger.debug("EntryListFacade.update_table called. Stack trace:\n%s", traceback.format_stack())
        logger.debug("EntryListFacade.update_table: Criteria before retrieval: %s", self._search_widget.get_search_criteria() if self._search_widget else 'No search widget')
        """テーブルを最新の状態に更新する

        POファイルからフィルタリング/ソートされたエントリを取得し、
        キャッシュマッピングを更新し、テーブルを表示し、ソートインジケータを更新する。
        """
        logger.debug("EntryListFacade.update_table: 開始")
        current_po = self._get_current_po()
        if not current_po:
            logger.debug(
                "EntryListFacade.update_table: POファイルが読み込まれていないため、テーブル更新をスキップします"
            )
            # テーブルクリア処理を追加しても良いかもしれない
            self._table_manager.update_table([], None)  # 空リストでクリア
            return

        try:
            # フィルタ条件を取得
            criteria = self._search_widget.get_search_criteria()
            logger.debug(f"EntryListFacade.update_table: フィルタ条件: {criteria}")

            # POファイルからフィルタリング＆ソート済みのエントリを取得
            # get_filtered_entries は内部で現在のソート条件を使用する
            logger.debug("EntryListFacade.update_table: POファイルからエントリ取得開始")

            # criteriaから個別のパラメータを取り出してget_filtered_entriesを呼び出す
            sorted_entries = current_po.get_filtered_entries(
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword,
                match_mode=criteria.match_mode,
            )

            logger.debug(
                f"EntryListFacade.update_table: 取得したエントリ数: {len(sorted_entries)}件"
            )

            # 新キャッシュ設計：TableManagerで行マッピングを管理
            logger.debug(
                "EntryListFacade.update_table: TableManagerの行マッピングを更新（新キャッシュ設計）"
            )
            self._table_manager.update_row_key_mappings(sorted_entries)

            # テーブルを更新（ソート済みリストとフィルタ条件を渡す）
            logger.debug(
                "EntryListFacade.update_table: TableManagerのupdate_table呼び出し"
            )
            displayed_entries = self._table_manager.update_table(
                sorted_entries, criteria
            )
            logger.debug(
                f"EntryListFacade.update_table: テーブル更新完了: {len(displayed_entries)}件表示"
            )

            # ソートインジケータを更新
            sort_column_name = current_po.get_sort_column()
            sort_order_str = current_po.get_sort_order()
            logger.debug(
                f"EntryListFacade.update_table: 現在のソート条件: column='{sort_column_name}', order='{sort_order_str}'"
            )
            logical_index = self._table_manager.get_column_index(sort_column_name)
            if logical_index is not None:
                qt_sort_order = (
                    Qt.SortOrder.AscendingOrder
                    if sort_order_str == "ASC"
                    else Qt.SortOrder.DescendingOrder
                )
                logger.debug(
                    f"EntryListFacade.update_table: ソートインジケータを更新: index={logical_index}, order={qt_sort_order}"
                )
                self._table.horizontalHeader().setSortIndicator(
                    logical_index, qt_sort_order
                )
            else:
                logger.warning(
                    f"EntryListFacade.update_table: ソート列名 '{sort_column_name}' に対応するインデックスが見つかりません"
                )

            # テーブルの表示を強制的に更新 (必要に応じて維持)
            logger.debug("EntryListFacade.update_table: テーブルの表示を強制的に更新")
            self._table.viewport().update()
            self._table.updateGeometry()
            self._table.repaint()

            # イベントループを処理して表示を更新 (必要な場合)
            # logger.debug("EntryListFacade.update_table: イベントループを処理して表示を更新")
            # QApplication.processEvents()

            logger.debug("EntryListFacade.update_table: 完了")

        except Exception as e:
            logger.error(f"EntryListFacade.update_table: エラー発生 {e}", exc_info=True)
            # 必要に応じてステータスバー等でユーザーに通知

    def select_entry_by_key(self, key: str) -> bool:
        """指定されたキーを持つエントリをテーブルで選択する

        Args:
            key: 検索するエントリのキー

        Returns:
            選択成功時はTrue、失敗時はFalse
        """
        if not key:
            logger.debug(f"キーが空のため選択できません: {key}")
            return False

        logger.debug(f"キーによるエントリ選択: {key}")
        try:
            # テーブル内の全ての行を確認
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)  # 最初の列に対するアイテムを取得
                if item is None:
                    continue

                item_key = item.data(Qt.ItemDataRole.UserRole)
                if item_key == key:
                    logger.debug(f"エントリを選択: 行={row}, キー={key}")
                    # 行選択
                    self._table.selectRow(row)
                    # ビューをスクロールして選択した行を表示
                    self._table.scrollTo(self._table.model().index(row, 0))
                    return True

            logger.debug(f"キー {key} を持つエントリがテーブルに見つかりませんでした")
            return False
        except Exception as e:
            logger.error(f"エントリ選択エラー: {e}")
            return False

    def get_selected_entry_key(self) -> Optional[str]:
        """現在選択されているエントリのキーを取得する

        Returns:
            選択中のエントリのキー、選択がない場合はNone
        """
        if not self._table.selectionModel().hasSelection():
            return None

        selection_rows = self._table.selectionModel().selectedRows()
        if not selection_rows:
            return None

        current_row = selection_rows[0].row()
        item = self._table.item(current_row, 0)
        if not item:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def update_table_and_reselect(self, key: str) -> None:
        """テーブルを更新し、指定されたキーのエントリを再選択する

        Args:
            key: 再選択するエントリのキー
        """
        logger.debug(f"EntryListFacade.update_table_and_reselect: 開始 key={key}")
        self.update_table()  # テーブルを更新
        if key:
            logger.debug(f"EntryListFacade.update_table_and_reselect: 再選択 key={key}")
            self.select_entry_by_key(key)  # キーで再選択
        logger.debug("EntryListFacade.update_table_and_reselect: 完了")

    def _on_cell_clicked(self, row: int, column: int) -> None:
        """テーブルのセルがクリックされた時の処理

        Args:
            row: クリックされた行
            column: クリックされた列
        """
        logger.debug(f"EntryListFacade._on_cell_clicked: 行={row}, 列={column}")

        item = self._table.item(row, 0)
        if not item:
            logger.debug("EntryListFacade._on_cell_clicked: アイテムが取得できない")
            return

        key = item.data(Qt.ItemDataRole.UserRole)
        logger.debug(f"EntryListFacade._on_cell_clicked: キー={key}")

        # POファイルからエントリを取得
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("EntryListFacade._on_cell_clicked: POファイルが取得できない")
            return

        try:
            entry = current_po.get_entry_by_key(key)
            if entry and hasattr(entry, "position"):
                logger.debug(
                    f"EntryListFacade._on_cell_clicked: エントリ位置={entry.position}のシグナルを発行"
                )
                self.entry_selected.emit(entry.position)
                logger.debug("EntryListFacade._on_cell_clicked: シグナル発行完了")
            else:
                logger.debug(
                    "EntryListFacade._on_cell_clicked: エントリが取得できないか、positionがない"
                )
        except Exception as e:
            logger.error(
                f"EntryListFacade._on_cell_clicked: エラー発生 {e}", exc_info=True
            )

    def toggle_column_visibility(self, column_index: int) -> None:
        """列の表示/非表示を切り替える

        Args:
            column_index: 列インデックス
        """
        self._table_manager.toggle_column_visibility(column_index)

    def is_column_visible(self, column_index: int) -> bool:
        """列の表示状態を取得する

        Args:
            column_index: 列インデックス

        Returns:
            列が表示されているかどうか
        """
        return self._table_manager.is_column_visible(column_index)

    def _prefetch_entries(self) -> None:
        """現在表示されている行周辺のエントリをプリフェッチする"""
        try:
            current_po = self._get_current_po()
            if not current_po or not current_po.cache_manager:
                return

            # 現在表示されている行の範囲を取得
            scroll_bar = self._table.verticalScrollBar()
            scroll_value = scroll_bar.value()

            # テーブルの表示領域の行数を推定
            visible_height = self._table.viewport().height()
            row_height = self._table.rowHeight(0) if self._table.rowCount() > 0 else 20
            visible_rows = max(1, visible_height // row_height)

            # スクロール位置から表示されている行の範囲を計算
            first_visible_row = max(
                0, scroll_value // row_height - 5
            )  # 上に余裕を持たせる
            last_visible_row = min(
                self._table.rowCount() - 1, first_visible_row + visible_rows + 10
            )  # 下にも余裕を持たせる

            # 表示されている行のエントリキーを収集（キャッシュにないもののみ）
            keys_to_prefetch = []
            for row in range(first_visible_row, last_visible_row + 1):
                if row < 0 or row >= self._table.rowCount():
                    continue

                item = self._table.item(row, 0)
                if item is None:
                    continue

                key = item.data(Qt.ItemDataRole.UserRole)
                # CacheManager を ViewerPOFile から取得して使用
                if key and not current_po.cache_manager.exists_entry(key):
                    # プリフェッチ中でもないことを確認
                    if not current_po.cache_manager.is_key_being_prefetched(key):
                        keys_to_prefetch.append(key)

            if not keys_to_prefetch:
                return

            logger.debug(
                f"EntryListFacade: プリフェッチ対象: {len(keys_to_prefetch)}件 (表示範囲: {first_visible_row}-{last_visible_row})"
            )

            # プリフェッチをバックグラウンドで開始
            self._entry_cache_manager.prefetch_entries(
                keys_to_prefetch,
                fetch_callback=current_po.get_entries_by_keys,  # ViewerPOFile のメソッドを渡す
            )

        except Exception as e:
            logger.exception(f"EntryListFacade: プリフェッチ中にエラー: {e}")
