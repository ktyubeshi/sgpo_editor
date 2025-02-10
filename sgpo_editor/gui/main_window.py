"""メインウィンドウ"""

import logging
from pathlib import Path
from typing import Optional, List, cast, Dict, Any
import traceback

from PySide6.QtCore import Qt, QSettings, QModelIndex, QEvent
from PySide6.QtGui import QAction, QKeySequence, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QWidget,
    QVBoxLayout,
)

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self.setWindowTitle("PO Editor")
        self.resize(800, 600)

        # POファイル
        self.current_po: Optional[ViewerPOFile] = None
        self.current_entry_index: int = 0
        self.total_entries: int = 0
        self._display_entries: List[str] = []

        # ウィジェット
        self.entry_editor = EntryEditor()
        self.stats_widget = StatsWidget()
        self.search_widget = SearchWidget(
            on_filter_changed=self._update_table,
            on_search_changed=self._on_search_changed,
            on_open_clicked=self._open_file,
        )
        self.table = QTableWidget()
        self.entry_table = self.table
        self.entry_editor_dock = QDockWidget("エントリ編集", self)

        # UIの初期化
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_dock_widgets()
        self._restore_dock_states()
        self._restore_window_state()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 検索/フィルタリング
        layout.addWidget(self.search_widget)

        # エントリ一覧
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["エントリ番号", "msgctxt", "msgid", "msgstr", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def _setup_dock_widgets(self) -> None:
        """ドックウィジェットの初期化"""
        # エントリ編集（上部）
        self.entry_editor_dock.setObjectName("entry_dock")
        self.entry_editor.text_changed.connect(self._on_entry_text_changed)
        self.entry_editor.apply_clicked.connect(self._on_apply_clicked)
        self.entry_editor.entry_changed.connect(self._on_entry_changed)
        self.entry_editor_dock.setWidget(self.entry_editor)
        self.entry_editor_dock.setAllowedAreas(
            Qt.DockWidgetArea.TopDockWidgetArea | 
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.entry_editor_dock)

        # 統計情報
        stats_dock = QDockWidget("統計情報", self)
        stats_dock.setObjectName("stats_dock")
        stats_dock.setWidget(self.stats_widget)
        stats_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, stats_dock)

    def _setup_menubar(self) -> None:
        """メニューバーの初期化"""
        # ファイルメニュー
        file_menu = self.menuBar().addMenu("ファイル")

        # 開く
        open_action = QAction("開く...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        # 保存
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        # 名前を付けて保存
        save_as_action = QAction("名前を付けて保存...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 終了
        exit_action = QAction("終了", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 表示メニュー
        display_menu = self.menuBar().addMenu("表示")
        display_menu.setObjectName("display_menu")
        
        # エントリ編集サブメニュー
        entry_edit_menu = display_menu.addMenu("エントリ編集")
        entry_edit_menu.setObjectName("entry_edit_menu")
        
        # レイアウト1
        layout1_action = QAction("レイアウト1", self)
        layout1_action.setObjectName("layout1_action")
        layout1_action.setCheckable(True)
        layout1_action.setChecked(True)
        layout1_action.triggered.connect(lambda: self._change_entry_layout(LayoutType.LAYOUT1))
        entry_edit_menu.addAction(layout1_action)
        
        # レイアウト2
        layout2_action = QAction("レイアウト2", self)
        layout2_action.setObjectName("layout2_action")
        layout2_action.setCheckable(True)
        layout2_action.triggered.connect(lambda: self._change_entry_layout(LayoutType.LAYOUT2))
        entry_edit_menu.addAction(layout2_action)
        
        # アクショングループの作成（排他的選択）
        layout_group = QActionGroup(self)
        layout_group.addAction(layout1_action)
        layout_group.addAction(layout2_action)
        layout_group.setExclusive(True)

    def _setup_statusbar(self) -> None:
        """ステータスバーの初期化"""
        self.statusBar().showMessage("準備完了")

    def _save_dock_states(self) -> None:
        """ドックウィジェットの状態を保存"""
        settings = QSettings()
        settings.setValue("dock_states", self.saveState())

    def _restore_dock_states(self) -> None:
        """ドックウィジェットの状態を復元"""
        settings = QSettings()
        if settings.contains("dock_states"):
            state = settings.value("dock_states")
            self.restoreState(state)
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    def _restore_window_state(self) -> None:
        """ウィンドウの状態を復元"""
        settings = QSettings()
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.contains("windowState"):
            self.restoreState(settings.value("windowState"))

    def _save_window_state(self) -> None:
        """ウィンドウの状態を保存"""
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event: QEvent) -> None:
        """ウィンドウが閉じられるときの処理

        Args:
            event: イベント
        """
        self._save_dock_states()
        self._save_window_state()
        event.accept()

    def _open_file(self) -> None:
        """ファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "POファイルを開く", "", "POファイル (*.po);;すべてのファイル (*.*)"
        )
        if not file_path:
            return

        try:
            self.current_po = ViewerPOFile()
            self.current_po.load(Path(file_path))
            self._update_table()
            self.setWindowTitle(f"PO Viewer - {Path(file_path).name}")
            self.statusBar().showMessage(f"ファイルを開きました: {file_path}", 3000)
        except Exception as e:
            logger.error("ファイルを開けませんでした: %s", e)
            self.statusBar().showMessage("ファイルを開けませんでした", 3000)

    def _save_file(self) -> None:
        """ファイルを保存する"""
        try:
            if not self.current_po:
                return

            if not hasattr(self.current_po, 'file_path') or not self.current_po.file_path:
                self._save_file_as()
                return

            try:
                self.current_po.save()
                self.statusBar().showMessage("ファイルを保存しました", 5000)
            except Exception as e:
                logger.error(f"ファイルの保存に失敗しました: {e}")
                self.statusBar().showMessage("保存に失敗しました", 3000)
                raise

        except Exception as e:
            logger.error(f"ファイルの保存に失敗しました: {e}")
            self.statusBar().showMessage("保存に失敗しました", 3000)
            raise

    def _save_file_as(self) -> None:
        """名前を付けて保存する"""
        if not self.current_po:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "名前を付けて保存",
            "",
            "POファイル (*.po);;すべてのファイル (*.*)"
        )
        if not file_path:
            return

        try:
            self.current_po.save(Path(file_path))
            self.statusBar().showMessage("保存しました", 3000)
        except Exception as e:
            logger.error(f"ファイルの保存に失敗しました: {e}")
            self.statusBar().showMessage("保存に失敗しました", 3000)
            raise

    def _validate_counters(self) -> None:
        """カウンターの検証"""
        try:
            if not isinstance(self.current_entry_index, int):
                self.current_entry_index = 0
                self.total_entries = 0
                raise ValueError("current_entry_indexは整数である必要があります")
            if not isinstance(self.total_entries, int):
                self.current_entry_index = 0
                self.total_entries = 0
                raise ValueError("total_entriesは整数である必要があります")
            if self.current_entry_index < 0:
                self.current_entry_index = 0
                raise ValueError("current_entry_indexは0以上である必要があります")
            if self.current_entry_index >= self.total_entries and self.total_entries > 0:
                self.current_entry_index = max(0, self.total_entries - 1)
                raise ValueError("current_entry_indexはtotal_entriesより小さい必要があります")
        except Exception as e:
            logger.error(f"カウンターの検証に失敗しました: {e}")
            self.statusBar().showMessage(f"カウンターの検証に失敗しました: {e}", 3000)
            raise

    def _update_progress(self) -> None:
        """内部カウンターの検証のみ実施（プログレスバーは削除済み）"""
        try:
            self._validate_counters()
        except Exception as e:
            logger.error(f"プログレスバーの更新でエラー: {e}")
            self.statusBar().showMessage(f"プログレスバーの更新でエラー: {e}", 3000)

    def _show_current_entry(self) -> None:
        """現在のエントリを表示する"""
        try:
            if not self.current_po or not self._display_entries:
                self.entry_editor.set_entry(None)
                return

            if not self._validate_counters():
                self.entry_editor.set_entry(None)
                return

            if self.current_entry_index < 0 or self.current_entry_index >= len(self._display_entries):
                self.entry_editor.set_entry(None)
                return

            key = self._display_entries[self.current_entry_index]
            entry = self.current_po.get_entry_by_key(key)
            if entry:
                self.entry_editor.set_entry(entry)
            else:
                self.entry_editor.set_entry(None)
        except Exception as e:
            logger.error("エントリの表示でエラー: %s", str(e))
            self.statusBar().showMessage("エントリの表示でエラー", 3000)
            self.entry_editor.set_entry(None)

    def _update_table(self, sort_column: int | None = None, sort_order: Qt.SortOrder | None = None) -> None:
        try:
            # Clear existing rows before updating the table
            self.table.setRowCount(0)
            # Ensure the table has 5 columns
            self.table.setColumnCount(5)
            criteria = self.search_widget.get_search_criteria()
            filter_text = "" if criteria.filter.strip() == "すべて" else criteria.filter
            search_text = criteria.search_text
            if self.current_po is None:
                return
            po = self.current_po
            # Convert sort parameters to strings
            sort_column_str = str(sort_column) if sort_column is not None else None
            if sort_order is not None:
                sort_order_str = "asc" if sort_order == Qt.SortOrder.AscendingOrder else "desc"
            else:
                sort_order_str = None
            # Retrieve filtered entries
            entries = po.get_filtered_entries(
                filter_text=filter_text,
                search_text=search_text,
                sort_column=sort_column_str,
                sort_order=sort_order_str
            )
            self._display_entries = []
            for idx, entry in enumerate(entries):
                # Debug: Log current state of flags before conversion
                logger.debug("_update_table: processing entry (key: %s) with flags type: %s, value: %s", getattr(entry, 'key', 'None'), type(entry.flags), entry.flags)
                if not hasattr(entry, 'flags') or not isinstance(entry.flags, list):
                    if isinstance(entry.flags, str) and entry.flags.strip() != "":
                        logger.debug("_update_table: converting entry.flags from string to list")
                        entry.flags = [entry.flags]
                    else:
                        logger.debug("_update_table: entry.flags is not a list and not a valid string; initializing to empty list")
                        entry.flags = []

                key = getattr(entry, 'key', None)
                if key is None:
                    raise AttributeError("'NoneType' object has no attribute 'key'")
                row = self.table.rowCount()
                self.table.insertRow(row)
                # Column 0: エントリ番号 (row index + 1)
                item0 = QTableWidgetItem(str(idx + 1))
                item0.setData(Qt.ItemDataRole.UserRole, key)
                self.table.setItem(row, 0, item0)
                
                # Column 1: msgctxt
                ctxt = entry.msgctxt if getattr(entry, 'msgctxt', None) is not None else ""
                item1 = QTableWidgetItem(str(ctxt))
                item1.setData(Qt.ItemDataRole.UserRole, key)
                self.table.setItem(row, 1, item1)
                
                # Column 2: msgid
                item2 = QTableWidgetItem(str(entry.msgid))
                item2.setData(Qt.ItemDataRole.UserRole, key)
                self.table.setItem(row, 2, item2)
                
                # Column 3: msgstr
                item3 = QTableWidgetItem(str(entry.msgstr))
                item3.setData(Qt.ItemDataRole.UserRole, key)
                self.table.setItem(row, 3, item3)
                
                # Column 4: 状態
                status = entry.get_status() if hasattr(entry, 'get_status') else ""
                item4 = QTableWidgetItem(str(status))
                item4.setData(Qt.ItemDataRole.UserRole, key)
                self.table.setItem(row, 4, item4)
                
                self._display_entries.append(key)
            self.total_entries = len(entries)
            if hasattr(self, 'current_entry_index'):
                self.current_entry_index = min(self.current_entry_index, max(0, self.total_entries - 1))
            else:
                self.current_entry_index = 0
            self._update_progress()
        except Exception as e:
            logger.error(f"テーブルの更新でエラー: {e}")
            self.statusBar().showMessage(f"テーブルの更新でエラー: {e}", 3000)

    def _on_header_clicked(self, logical_index: int) -> None:
        """ヘッダーがクリックされたときの処理"""
        if not self.table:
            return

        current_order = self.table.horizontalHeader().sortIndicatorOrder()
        new_order = (
            Qt.SortOrder.DescendingOrder
            if current_order == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        try:
            self._update_table(logical_index, new_order)
        except Exception as e:
            logger.error(f"ソートでエラー: {e}")
            self.statusBar().showMessage(f"ソートでエラー: {e}", 3000)

    def _on_selection_changed(self) -> None:
        """テーブルの選択が変更されたときの処理"""
        try:
            row = self.table.currentRow()
            if row < 0:
                self.entry_editor.set_entry(None)
                return

            item = self.table.item(row, 0)
            if item is None:
                self.entry_editor.set_entry(None)
                return

            key = item.data(Qt.ItemDataRole.UserRole)

            if not self.current_po:
                self.entry_editor.set_entry(None)
                return

            entry = self.current_po.get_entry_by_key(key)
            if entry is None:
                self.entry_editor.set_entry(None)
                return

            if not hasattr(entry, 'msgid') or entry.msgid is None:
                entry.msgid = ""
            elif not isinstance(entry.msgid, str):
                entry.msgid = str(entry.msgid)

            self.entry_editor.set_entry(entry)
        except Exception as e:
            self.statusBar().showMessage(f"選択変更でエラー: {e}", 3000)

    def _on_search_changed(self) -> None:
        """検索テキストが変更されたときの処理"""
        self._update_table()

    def _on_entry_changed(self, entry_number: int) -> None:
        """エントリが変更されたときの処理"""
        if not self.entry_editor_dock:
            return

        title = "エントリ編集"
        if entry_number >= 0:
            title = f"エントリ編集 - #{entry_number + 1}"
        self.entry_editor_dock.setWindowTitle(title)

    def _on_entry_text_changed(self) -> None:
        """エントリのテキストが変更されたときの処理"""
        if not self.entry_editor or not self.entry_editor_dock:
            return

        editor = cast(EntryEditor, self.entry_editor)
        if editor.current_entry_number is not None:
            # エントリが変更されたことを示す*マークを追加
            title = self.entry_editor_dock.windowTitle()
            if not title.endswith("*"):
                self.entry_editor_dock.setWindowTitle(f"{title}*")

    def _on_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理"""
        if not self.entry_editor.current_entry:
            return

        entry = self.entry_editor.current_entry
        # Log the initial state of flags
        logger.debug("_on_apply_clicked: initial entry.flags type: %s, value: %s", type(entry.flags), entry.flags)

        entry.msgstr = self.entry_editor.msgstr_edit.toPlainText()

        # If entry.flags is not a list, initialize it to an empty list
        if not hasattr(entry, 'flags') or not isinstance(entry.flags, list):
            logger.debug("_on_apply_clicked: entry.flags is not a list; initializing to empty list")
            entry.flags = []

        # Update fuzzy status based on checkbox
        if "fuzzy" in entry.flags and not self.entry_editor.fuzzy_checkbox.isChecked():
            logger.debug("_on_apply_clicked: removing 'fuzzy' from entry.flags")
            entry.flags.remove("fuzzy")
        elif "fuzzy" not in entry.flags and self.entry_editor.fuzzy_checkbox.isChecked():
            logger.debug("_on_apply_clicked: adding 'fuzzy' to entry.flags")
            entry.flags.append("fuzzy")

        logger.debug("_on_apply_clicked: final entry.flags type: %s, value: %s", type(entry.flags), entry.flags)

        # エントリを更新
        if self.current_po:
            self.current_po.update_entry(entry)
            self._modified = True
            self.statusBar().showMessage("エントリを更新しました", 3000)

        # ウィンドウタイトルを更新
        title = self.entry_editor_dock.windowTitle()
        if title.endswith("*"):
            self.entry_editor_dock.setWindowTitle(title[:-1])

        # 追加: エントリリストの表示を更新
        self._update_table()

    def next_entry(self) -> None:
        try:
            if not isinstance(self.current_entry_index, int):
                raise TypeError("current_entry_index is not int")
            if self.current_entry_index < self.total_entries - 1:
                self.current_entry_index += 1
                self.table.setCurrentCell(self.current_entry_index, 0)
                self._on_selection_changed()
            else:
                raise IndexError("Already at last entry")
        except Exception as e:
            self.statusBar().showMessage(f"次のエントリへの移動でエラー: {e}", 3000)
            raise

    def previous_entry(self) -> None:
        try:
            if not isinstance(self.current_entry_index, int):
                raise TypeError("current_entry_index is not int")
            if self.current_entry_index > 0:
                self.current_entry_index -= 1
                self.table.setCurrentCell(self.current_entry_index, 0)
                self._on_selection_changed()
            else:
                raise IndexError("Already at first entry")
        except Exception as e:
            self.statusBar().showMessage(f"前のエントリへの移動でエラー: {e}", 3000)
            raise

    def first_entry(self) -> None:
        """最初のエントリに移動する"""
        try:
            if self.total_entries > 0:
                self.current_entry_index = 0
                self.table.selectRow(self.current_entry_index)
                self._update_progress()
        except Exception as e:
            logger.error(f"最初のエントリへの移動でエラー: {e}")
            self.statusBar().showMessage(f"最初のエントリへの移動でエラー: {e}", 3000)
            raise

    def last_entry(self) -> None:
        """最後のエントリに移動する"""
        try:
            if self.total_entries > 0:
                self.current_entry_index = self.total_entries - 1
                self.table.selectRow(self.current_entry_index)
                self._update_progress()
        except Exception as e:
            logger.error(f"最後のエントリへの移動でエラー: {e}")
            self.statusBar().showMessage(f"最後のエントリへの移動でエラー: {e}", 3000)
            raise

    def _change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する"""
        self.entry_editor.set_layout_type(layout_type)


def main():
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
