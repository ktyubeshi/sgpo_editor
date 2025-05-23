"""UI設定モジュール

このモジュールは、UIコンポーネントの設定と管理に関する機能を提供します。
"""

import logging
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
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


# 非同期メソッドを呼び出すためのヘルパー関数
def run_async(coro):
    """非同期関数（コルーチンオブジェクト）をQtイベントループで実行するためのヘルパー関数"""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            return loop.create_task(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


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
        # ドックウィジェット参照を保持する辞書を追加
        self.dock_widgets = {
            "entry_editor": self.entry_editor_dock,
        }

        # メニューアクション
        self.layout1_action: Optional[QAction] = None
        self.layout2_action: Optional[QAction] = None

        # 最近使用したファイルのアクション
        self.recent_file_actions: List[QAction] = []
        self.recent_files_menu: Optional[QMenu] = None

        # 列表示設定のアクション
        self.column_visibility_actions: List[QAction] = []
        self.column_visibility_menu: Optional[QMenu] = None
        # クリアアクション用のインスタンス変数を初期化 (空のQAction)
        self.clear_recent_action: QAction = QAction(main_window)

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

        # 統計情報ドックをdock_widgets辞書に追加
        self.dock_widgets["stats"] = stats_dock

    def register_dock_widget(self, name: str, dock_widget: QDockWidget) -> None:
        """ドックウィジェットを登録

        Args:
            name: ドックウィジェットの名前
            dock_widget: ドックウィジェット
        """
        self.dock_widgets[name] = dock_widget

    def setup_window_menu(self) -> None:
        """ウィンドウメニューの設定"""
        window_menu = self.main_window.menuBar().addMenu("ウィンドウ")
        window_menu.setObjectName("window_menu")

        # 登録されたドックウィジェットごとにメニュー項目を作成
        for name, dock_widget in self.dock_widgets.items():
            action = QAction(dock_widget.windowTitle(), self.main_window)
            action.setCheckable(True)
            action.setChecked(dock_widget.isVisible())
            # pylint: disable=cell-var-from-loop
            action.triggered.connect(
                lambda checked, d=dock_widget: d.setVisible(checked)
            )
            window_menu.addAction(action)

    def setup_menubar(self, callbacks: Dict[str, Any]) -> None:
        """メニューバーの設定

        Args:
            callbacks: コールバック関数の辞書
              - open_file: ファイルを開く
              - save_file: ファイルを保存
              - save_file_as: 名前を付けて保存
              - close: アプリケーションを閉じる
              - change_layout: レイアウト変更
              - open_recent_file: 最近使用したファイルを開く
              - toggle_column_visibility: 列表示の切り替え
              - table_manager: テーブルマネージャ
              - open_po_format_editor: POフォーマットエディタを開く
              - show_preview: プレビューを表示
              - show_translation_evaluate: 翻訳品質評価ダイアログを表示
              - show_translation_evaluation_result: 翻訳品質評価結果ダイアログを表示
        """
        # ファイルメニュー
        file_menu = self.main_window.menuBar().addMenu("ファイル")

        # 開く - 非同期メソッドを呼び出せるように修正
        open_action = QAction("開く...", self.main_window)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(lambda: run_async(callbacks["open_file"]))
        file_menu.addAction(open_action)

        # 最近使用した項目を開く
        self.recent_files_menu = QMenu("最近使用した項目を開く", self.main_window)
        if self.recent_files_menu:
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
        if self.layout1_action:
            self.layout1_action.setObjectName("layout1_action")
            self.layout1_action.setCheckable(True)
            self.layout1_action.setChecked(True)
            self.layout1_action.triggered.connect(
                lambda: callbacks["change_layout"](LayoutType.LAYOUT1)
            )
            entry_edit_menu.addAction(self.layout1_action)

        # レイアウト2
        self.layout2_action = QAction("レイアウト2", self.main_window)
        if self.layout2_action:
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
        if self.column_visibility_menu:
            self.column_visibility_menu.setObjectName("column_visibility_menu")

        # テーブルマネージャが提供されている場合は列表示設定を構成
        if callbacks.get("table_manager") and callbacks.get("toggle_column_visibility"):
            self._setup_column_visibility_menu(
                callbacks["toggle_column_visibility"], callbacks["table_manager"]
            )

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

        # 翻訳品質評価
        if "show_translation_evaluate" in callbacks:
            translation_evaluate_action = QAction("翻訳品質評価", self.main_window)
            translation_evaluate_action.setObjectName("translation_evaluate_action")
            translation_evaluate_action.setShortcut("Ctrl+E")
            translation_evaluate_action.triggered.connect(
                callbacks["show_translation_evaluate"]
            )
            tools_menu.addAction(translation_evaluate_action)

        # 翻訳品質評価結果表示
        if "show_translation_evaluation_result" in callbacks:
            translation_result_action = QAction("翻訳品質評価結果", self.main_window)
            translation_result_action.setObjectName("translation_result_action")
            translation_result_action.setShortcut("Ctrl+Shift+E")
            translation_result_action.triggered.connect(
                callbacks["show_translation_evaluation_result"]
            )
            tools_menu.addAction(translation_result_action)

    def _setup_column_visibility_menu(
        self, toggle_callback: Callable[[int], None], table_manager: Any
    ) -> None:
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
                lambda checked=False, idx=index: self._handle_column_toggle(
                    idx, toggle_callback
                )
            )

            self.column_visibility_menu.addAction(action)
            self.column_visibility_actions.append(action)

    def update_column_visibility_action(self, column_index: int, visible: bool) -> None:
        """列表示設定アクションの状態を更新

        Args:
            column_index: 列インデックス
            visible: 表示状態
        """
        print(
            f"Updating column visibility action for column {column_index} to {visible}"
        )
        if 0 <= column_index < len(self.column_visibility_actions):
            self.column_visibility_actions[column_index].setChecked(visible)
            print(f"Action updated for column {column_index}")
        else:
            print(
                f"Column index {column_index} out of range (0-{len(self.column_visibility_actions) - 1})"
            )

    def _handle_column_toggle(
        self, index: int, toggle_callback: Callable[[int], None]
    ) -> None:
        """列の表示/非表示を切り替えるハンドラー

        Args:
            index: 列インデックス
            toggle_callback: 列の表示/非表示を切り替えるコールバック関数
        """
        print(f"Menu clicked for column {index}")
        toggle_callback(index)

    def update_recent_files_menu(
        self, callback: Optional[Callable[[str], Any]]
    ) -> None:
        """最近使用したファイルメニューの更新

        Args:
            callback: 最近使用したファイルを開くためのコールバック（非同期関数も可）
        """
        if not callback or not self.recent_files_menu:
            return

        # 既存のアクションをクリア
        self.recent_files_menu.clear()
        self.recent_file_actions.clear()

        # FileHandler経由で最近使ったファイルリストを取得
        recent_files: list[str]
        if hasattr(self.main_window, "file_handler") and hasattr(
            self.main_window.file_handler, "get_recent_files"
        ):
            try:
                recent_files = list(self.main_window.file_handler.get_recent_files())
            except Exception:
                recent_files = []
        else:
            # フォールバック: QSettingsから取得
            settings = QSettings()
            recent_files_json = settings.value("recent_files", "[]")
            try:
                recent_files = json.loads(recent_files_json)
            except json.JSONDecodeError:
                recent_files = []
                logger.warning("Failed to load recent files setting.")

        num_recent_files = len(recent_files)

        # メニュー項目を作成
        for i, file_path_str in enumerate(recent_files):
            file_path = Path(file_path_str)
            # ファイルが存在するか確認
            if not file_path.exists():
                logger.warning(f"Recent file not found, removing: {file_path_str}")
                # ここでリストから削除するロジックを追加するべき
                continue

            action_text = f"&{i + 1}. {file_path.name}"
            action = QAction(action_text, self.main_window)
            action.setData(file_path_str)  # ファイルパスをデータとして保持
            # functools.partial を使ってコールバックに関数を渡す
            action.triggered.connect(
                lambda checked=False, p=file_path_str: run_async(callback(p))
            )
            self.recent_files_menu.addAction(action)
            self.recent_file_actions.append(action)

        # ファイル履歴がある場合は区切り線とクリアアクションを追加
        if num_recent_files > 0:
            self.recent_files_menu.addSeparator()

            # クリアアクションを作成し、インスタンス変数に設定
            self.clear_recent_action.setText("履歴をクリア (&C)")
            # 接続済みの場合は再接続しない (または古い接続を解除)
            try:
                self.clear_recent_action.triggered.disconnect()
            except RuntimeError:
                pass  # まだ接続されていない
            self.clear_recent_action.triggered.connect(self._clear_recent_files)
            self.clear_recent_action.setEnabled(True)  # 履歴があるので有効化
            self.recent_files_menu.addAction(self.clear_recent_action)
        else:
            # 履歴がない場合は「履歴なし」を表示し、クリアアクションを無効化
            no_history_action = QAction("(履歴なし)", self.main_window)
            no_history_action.setEnabled(False)
            self.recent_files_menu.addAction(no_history_action)
            # クリアアクション自体は存在し続けるが、無効化してテキストをクリア
            self.clear_recent_action.setText("")  # テキストを空に
            self.clear_recent_action.setEnabled(False)
            # self.clear_recent_action = None # None にはしない

    def _clear_recent_files(self) -> None:
        """最近使用したファイル履歴をクリアする内部メソッド"""
        settings = QSettings()
        settings.setValue("recent_files", json.dumps([]))
        settings.sync()
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
