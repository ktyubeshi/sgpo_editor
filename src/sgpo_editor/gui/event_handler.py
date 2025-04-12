"""イベント処理モジュール

このモジュールは、GUIイベントの処理とハンドリングに関する機能を提供します。
注意: このクラスはファサードパターンに移行中であり、徐々に廃止される予定です。
"""

import logging
from typing import Callable, Dict, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.types import EntryModelMap

if TYPE_CHECKING:
    from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class EventHandler(QObject):
    """イベント処理クラス

    注意: このクラスはファサードパターンに移行中であり、将来的には完全に廃止される予定です。
    新しいコードではEntryListFacadeとEntryEditorFacadeを使用してください。

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

    # シグナル定義（互換性のために保持）
    entry_updated = Signal(int)  # エントリが更新されたとき（引数：エントリ番号）
    entry_selected = Signal(int)  # エントリが選択されたとき（引数：エントリ番号）

    def __init__(
        self,
        table: QTableWidget,
        entry_editor: EntryEditor,
        entry_cache_manager: EntryCacheManager,
        get_current_po: Callable[[], Optional[ViewerPOFile]],
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

        logger.warning("EventHandlerは廃止予定です。新しいコードではEntryListFacadeとEntryEditorFacadeを使用してください。")

    def setup_connections(self) -> None:
        """イベント接続をセットアップする"""
        logger.debug("EventHandler.setup_connections: 開始")
        # テーブルのダブルクリックシグナル
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        logger.debug("EventHandler.setup_connections: 完了")

    def _process_drag_selection(self) -> None:
        """ドラッグ選択処理の遅延実行 (現在は不使用)"""
        pass

    def _on_item_double_clicked(self, item) -> None:
        """テーブルアイテムがダブルクリックされたときの処理"""
        row = item.row()
        key = self.entry_cache_manager.get_key_for_row(row)
        if key:
            current_po = self._get_current_po()
            if current_po:
                entry = current_po.get_entry_by_key(key)
                logger.debug(f"EventHandler: Item double clicked: row={row}, key={key}")

    # 以下の不要メソッドは削除
    # _on_entry_changed
    # change_entry_layout は既に EntryEditorFacade に移行済み
