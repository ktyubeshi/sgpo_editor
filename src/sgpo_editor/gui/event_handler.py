"""イベント処理モジュール

このモジュールは、GUIイベントの処理とハンドリングに関する機能を提供します。
"""

import logging
from typing import Callable, Dict, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.types import EntryModelMap

if TYPE_CHECKING:
    from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class EventHandler(QObject):
    """イベント処理クラス

    GUIイベントを処理し、エントリの選択、表示、編集、更新に関するロジックを提供します。

    ファサードとの役割分担:
        ファサード導入後のEventHandlerの主な役割:
        1. テーブル操作に関連するイベント処理（セル選択、エントリ選択時のUI更新等）
        2. エントリエディタとの直接的なインタラクション処理
        3. キャッシュ管理とパフォーマンス最適化

        ファサードに委譲された責務:
        1. EntryListFacade: テーブル表示と更新、エントリリスト操作のカプセル化
        2. EntryEditorFacade: エントリ編集操作のカプセル化

        注意: このクラスは段階的にファサードに機能を移行中のため、一部の機能はファサードと
        重複している場合があります。今後の開発では、以下の方針でリファクタリングを検討:
        - ファサードを使った実装に一本化し、EventHandlerの役割を純粋なイベント連携に限定
        - または、EventHandlerを完全にファサードに統合し、このクラスを廃止

    キャッシュ管理:
        キャッシュ管理は EntryCacheManager に集約されました。
        このクラスはUIイベントと EntryCacheManager や Facade を連携させる役割を担います。

        注意:
            リファクタリング進行中のため、一部古いコメントが残っている可能性があります。
    """

    entry_updated = Signal(int)  # エントリが更新されたとき（引数：エントリ番号）
    entry_selected = Signal(int)  # エントリが選択されたとき（引数：エントリ番号）

    def __init__(
        self,
        table: QTableWidget,
        entry_editor: EntryEditor,
        entry_cache_manager: EntryCacheManager,
        get_current_po: Callable[[], Optional[ViewerPOFileRefactored]],
        show_status: Callable[[str, int], None],
    ) -> None:
        """初期化

        Args:
            table: テーブルウィジェット
            entry_editor: エントリエディタ
            entry_cache_manager: EntryCacheManager instance
            get_current_po: 現在のPOファイルを取得するコールバック
            show_status: ステータス表示用コールバック
        """
        super().__init__()
        self.table = table
        self.entry_editor = entry_editor
        self.entry_cache_manager = entry_cache_manager
        self._get_current_po = get_current_po
        self._show_status = show_status
        self._last_processed_row = -1
        self._drag_timer = QTimer()
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._process_drag_selection)
        self._pending_row = -1

        # プリフェッチタイマー
        self._prefetch_timer = QTimer()
        self._prefetch_timer.setSingleShot(True)

        # 接続をセットアップ
        self.setup_connections()

    def setup_connections(self) -> None:
        """イベント接続をセットアップする"""
        logger.debug("EventHandler.setup_connections: 開始")
        # テーブルの選択変更シグナル (EntryListFacadeに移行)
        # self.table.itemSelectionChanged.connect(self._on_selection_changed)
        # テーブルのダブルクリックシグナル
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        # エントリエディタの適用ボタンクリックシグナル (EntryEditorFacadeに移行)
        # self.entry_editor.apply_clicked.connect(self._on_apply_clicked)
        # エントリエディタのテキスト変更シグナル (EntryEditorFacadeに移行)
        # self.entry_editor.text_changed.connect(self._on_text_changed)
        # テーブルのセル選択/エンターシグナル (これもFacadeで処理されるべき)
        # self.table.cellClicked.connect(self._on_cell_selected)
        # self.table.cellEntered.connect(self._on_cell_entered)
        logger.debug("EventHandler.setup_connections: 完了")

    def _on_cell_selected(self, row: int, column: int) -> None:
        """セルがクリックされたときの処理 (現在はEntryListFacadeが処理)"""
        # self._update_detail_view(row) # Facadeに処理を移譲
        pass

    def _on_cell_entered(self, row: int, column: int) -> None:
        """セルにマウスが入ったときの処理 (現在はEntryListFacadeが処理)"""
        # マウスドラッグ中かどうかを確認
        # if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
        #     if row != self._last_processed_row:
        #         self._pending_row = row
        #         if not self._drag_timer.isActive():
        #             self._drag_timer.start(17)
        pass

    def _process_drag_selection(self) -> None:
        """ドラッグ選択処理の遅延実行 (現在はEntryListFacadeが処理)"""
        # if self._pending_row >= 0 and self._pending_row != self._last_processed_row:
        #     # Facadeのメソッドを呼び出すように変更する想定だったが、そもそも不要
        #     # key = self.entry_cache_manager.get_key_for_row(self._pending_row)
        #     # if key:
        #     #     # EntryEditorFacadeのインスタンスが必要
        #     #     pass # self.entry_editor_facade.display_entry_by_key(key)
        #     self._last_processed_row = self._pending_row
        pass

    def _start_prefetch_timer(self):
        """プリフェッチタイマーを開始する"""
        if not self._prefetch_timer.isActive():
            self._prefetch_timer.start(10)

    def _on_item_double_clicked(self, item) -> None:
        """テーブルアイテムがダブルクリックされたときの処理"""
        row = item.row()
        # self._update_detail_view(row) # Facadeに処理を移譲
        key = self.entry_cache_manager.get_key_for_row(row)
        if key:
            current_po = self._get_current_po()
            if current_po:
                entry = current_po.get_entry_by_key(key)
                # ここでレビューダイアログ表示などのアクション？
                # TODO: ダブルクリック時のアクションを定義する
                logger.debug(f"EventHandler: Item double clicked: row={row}, key={key}")
                # self.entry_editor_facade.show_review_dialog() # 例

    def _on_entry_changed(self, entry_number: int) -> None:
        """エントリが変更されたときの処理 (現在は未使用のはず)"""
        # テーブルの現在の行データを使用して、DBに再クエリせずに目的のエントリを見つける
        # for row in range(self.table.rowCount()):
        #     item = self.table.item(row, 0)
        #     if item is None:
        #         continue
        #     key = item.data(Qt.ItemDataRole.UserRole)
        #     if key in self.entry_cache_manager.cache: # CacheManagerのAPI変更を反映する必要あり
        #         entry = self.entry_cache_manager.get_entry_from_cache(key)
        #         if entry and hasattr(entry, "position") and entry.position == entry_number:
        #             self.table.selectRow(row)
        #             break
        pass

    def change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する (EntryEditorFacadeに委譲済み)"""
        # self.entry_editor.change_layout(layout_type)
        pass # 実処理はFacadeで行う

    # get_current_entry メソッド全体を削除
    # def get_current_entry(self) -> Optional["EntryModel"]:
    #    ...

    # clear_cache メソッド全体を削除 (CacheManagerへ移行済み)
    # def clear_cache(self) -> None:
    #    ...
