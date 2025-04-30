"""
このモジュールは廃止されました。

以下のファサードに完全に移行しました:
- src/sgpo_editor/gui/facades/entry_list_facade.py
- src/sgpo_editor/gui/facades/entry_editor_facade.py

このファイルは互換性のために一時的に保持されていますが、将来のバージョンで削除されます。
"""

import logging
from typing import Callable, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.entry_editor import EntryEditor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EventHandler(QObject):
    """イベント処理クラス

    注意: このクラスは廃止予定です。新しいコードでは EntryListFacade と EntryEditorFacade を使用してください。
    このクラスは後方互換性のために維持されていますが、将来のバージョンで削除される予定です。

    ファサードパターンへの移行:
    - EntryListFacade: テーブル表示と更新、エントリリスト操作
    - EntryEditorFacade: エントリ編集操作
    """

    # シグナル定義（互換性のために保持）
    entry_updated = Signal(str)  # エントリが更新されたとき（引数：エントリキー）
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

        # 後方互換性のために使用しなくなったタイマーを保持
        self._drag_timer = QTimer()
        self._drag_timer.setSingleShot(True)

        logger.warning(
            "EventHandlerは廃止予定です。新しいコードではEntryListFacadeとEntryEditorFacadeを使用してください。"
        )

    def setup_connections(self) -> None:
        """イベント接続をセットアップする

        注意: このメソッドは後方互換性のために維持されていますが、
        新しいコードでは EntryListFacade と EntryEditorFacade を使用してください。
        """
        logger.debug("EventHandler.setup_connections: このクラスは廃止予定です")
        # Connect table cell change to handler
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

    def _on_item_double_clicked(self, item) -> None:
        """テーブルアイテムがダブルクリックされたときの処理

        注意: このメソッドは後方互換性のために維持されていますが、
        新しいコードでは EntryListFacade を使用してください。
        """
        row = item.row()
        key = self.entry_cache_manager.get_key_for_row(row)
        if key:
            logger.debug(
                f"EventHandler: Item double clicked: row={row}, key={key} (廃止予定のメソッド)"
            )

    def _on_current_cell_changed(self, currentRow: int, currentColumn: int, previousRow: int, previousColumn: int) -> None:
        """テーブルの選択セルが変更されたときの処理"""
        try:
            item = self.table.item(currentRow, currentColumn)
        except Exception:
            return
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        po_file = self._get_current_po()
        if po_file and key:
            entry = po_file.get_entry_by_key(key)
            self.entry_editor.set_entry(entry)
