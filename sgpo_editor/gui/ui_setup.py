"""UI設定モジュール

このモジュールは、UIコンポーネントの設定と管理に関する機能を提供します。
"""

import logging
from typing import Optional, Callable

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QProgressBar,
)

from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.stats import StatsWidget
from sgpo_editor.gui.widgets.search import SearchWidget

logger = logging.getLogger(__name__)


class UIManager:
    """UI管理クラス"""

    def __init__(self, main_window: QMainWindow, entry_editor: EntryEditor, 
                stats_widget: StatsWidget, search_widget: SearchWidget) -> None:
        """初期化

        Args:
            main_window: メインウィンドウ
            entry_editor: エントリエディタ
            stats_widget: 統計情報ウィジェット
            search_widget: 検索ウィジェット
        """
        self.main_window = main_window
        self.entry_editor = entry_editor
        self.stats_widget = stats_widget
        self.search_widget = search_widget
        
        # ドックウィジェット
        self.entry_editor_dock = QDockWidget("エントリ編集", main_window)
        
        # メニューアクション
        self.layout1_action: Optional[QAction] = None
        self.layout2_action: Optional[QAction] = None
        
    def setup_central_widget(self, table_widget) -> None:
        """中央ウィジェットの設定

        Args:
            table_widget: テーブルウィジェット
        """
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 検索/フィルタリング
        layout.addWidget(self.search_widget)
        
        # エントリ一覧
        layout.addWidget(table_widget)

    def setup_dock_widgets(self) -> None:
        """ドックウィジェットの設定"""
        # エントリ編集（上部）
        self.entry_editor_dock.setObjectName("entry_dock")
        self.entry_editor_dock.setWidget(self.entry_editor)
        self.entry_editor_dock.setAllowedAreas(
            Qt.DockWidgetArea.TopDockWidgetArea | 
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.main_window.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.entry_editor_dock)

        # 統計情報
        stats_dock = QDockWidget("統計情報", self.main_window)
        stats_dock.setObjectName("stats_dock")
        stats_dock.setWidget(self.stats_widget)
        stats_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, stats_dock)

    def setup_menubar(self, callbacks) -> None:
        """メニューバーの設定

        Args:
            callbacks: コールバック関数の辞書
              - open_file: ファイルを開く
              - save_file: ファイルを保存
              - save_file_as: 名前を付けて保存
              - close: アプリケーションを閉じる
              - change_layout: レイアウト変更
        """
        # ファイルメニュー
        file_menu = self.main_window.menuBar().addMenu("ファイル")

        # 開く
        open_action = QAction("開く...", self.main_window)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(callbacks["open_file"])
        file_menu.addAction(open_action)

        # 保存
        save_action = QAction("保存", self.main_window)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(callbacks["save_file"])
        file_menu.addAction(save_action)

        # 名前を付けて保存
        save_as_action = QAction("名前を付けて保存...", self.main_window)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(callbacks["save_file_as"])
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # 終了
        exit_action = QAction("終了", self.main_window)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(callbacks["close"])
        file_menu.addAction(exit_action)

        # 表示メニュー
        display_menu = self.main_window.menuBar().addMenu("表示")
        display_menu.setObjectName("display_menu")
        
        # エントリ編集サブメニュー
        entry_edit_menu = display_menu.addMenu("エントリ編集")
        entry_edit_menu.setObjectName("entry_edit_menu")
        
        # レイアウト1
        self.layout1_action = QAction("レイアウト1", self.main_window)
        self.layout1_action.setObjectName("layout1_action")
        self.layout1_action.setCheckable(True)
        self.layout1_action.setChecked(True)
        self.layout1_action.triggered.connect(
            lambda: callbacks["change_layout"](LayoutType.LAYOUT1)
        )
        entry_edit_menu.addAction(self.layout1_action)
        
        # レイアウト2
        self.layout2_action = QAction("レイアウト2", self.main_window)
        self.layout2_action.setObjectName("layout2_action")
        self.layout2_action.setCheckable(True)
        self.layout2_action.triggered.connect(
            lambda: callbacks["change_layout"](LayoutType.LAYOUT2)
        )
        entry_edit_menu.addAction(self.layout2_action)
        
        # アクショングループの作成（排他的選択）
        layout_group = QActionGroup(self.main_window)
        layout_group.addAction(self.layout1_action)
        layout_group.addAction(self.layout2_action)
        layout_group.setExclusive(True)

    def setup_statusbar(self) -> None:
        """ステータスバーの設定"""
        self.main_window.statusBar().showMessage("準備完了")

    def save_dock_states(self) -> None:
        """ドックウィジェットの状態を保存"""
        settings = QSettings()
        settings.setValue("dock_states", self.main_window.saveState())

    def restore_dock_states(self) -> None:
        """ドックウィジェットの状態を復元"""
        settings = QSettings()
        if settings.contains("dock_states"):
            state = settings.value("dock_states")
            self.main_window.restoreState(state)

    def restore_window_state(self) -> None:
        """ウィンドウの状態を復元"""
        settings = QSettings()
        if settings.contains("geometry"):
            self.main_window.restoreGeometry(settings.value("geometry"))

    def save_window_state(self) -> None:
        """ウィンドウの状態を保存"""
        settings = QSettings()
        settings.setValue("geometry", self.main_window.saveGeometry())
