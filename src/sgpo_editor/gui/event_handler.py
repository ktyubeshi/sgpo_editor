"""イベント処理モジュール

このモジュールは、GUIイベントの処理とハンドリングに関する機能を提供します。
"""

import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType

logger = logging.getLogger(__name__)


class EventHandler(QObject):
    """イベント処理クラス"""

    entry_updated = Signal(int)  # エントリが更新されたとき（引数：エントリ番号）

    def __init__(
        self,
        table: QTableWidget,
        entry_editor: EntryEditor,
        get_current_po: Callable[[], Optional[ViewerPOFile]],
        update_table: Callable[[], None],
        show_status: Callable[[str, int], None],
    ) -> None:
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

        # エントリキャッシュを初期化（キー：エントリキー、値：エントリオブジェクト）
        self._entry_cache = {}
        # 行インデックスとキーのマッピング（キー：行インデックス、値：エントリキー）
        self._row_key_map = {}

        # プリフェッチタイマー
        self._prefetch_timer = QTimer()
        self._prefetch_timer.setSingleShot(True)
        self._prefetch_timer.timeout.connect(self._prefetch_visible_entries)

    def setup_connections(self) -> None:
        """イベント接続の設定"""
        # テーブル選択イベント
        self.table.cellPressed.connect(self._on_cell_selected)
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        # テーブルスクロールイベント
        self.table.verticalScrollBar().valueChanged.connect(
            lambda: self._prefetch_timer.start(100)  # スクロール後にプリフェッチ
        )

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

            # 行インデックスとキーのマッピングを更新
            self._row_key_map[row] = key

            # キャッシュにエントリがあればそれを使用
            if key in self._entry_cache:
                entry = self._entry_cache[key]
                self.entry_editor.set_entry(entry)

                # エントリ選択変更時にシグナルを発行
                if hasattr(entry, "position"):
                    self.entry_updated.emit(entry.position)
                return

            # キャッシュになければPOファイルから取得
            current_po = self._get_current_po()
            if not current_po:
                self.entry_editor.set_entry(None)
                return

            entry = current_po.get_entry_by_key(key)
            if entry is None:
                self.entry_editor.set_entry(None)
                return

            if not hasattr(entry, "msgid") or entry.msgid is None:
                entry.msgid = ""
            elif not isinstance(entry.msgid, str):
                entry.msgid = str(entry.msgid)

            # エントリをキャッシュに保存
            self._entry_cache[key] = entry

            self.entry_editor.set_entry(entry)

            # エントリ選択変更時にシグナルを発行
            if hasattr(entry, "position"):
                self.entry_updated.emit(entry.position)

            # 選択が完了したら、非同期でプリフェッチを開始
            if not self._prefetch_timer.isActive():
                self._prefetch_timer.start(10)
        except Exception as e:
            self._show_status(f"詳細表示でエラー: {e}", 3000)

    def _prefetch_visible_entries(self) -> None:
        """現在表示されているエリアのエントリをプリフェッチする"""
        try:
            current_po = self._get_current_po()
            if not current_po:
                return

            # 現在表示されている行の範囲を取得
            scroll_bar = self.table.verticalScrollBar()
            scroll_value = scroll_bar.value()

            # テーブルの表示領域の行数を推定
            visible_height = self.table.viewport().height()
            row_height = self.table.rowHeight(0) if self.table.rowCount() > 0 else 20
            visible_rows = max(1, visible_height // row_height)

            # スクロール位置から表示されている行の範囲を計算
            first_visible_row = max(
                0, scroll_value // row_height - 5
            )  # 上に余裕を持たせる
            last_visible_row = min(
                self.table.rowCount() - 1, first_visible_row + visible_rows + 10
            )  # 下にも余裕を持たせる

            # 表示されている行のエントリキーを収集（キャッシュにないもののみ）
            keys_to_prefetch = []
            for row in range(first_visible_row, last_visible_row + 1):
                if row < 0 or row >= self.table.rowCount():
                    continue

                item = self.table.item(row, 0)
                if item is None:
                    continue

                key = item.data(Qt.ItemDataRole.UserRole)
                if key and key not in self._entry_cache:
                    keys_to_prefetch.append(key)

            # キャッシュにないエントリを一つずつプリフェッチ
            for key in keys_to_prefetch:
                try:
                    entry = current_po.get_entry_by_key(key)
                    if entry:
                        if not hasattr(entry, "msgid") or entry.msgid is None:
                            entry.msgid = ""
                        elif not isinstance(entry.msgid, str):
                            entry.msgid = str(entry.msgid)

                        self._entry_cache[key] = entry
                except Exception as e:
                    logger.debug(f"エントリのプリフェッチ中にエラー {key}: {e}")

        except Exception as e:
            logger.debug(f"プリフェッチエラー: {e}")

    def _on_entry_text_changed(self) -> None:
        """エントリのテキストが変更されたときの処理"""
        self._show_status(
            "変更が保留中です。適用するには [適用] ボタンをクリックしてください。", 0
        )

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

            # キャッシュの更新
            if hasattr(entry, "key") and entry.key:
                self._entry_cache[entry.key] = entry

            # テーブルの更新
            self._update_table()

            self._show_status(f"エントリ {entry.position} を更新しました", 3000)
            self.entry_updated.emit(entry.position)

        except Exception as e:
            logger.error(f"エントリを適用する際にエラーが発生しました: {e}")
            QMessageBox.critical(
                None, "エラー", f"エントリを適用する際にエラーが発生しました:\n{e}"
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

    def clear_cache(self) -> None:
        """キャッシュをクリアする"""
        self._entry_cache.clear()
        self._row_key_map.clear()

    def _on_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ) -> None:
        """現在のセルが変更されたときの処理"""
        if current_row != previous_row:
            self._update_detail_view(current_row)

    def change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する

        Args:
            layout_type: レイアウトタイプ
        """
        self.entry_editor.change_layout(layout_type)

    def get_current_entry(self) -> Optional[Any]:
        """現在選択されているエントリを取得する

        Returns:
            Optional[Any]: 現在選択されているエントリ（なければNone）
        """
        return self.entry_editor.current_entry
