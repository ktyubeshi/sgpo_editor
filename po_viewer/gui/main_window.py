"""メインウィンドウの実装"""
import logging
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QDockWidget,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence

from .widgets.entry_editor import EntryEditorWidget
from .widgets.stats import StatsWidget
from .widgets.search import SearchWidget
from .models.entry import EntryModel
from ..core.viewer_po_file import ViewerPOFile

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """POビューワーのメインウィンドウ"""

    def __init__(self):
        """初期化"""
        super().__init__()
        self.setWindowTitle("PO Viewer")
        self.setMinimumSize(800, 600)
        
        # POファイル
        self.current_po: Optional[ViewerPOFile] = None
        self._display_entries: List[str] = []  # 表示順序を保持するキーのリスト
        
        # ウィジェット
        self.entry_editor: Optional[EntryEditorWidget] = None
        self.stats_widget: Optional[StatsWidget] = None
        self.search_widget: Optional[SearchWidget] = None
        self.table: Optional[QTableWidget] = None
        
        # UIの初期化
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_dock_widgets()
        self._restore_dock_states()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 検索/フィルタリング
        self.search_widget = SearchWidget(
            on_filter_changed=self._update_table,
            on_search_changed=self._on_search_changed,
            on_open_clicked=self._open_file,
        )
        layout.addWidget(self.search_widget)
        
        # エントリ一覧
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "msgid", "msgstr", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def _setup_dock_widgets(self) -> None:
        """ドックウィジェットの初期化"""
        # エントリ編集
        entry_dock = QDockWidget("エントリ編集", self)
        entry_dock.setObjectName("entry_dock")
        self.entry_editor = EntryEditorWidget()
        entry_dock.setWidget(self.entry_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, entry_dock)
        
        # 統計情報
        stats_dock = QDockWidget("統計情報", self)
        stats_dock.setObjectName("stats_dock")
        self.stats_widget = StatsWidget()
        stats_dock.setWidget(self.stats_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, stats_dock)

    def _setup_menubar(self) -> None:
        """メニューバーの初期化"""
        # ファイルメニュー
        file_menu = self.menuBar().addMenu("ファイル")
        
        # 開く
        open_action = QAction("開く...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        # 保存
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        
        # 名前を付けて保存
        save_as_action = QAction("名前を付けて保存...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # 終了
        exit_action = QAction("終了", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_statusbar(self) -> None:
        """ステータスバーの初期化"""
        self.statusBar().showMessage("準備完了")

    def _save_dock_states(self) -> None:
        """ドックウィジェットの状態を保存"""
        settings = QSettings()
        settings.setValue("mainwindow/geometry", self.saveGeometry())
        settings.setValue("mainwindow/state", self.saveState())

    def _restore_dock_states(self) -> None:
        """ドックウィジェットの状態を復元"""
        settings = QSettings()
        geometry = settings.value("mainwindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = settings.value("mainwindow/state")
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:
        """ウィンドウが閉じられるときの処理"""
        self._save_dock_states()
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
            self.setWindowTitle(f"POビューワー - {Path(file_path).name}")
            self.statusBar().showMessage(f"ファイルを開きました: {file_path}", 3000)
        except Exception as e:
            logger.error("ファイルを開けませんでした: %s", e)
            self.statusBar().showMessage("ファイルを開けませんでした", 3000)

    def _save_file(self) -> None:
        """ファイルを保存"""
        if not self.current_po or not self.current_po.path:
            self._save_file_as()
            return

        try:
            self.current_po.save()
            self.statusBar().showMessage("保存しました", 3000)
        except Exception as e:
            logger.error("保存に失敗しました: %s", e)
            self.statusBar().showMessage("保存に失敗しました", 3000)

    def _save_file_as(self) -> None:
        """名前を付けて保存"""
        if not self.current_po:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "名前を付けて保存", "", "POファイル (*.po);;すべてのファイル (*.*)"
        )
        if not file_path:
            return

        try:
            self.current_po.save(Path(file_path))
            self.setWindowTitle(f"POビューワー - {Path(file_path).name}")
            self.statusBar().showMessage("保存しました", 3000)
        except Exception as e:
            logger.error("保存に失敗しました: %s", e)
            self.statusBar().showMessage("保存に失敗しました", 3000)

    def _update_table(self, sort_column: Optional[int] = None, sort_order: Optional[Qt.SortOrder] = None) -> None:
        """テーブルの内容を更新"""
        if not self.current_po:
            self.table.setRowCount(0)
            return

        # フィルタリング
        filter_text = self.search_widget.get_filter()
        search_text = self.search_widget.get_search_text().lower()
        
        # エントリをフィルタリング
        entries = self.current_po.get_entries()
        filtered_entries = []
        self._display_entries = []
        
        for entry in entries:
            # フィルタ条件をチェック
            if filter_text == "翻訳済み" and not entry.translated():
                continue
            if filter_text == "未翻訳" and entry.translated():
                continue
            if filter_text == "ファジー" and not entry.is_fuzzy():
                continue
            
            # 検索テキストをチェック
            if search_text:
                if (
                    search_text not in entry.msgid.lower()
                    and search_text not in entry.msgstr.lower()
                    and (not entry.msgctxt or search_text not in entry.msgctxt.lower())
                ):
                    continue
            
            filtered_entries.append(entry)
            self._display_entries.append(entry.key)

        # テーブルを更新
        self.table.setRowCount(len(filtered_entries))
        for i, entry in enumerate(filtered_entries):
            # インデックス
            index_item = QTableWidgetItem(str(i + 1))
            index_item.setData(Qt.UserRole, entry.key)
            self.table.setItem(i, 0, index_item)
            
            # msgid
            msgid_item = QTableWidgetItem(entry.msgid)
            self.table.setItem(i, 1, msgid_item)
            
            # msgstr
            msgstr_item = QTableWidgetItem(entry.msgstr)
            self.table.setItem(i, 2, msgstr_item)
            
            # 状態
            status_item = QTableWidgetItem(entry.get_status())
            self.table.setItem(i, 3, status_item)

        # ソート
        if sort_column is not None and sort_order is not None:
            self.table.sortItems(sort_column, sort_order)

        # 統計情報を更新
        if self.stats_widget:
            self.stats_widget.update_stats(self.current_po.get_stats())

    def _on_header_clicked(self, logical_index: int) -> None:
        """ヘッダーがクリックされたときの処理"""
        current_order = self.table.horizontalHeader().sortIndicatorOrder()
        new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        self._update_table(logical_index, new_order)

    def _on_selection_changed(self) -> None:
        """テーブルの選択行が変更されたときの処理"""
        current_row = self.table.currentRow()
        if current_row < 0:
            self.entry_editor.set_entry(None)
            return

        # 選択行の最初のセルからエントリのキーを取得
        item = self.table.item(current_row, 0)
        if not item:
            self.entry_editor.set_entry(None)
            return

        key = item.data(Qt.UserRole)
        entries = self.current_po.get_entries()
        entry = next((e for e in entries if e.key == key), None)
        if entry:
            self.entry_editor.set_entry(entry)
        else:
            self.entry_editor.set_entry(None)

    def _on_search_changed(self) -> None:
        """検索テキストが変更されたときの処理"""
        self._update_table()
