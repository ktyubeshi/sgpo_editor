"""UI設定モジュール

このモジュールは、UIコンポーネントの設定と管理に関する機能を提供します。
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMenu,
    QTableWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget

logger = logging.getLogger(__name__)


class UIManager:
    """UI管理クラス"""

    def __init__(
        self,
        main_window: QMainWindow,
        entry_editor: EntryEditor,
        stats_widget: StatsWidget,
        search_widget: SearchWidget,
    ) -> None:
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

        # 最近使用したファイルのアクション
        self.recent_file_actions: List[QAction] = []
        self.recent_files_menu: Optional[QMenu] = None
        
        # 列表示設定のアクション
        self.column_visibility_actions: List[QAction] = []
        self.column_visibility_menu: Optional[QMenu] = None

        # ツールバーアクション
        self.toolbar_actions: Dict[str, QAction] = {}

    def setup_central_widget(self, table_widget: QTableWidget) -> None:
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
            Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.main_window.addDockWidget(
            Qt.DockWidgetArea.TopDockWidgetArea, self.entry_editor_dock
        )

        # 統計情報
        stats_dock = QDockWidget("統計情報", self.main_window)
        stats_dock.setObjectName("stats_dock")
        stats_dock.setWidget(self.stats_widget)
        stats_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.main_window.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, stats_dock
        )

    def setup_menubar(self, callbacks: Dict[str, Callable[..., Any]]) -> None:
        """メニューバーの設定

        Args:
            callbacks: コールバック関数の辞書
              - open_file: ファイルを開く
              - save_file: ファイルを保存
              - save_file_as: 名前を付けて保存
              - close: アプリケーションを閉じる
              - change_layout: レイアウト変更
              - open_recent_file: 最近使用したファイルを開く
        """
        # ファイルメニュー
        file_menu = self.main_window.menuBar().addMenu("ファイル")

        # 開く
        open_action = QAction("開く...", self.main_window)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(callbacks["open_file"])
        file_menu.addAction(open_action)

        # 最近使用した項目を開く
        self.recent_files_menu = QMenu("最近使用した項目を開く", self.main_window)
        self.recent_files_menu.setObjectName("recent_files_menu")
        file_menu.addMenu(self.recent_files_menu)

        # 最近使用したファイルアクションのリストを作成
        self.update_recent_files_menu(callbacks.get("open_recent_file"))

        file_menu.addSeparator()

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
        
        # 列表示設定サブメニュー
        self.column_visibility_menu = display_menu.addMenu("表示列の設定")
        self.column_visibility_menu.setObjectName("column_visibility_menu")
        
        # 列表示設定のコールバックが提供されている場合、メニューを設定
        if "toggle_column_visibility" in callbacks and "table_manager" in callbacks:
            # メニュー設定を明示的に実行
            print("Setting up column visibility menu with callbacks")
            toggle_cb = callbacks["toggle_column_visibility"]
            table_mgr = callbacks["table_manager"]
            self._setup_column_visibility_menu(toggle_cb, table_mgr)

        # ツールメニュー
        tools_menu = self.main_window.menuBar().addMenu("ツール")
        tools_menu.setObjectName("tools_menu")

        # POフォーマットエディタ
        po_format_editor_action = QAction("POフォーマットエディタ", self.main_window)
        po_format_editor_action.setObjectName("po_format_editor_action")
        po_format_editor_action.setShortcut("Ctrl+P")
        po_format_editor_action.triggered.connect(callbacks["open_po_format_editor"])
        tools_menu.addAction(po_format_editor_action)

        # プレビュー
        preview_action = QAction("プレビュー", self.main_window)
        preview_action.setObjectName("preview_action")
        preview_action.setShortcut("Ctrl+R")
        preview_action.triggered.connect(callbacks["show_preview"])
        tools_menu.addAction(preview_action)

    def _setup_column_visibility_menu(self, toggle_callback: Callable[[int], None], table_manager: Any) -> None:
        """列表示設定メニューを設定
        
        Args:
            toggle_callback: 列の表示/非表示を切り替えるコールバック関数
            table_manager: テーブルマネージャーインスタンス
        """
        print("Setting up column visibility menu")
        if not self.column_visibility_menu:
            print("Column visibility menu not found")
            return
            
        # 既存のアクションをクリア
        self.column_visibility_menu.clear()
        self.column_visibility_actions.clear()
        
        # 各列の表示/非表示切り替えアクションを作成
        for i in range(table_manager.get_column_count()):
            column_name = table_manager.get_column_name(i)
            action = QAction(column_name, self.main_window)
            action.setObjectName(f"column_visibility_action_{i}")
            action.setCheckable(True)
            is_visible = table_manager.is_column_visible(i)
            action.setChecked(is_visible)
            print(f"Column {i} ({column_name}) is visible: {is_visible}")

            # インデックスを別の変数に保存してクロージャを回避
            index = i  # 現在のループ値をコピー
            
            # シンプルなQAction.triggered接続方法に変更
            action.triggered.connect(
                lambda checked=False, idx=index: self._handle_column_toggle(idx, toggle_callback)
            )
            
            self.column_visibility_menu.addAction(action)
            self.column_visibility_actions.append(action)
    
    def update_column_visibility_action(self, column_index: int, visible: bool) -> None:
        """列表示設定アクションの状態を更新
        
        Args:
            column_index: 列インデックス
            visible: 表示状態
        """
        print(f"Updating column visibility action for column {column_index} to {visible}")
        if 0 <= column_index < len(self.column_visibility_actions):
            self.column_visibility_actions[column_index].setChecked(visible)
            print(f"Action updated for column {column_index}")
        else:
            print(f"Column index {column_index} out of range (0-{len(self.column_visibility_actions)-1})")
    
    def _handle_column_toggle(self, index: int, toggle_callback: Callable[[int], None]) -> None:
        """列の表示/非表示を切り替えるハンドラー
        
        Args:
            index: 列インデックス
            toggle_callback: 列の表示/非表示を切り替えるコールバック関数
        """
        print(f"Menu clicked for column {index}")
        toggle_callback(index)
    
    def update_recent_files_menu(self, callback: Callable[[str], None]) -> None:
        """最近使用したファイルメニューを更新する

        Args:
            callback: 最近使用したファイルを開くコールバック
        """
        if not self.recent_files_menu or not callback:
            return

        # まず既存のアクションをクリア
        self.recent_files_menu.clear()
        self.recent_file_actions.clear()

        # 設定から最近使用したファイルのリストを取得
        settings = QSettings()
        recent_files = settings.value("recent_files", [])

        if not recent_files:
            # 最近使用したファイルがない場合
            no_files_action = QAction("最近使用した項目はありません", self.main_window)
            no_files_action.setEnabled(False)
            self.recent_files_menu.addAction(no_files_action)
            return

        # 最近使用したファイルのアクションを作成
        for filepath in recent_files:
            if not isinstance(filepath, str):
                continue

            action = QAction(Path(filepath).name, self.main_window)
            action.setData(filepath)
            action.setStatusTip(filepath)
            action.triggered.connect(
                lambda checked=False, path=filepath: callback(path)
            )
            self.recent_files_menu.addAction(action)
            self.recent_file_actions.append(action)

        self.recent_files_menu.addSeparator()

        # クリアアクション
        clear_action = QAction("履歴をクリア", self.main_window)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_files_menu.addAction(clear_action)

    def _clear_recent_files(self) -> None:
        """最近使用したファイルの履歴をクリア"""
        settings = QSettings()
        settings.setValue("recent_files", [])
        self.update_recent_files_menu(lambda _: None)

    def setup_toolbar(self, show_review_dialog_callback: Callable[[str], None]) -> None:
        """ツールバーの設定

        Args:
            show_review_dialog_callback: レビュー関連ダイアログを表示するコールバック
        """
        # レビューツールバーの作成
        toolbar = QToolBar("レビューツールバー", self.main_window)
        toolbar.setObjectName("review_toolbar")

        # 翻訳者コメントアクション
        translator_comment_action = QAction("翻訳者コメント", self.main_window)
        translator_comment_action.setObjectName("translator_comment_action")
        # ラムダ式ではなく、部分関数を使用してコールバックを設定

        def translator_callback():
            show_review_dialog_callback("translator_comment")

        translator_comment_action.triggered.connect(translator_callback)
        toolbar.addAction(translator_comment_action)
        self.toolbar_actions["translator_comment"] = translator_comment_action

        # レビューコメントアクション - 非表示
        review_comment_action = QAction("レビューコメント", self.main_window)
        review_comment_action.setObjectName("review_comment_action")
        review_comment_action.setVisible(False)  # 非表示に設定

        def review_callback():
            show_review_dialog_callback("review_comment")

        review_comment_action.triggered.connect(review_callback)
        toolbar.addAction(review_comment_action)
        self.toolbar_actions["review_comment"] = review_comment_action

        # 品質スコアアクション - 非表示
        quality_score_action = QAction("品質スコア", self.main_window)
        quality_score_action.setObjectName("quality_score_action")
        quality_score_action.setVisible(False)  # 非表示に設定

        def quality_callback():
            show_review_dialog_callback("quality_score")

        quality_score_action.triggered.connect(quality_callback)
        toolbar.addAction(quality_score_action)
        self.toolbar_actions["quality_score"] = quality_score_action

        # チェック結果アクション - 非表示
        check_result_action = QAction("チェック結果", self.main_window)
        check_result_action.setObjectName("check_result_action")
        check_result_action.setVisible(False)  # 非表示に設定

        def check_callback():
            show_review_dialog_callback("check_result")

        check_result_action.triggered.connect(check_callback)
        toolbar.addAction(check_result_action)
        self.toolbar_actions["check_result"] = check_result_action

        # デバッグアクション
        debug_action = QAction("デバッグ", self.main_window)
        debug_action.setObjectName("debug_action")

        def debug_callback():
            show_review_dialog_callback("debug")

        debug_action.triggered.connect(debug_callback)
        toolbar.addAction(debug_action)
        self.toolbar_actions["debug"] = debug_action

        # ツールバーをメインウィンドウに追加
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

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
