"""イベント処理モジュール

このモジュールは、GUIイベントの処理とハンドリングに関する機能を提供します。
"""

import logging
from typing import Callable, Dict, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget

from sgpo_editor.core.viewer_po_file import ViewerPOFile
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
        このクラスは、UI表示の高速化のために以下の独自キャッシュを管理します:

        1. _entry_cache: エントリキーをキーとするエントリオブジェクトのキャッシュ
           - 目的: 繰り返しアクセスされるエントリの高速表示
           - スコープ: UI表示限定の一時的キャッシュ
           - EntryCacheManagerとの関係: 独立したUI専用キャッシュであり、コアの
             EntryCacheManagerとは別に管理される。データの永続化には関与しない

        2. _row_key_map: 行インデックスとエントリキーのマッピング
           - 目的: テーブル行からエントリへの素早いアクセス
           - スコープ: テーブル表示中のみ有効

    プリフェッチ戦略:
        _prefetch_visible_entries メソッドは、以下の機能を提供します:
        - 現在表示中のテーブル行のエントリをバックグラウンドで事前ロード
        - スクロール時のスムーズな表示のために先読み
        - UIスレッドのブロックを避けるために部分的なロード

    注意:
        このクラスのキャッシュは表示用途のみであり、エントリの編集・保存には
        ViewerPOFileを通じたDBアクセスが必要。エントリ更新時には、適切に
        キャッシュを無効化してViewerPOFileの最新データを取得する必要がある。
    """

    entry_updated = Signal(int)  # エントリが更新されたとき（引数：エントリ番号）
    entry_selected = Signal(int)  # エントリが選択されたとき（引数：エントリ番号）

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
        self._entry_cache: EntryModelMap = {}
        # 行インデックスとキーのマッピング（キー：行インデックス、値：エントリキー）
        self._row_key_map: Dict[int, str] = {}

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

        テーブルの行を元に対応するエントリを取得し、エントリエディタに表示します。
        パフォーマンス最適化のため、以下のキャッシュ戦略を使用します:
        1. 内部キャッシュ(_entry_cache)をまず確認
        2. キャッシュになければViewerPOFileからエントリを取得
        3. 取得したエントリを内部キャッシュに保存

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

                # エントリ選択変更時に選択シグナルを発行
                if hasattr(entry, "position"):
                    self.entry_selected.emit(entry.position)
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
                self.entry_selected.emit(entry.position)

            # 選択が完了したら、非同期でプリフェッチを開始
            if not self._prefetch_timer.isActive():
                self._prefetch_timer.start(10)
        except Exception as e:
            self._show_status(f"詳細表示でエラー: {e}", 3000)

    def _prefetch_visible_entries(self) -> None:
        """現在表示されているエリアのエントリをプリフェッチする

        テーブルスクロール時やテーブル表示後に呼び出され、現在表示されている
        エリアおよびその前後のエントリを事前にロードします。これにより:
        1. エントリ間のナビゲーション高速化
        2. スクロール時の表示遅延軽減
        3. エントリ選択時のレスポンス向上

        キャッシュ戦略:
        - 現在表示中の行の前後数行を含む範囲のエントリをロード
        - すでにキャッシュにあるエントリは再取得しない
        - DBアクセスを最小限に抑えるため、必要なエントリのみを取得

        注意:
        このメソッドはタイマーを介して非同期に実行され、UIスレッドをブロックしません。
        """
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
        logger.debug("EventHandler._on_apply_clicked: 開始")
        try:
            entry = self.entry_editor.current_entry
            if not entry:
                logger.debug("EventHandler._on_apply_clicked: エントリがNoneのため終了")
                return

            current_po = self._get_current_po()
            if not current_po:
                logger.debug(
                    "EventHandler._on_apply_clicked: POファイルがNoneのため終了"
                )
                return

            # エントリの更新
            logger.debug(
                f"EventHandler._on_apply_clicked: エントリ更新開始 key={entry.key}, position={entry.position}"
            )
            current_po.update_entry(entry)
            logger.debug("EventHandler._on_apply_clicked: エントリ更新完了")

            # キャッシュの更新
            if hasattr(entry, "key") and entry.key:
                logger.debug(
                    f"EventHandler._on_apply_clicked: キャッシュ更新 key={entry.key}"
                )
                self._entry_cache[entry.key] = entry

            # この時点でテーブルを更新すると重複更新が発生するため、ここでの更新は行わない
            # MainWindowの_on_entry_updatedで一元的に更新される
            # self._update_table()
            logger.debug(
                "EventHandler._on_apply_clicked: テーブル更新はMainWindowに委譲"
            )

            # 更新されたエントリを選択状態に戻す
            if hasattr(entry, "key") and entry.key:
                logger.debug(
                    f"EventHandler._on_apply_clicked: 更新されたエントリを選択状態に戻す key={entry.key}"
                )
                # テーブルの現在の行データを使用して、更新されたエントリの行を見つける
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if item is None:
                        continue

                    key = item.data(Qt.ItemDataRole.UserRole)
                    if key == entry.key:
                        logger.debug(
                            f"EventHandler._on_apply_clicked: 該当する行を選択 row={row}"
                        )
                        # 該当する行を選択
                        self.table.selectRow(row)
                        break

            logger.debug("EventHandler._on_apply_clicked: ステータス表示")
            self._show_status(f"エントリ {entry.position} を更新しました", 3000)
            logger.debug(
                f"EventHandler._on_apply_clicked: entry_updatedシグナル発行 position={entry.position}"
            )
            self.entry_updated.emit(entry.position)
            logger.debug("EventHandler._on_apply_clicked: 完了")

        except Exception as e:
            logger.error(f"EventHandler._on_apply_clicked: エラー発生 {e}")
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
        # テーブルの現在の行データを使用して、DBに再クエリせずに目的のエントリを見つける
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue

            key = item.data(Qt.ItemDataRole.UserRole)
            if key in self._entry_cache:
                entry = self._entry_cache[key]
                if hasattr(entry, "position") and entry.position == entry_number:
                    self.table.selectRow(row)
                    break

    def clear_cache(self) -> None:
        """エントリキャッシュをクリアする

        以下の場合に呼び出されます:
        1. POファイルの読み込み/切り替え時
        2. テーブル内容の完全な更新時
        3. エントリに重要な変更があった場合

        これにより、キャッシュデータとViewerPOFileの実データとの整合性が保たれます。
        """
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

    def get_current_entry(self) -> Optional["EntryModel"]:
        """現在選択されているエントリを取得する

        Returns:
            Optional[EntryModel]: 現在選択されているエントリ（なければNone）
        """
        return self.entry_editor.current_entry
