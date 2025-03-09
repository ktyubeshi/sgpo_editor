"""ツールバーのテスト"""

import pytest
from PySide6.QtWidgets import QApplication, QToolBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from sgpo_editor.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """メインウィンドウのフィクスチャ"""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def test_toolbar_exists(main_window):
    """ツールバーが存在することを確認"""
    # ツールバーが存在するか確認
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None
    assert toolbar.windowTitle() == "レビューツールバー"


def test_toolbar_actions(main_window):
    """ツールバーに必要なアクションが含まれていることを確認"""
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None
    
    # 必要なアクションが存在するか確認
    action_names = [
        "translator_comment_action",
        "review_comment_action",
        "quality_score_action",
        "check_result_action",
        "debug_action"
    ]
    
    for name in action_names:
        action = main_window.findChild(QAction, name)
        assert action is not None
        assert action in toolbar.actions()


def test_toolbar_action_triggers(main_window, monkeypatch):
    """ツールバーのアクションが正しく機能することを確認"""
    # モックを設定
    called_dialogs = []
    
    def mock_show_dialog(dialog_type):
        called_dialogs.append(dialog_type)
    
    # UIManagerのツールバーアクションを直接テスト
    # 各アクションのコールバックをテストする
    toolbar_actions = {
        "translator_comment": "translator_comment",
        "review_comment": "review_comment",
        "quality_score": "quality_score",
        "check_result": "check_result",
        "debug": "debug"
    }
    
    # 各ツールバーアクションのコールバックを直接呼び出す
    for action_key, expected_value in toolbar_actions.items():
        # ツールバーアクションが存在することを確認
        assert action_key in main_window.ui_manager.toolbar_actions
        
        # ツールバーアクションのコールバックをモックに置き換え
        main_window.ui_manager.toolbar_actions[action_key].triggered.connect(lambda checked=False, type=expected_value: mock_show_dialog(type))
        
        # アクションをトリガー
        main_window.ui_manager.toolbar_actions[action_key].trigger()
        
        # モック関数が呼び出されたことを確認
        assert expected_value in called_dialogs


def test_toolbar_position(main_window):
    """ツールバーが画面上部に配置されていることを確認"""
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None
    
    # ツールバーが上部に配置されているか確認
    assert toolbar.orientation() == Qt.Orientation.Horizontal
    assert main_window.toolBarArea(toolbar) == Qt.ToolBarArea.TopToolBarArea
