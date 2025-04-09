"""エントリリストのファサードモジュール

このモジュールは、エントリリスト表示に関連する操作をカプセル化するファサードクラスを提供する。
複雑なシグナルフローを単純化し、責務を明確にすることを目的としている。
"""

import logging
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QTableWidget, QApplication

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
        get_current_po: Callable,
    ) -> None:
        """初期化

        Args:
            table: テーブルウィジェット
            table_manager: テーブル管理クラス
            search_widget: 検索ウィジェット
            get_current_po: 現在のPOファイルを取得する関数
        """
        super().__init__()
        self._table = table
        self._table_manager = table_manager
        self._search_widget = search_widget
        self._get_current_po = get_current_po

        # テーブルのセル選択シグナルを接続
        self._table.cellClicked.connect(self._on_cell_clicked)

        # 検索ウィジェットのシグナルを置き換え
        self._search_widget.filter_changed.connect(self.update_filter)

    def update_table(self) -> None:
        """テーブルを最新の状態に更新する

        このメソッドは、POファイルからフィルタリングされたエントリを取得し、
        テーブルを更新します。

        キャッシュ管理:
            1. POファイルの get_filtered_entries を update_filter=True で呼び出すことで、
               ViewerPOFile 内の _force_filter_update フラグがセットされていてもキャッシュが更新される
            2. TableManager.update_table にエントリリストを渡し、TableManager内の
               _entry_cache が更新される（これはGUIコンポーネント用の一時的なキャッシュ）
            3. 最終的にこのメソッドは ViewerPOFile のキャッシュと TableManager のキャッシュを
               同期させることで、表示の一貫性を保つ役割を果たす

        Note:
            このメソッドはテーブル更新関連のキャッシュを強制的に更新するため、
            パフォーマンスを考慮して必要な時のみ呼び出すこと
        """
        logger.debug("EntryListFacade.update_table: 開始")
        current_po = self._get_current_po()
        if not current_po:
            logger.debug(
                "EntryListFacade.update_table: POファイルが読み込まれていないため、テーブル更新をスキップします"
            )
            return

        try:
            # フィルタ条件を取得
            criteria = self._search_widget.get_search_criteria()
            filter_text = criteria.filter
            filter_keyword = criteria.filter_keyword

            logger.debug(
                f"EntryListFacade.update_table: フィルタ条件 filter_text={filter_text}, filter_keyword={filter_keyword}"
            )

            # POファイルからフィルタ条件に合ったエントリを取得
            logger.debug(
                f"EntryListFacade.update_table: POファイルからエントリ取得開始 _force_filter_update={current_po._force_filter_update}"
            )
            entries = current_po.get_filtered_entries(
                update_filter=True,  # 強制的に更新
                filter_text=filter_text,
                filter_keyword=filter_keyword,
            )

            logger.debug(
                f"EntryListFacade.update_table: 取得したエントリ数: {len(entries)}件"
            )

            # テーブルを更新（フィルタ条件を渡す）
            logger.debug(
                "EntryListFacade.update_table: TableManagerのupdate_table呼び出し"
            )
            sorted_entries = self._table_manager.update_table(entries, criteria)

            logger.debug(
                f"EntryListFacade.update_table: テーブル更新完了: {len(sorted_entries) if sorted_entries else 0}件表示"
            )

            # テーブルの表示を強制的に更新
            logger.debug("EntryListFacade.update_table: テーブルの表示を強制的に更新")
            self._table.viewport().update()
            self._table.updateGeometry()
            self._table.repaint()

            # イベントループを処理して表示を更新
            logger.debug(
                "EntryListFacade.update_table: イベントループを処理して表示を更新"
            )
            QApplication.processEvents()

            logger.debug("EntryListFacade.update_table: 完了")

        except Exception as e:
            logger.error(f"EntryListFacade.update_table: エラー発生 {e}")
            logger.error(f"テーブル更新エラー: {e}")

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

    def update_filter(self) -> None:
        """検索フィルタが変更された時の処理"""
        logger.debug("フィルタ条件が変更されました")
        self.update_table()
        self.filter_changed.emit()

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
