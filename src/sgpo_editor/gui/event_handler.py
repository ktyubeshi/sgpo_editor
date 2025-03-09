"""イベント処理モジュール

このモジュールは、GUIイベントの処理とハンドリングに関する機能を提供します。
"""

import logging
from typing import Optional, Callable, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QTableWidget, QMessageBox

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType

logger = logging.getLogger(__name__)


class EventHandler(QObject):
    """イベント処理クラス"""
    
    entry_updated = Signal(int)  # エントリが更新されたとき（引数：エントリ番号）
    
    def __init__(self, table: QTableWidget, entry_editor: EntryEditor,
                 get_current_po: Callable[[], Optional[ViewerPOFile]],
                 update_table: Callable[[], None],
                 show_status: Callable[[str, int], None]) -> None:
        """初期化

        Args:
            table: テーブルウィジェット
            entry_editor: エントリエディタ
            get_current_po: 現在のPOファイルを取得するコールバック
            update_table: テーブル更新用コールバック
            show_status: ステータス表示用コールバック
        """
        super().__init__()
        self.table = table
        self.entry_editor = entry_editor
        self._get_current_po = get_current_po
        self._update_table = update_table
        self._show_status = show_status
        self._last_processed_row = -1
        self._drag_timer = QTimer()
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._process_drag_selection)
        self._pending_row = -1

    def setup_connections(self) -> None:
        """イベント接続の設定"""
        # テーブル選択イベント
        self.table.cellPressed.connect(self._on_cell_selected)
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        
        # エントリエディタイベント
        self.entry_editor.text_changed.connect(self._on_entry_text_changed)
        self.entry_editor.apply_clicked.connect(self._on_apply_clicked)
        self.entry_editor.entry_changed.connect(self._on_entry_changed)

    def _on_cell_selected(self, row: int, column: int) -> None:
        """セルがクリックされたときの処理

        Args:
            row: 行インデックス
            column: 列インデックス
        """
        self._update_detail_view(row)
    
    def _on_cell_entered(self, row: int, column: int) -> None:
        """セルにマウスが入ったときの処理

        Args:
            row: 行インデックス
            column: 列インデックス
        """
        # マウスドラッグ中かどうかを確認
        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            # 前回処理した行と同じなら処理しない（ドラッグ中の重複更新を防止）
            if row != self._last_processed_row:
                self._pending_row = row
                
                # すでにタイマーが動いていない場合のみ開始
                if not self._drag_timer.isActive():
                    # 約16.7ミリ秒後に処理を実行（60fps相当）
                    self._drag_timer.start(17)
    
    def _process_drag_selection(self) -> None:
        """ドラッグ選択処理の遅延実行"""
        if self._pending_row >= 0 and self._pending_row != self._last_processed_row:
            self._update_detail_view(self._pending_row)
            self._last_processed_row = self._pending_row

    def _update_detail_view(self, row: int) -> None:
        """指定された行のエントリ詳細を表示する

        Args:
            row: 行インデックス
        """
        try:
            if row < 0 or row >= self.table.rowCount():
                self.entry_editor.set_entry(None)
                return

            item = self.table.item(row, 0)
            if item is None:
                self.entry_editor.set_entry(None)
                return

            key = item.data(Qt.ItemDataRole.UserRole)
            current_po = self._get_current_po()

            if not current_po:
                self.entry_editor.set_entry(None)
                return

            entry = current_po.get_entry_by_key(key)
            if entry is None:
                self.entry_editor.set_entry(None)
                return

            if not hasattr(entry, 'msgid') or entry.msgid is None:
                entry.msgid = ""
            elif not isinstance(entry.msgid, str):
                entry.msgid = str(entry.msgid)

            self.entry_editor.set_entry(entry)
            
            # エントリ選択変更時にシグナルを発行
            if hasattr(entry, 'position'):
                self.entry_updated.emit(entry.position)
        except Exception as e:
            self._show_status(f"詳細表示でエラー: {e}", 3000)

    def _on_entry_text_changed(self) -> None:
        """エントリのテキストが変更されたときの処理"""
        self._show_status("変更が保留中です。適用するには [適用] ボタンをクリックしてください。", 0)

    def _on_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理"""
        try:
            entry = self.entry_editor.current_entry
            if not entry:
                return
                
            current_po = self._get_current_po()
            if not current_po:
                return
                
            # エントリの更新
            current_po.update_entry(entry)
            
            # テーブルの更新
            self._update_table()
            
            self._show_status(f"エントリ {entry.position} を更新しました", 3000)
            self.entry_updated.emit(entry.position)
            
        except Exception as e:
            logger.error(f"エントリを適用する際にエラーが発生しました: {e}")
            QMessageBox.critical(
                None,
                "エラー",
                f"エントリを適用する際にエラーが発生しました:\n{e}"
            )
            self._show_status(f"エラー: {e}", 3000)

    def _on_entry_changed(self, entry_number: int) -> None:
        """エントリが変更されたときの処理

        Args:
            entry_number: エントリ番号
        """
        current_po = self._get_current_po()
        if not current_po:
            return
            
        entries = current_po.get_filtered_entries()
        if not entries:
            return
            
        for i, entry in enumerate(entries):
            if entry.position == entry_number:
                self.table.selectRow(i)
                break

    def _on_current_cell_changed(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        """現在のセルが変更されたときの処理（キーボード操作対応）

        Args:
            current_row: 現在の行インデックス
            current_column: 現在の列インデックス
            previous_row: 前の行インデックス
            previous_column: 前の列インデックス
        """
        self._update_detail_view(current_row)

    def change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する

        Args:
            layout_type: レイアウトタイプ
        """
        self.entry_editor.set_layout_type(layout_type)
        
    def get_current_entry(self) -> Any:
        """現在選択されているエントリを取得する
        
        Returns:
            現在選択されているエントリ、またはNone
        """
        return self.entry_editor.current_entry
