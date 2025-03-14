"""ツールバーのテスト"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

from sgpo_editor.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """メインウィンドウのフィクスチャ"""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture
def mock_dialog_manager():
    """ダイアログマネージャーのモック"""
    with patch("sgpo_editor.gui.main_window.DialogManager") as mock:
        instance = mock.return_value
        instance.show_dialog = Mock()
        yield instance


def test_toolbar_exists(main_window):
    """ツールバーが存在することを確認"""
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None
    assert toolbar.windowTitle() == "レビューツールバー"


def test_toolbar_actions(main_window):
    """ツールバーに必要なアクションが含まれていることを確認"""
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None

    action_names = [
        "translator_comment_action",
        "review_comment_action",
        "quality_score_action",
        "check_result_action",
        "debug_action",
    ]

    for name in action_names:
        action = main_window.findChild(QAction, name)
        assert action is not None
        assert action in toolbar.actions()


def test_toolbar_action_triggers(main_window, mock_dialog_manager):
    """ツールバーのアクションが正しく機能することを確認"""
    toolbar_actions = {
        "translator_comment": "translator_comment",
        "review_comment": "review_comment",
        "quality_score": "quality_score",
        "check_result": "check_result",
        "debug": "debug",
    }

    for action_key, expected_value in toolbar_actions.items():
        assert action_key in main_window.ui_manager.toolbar_actions
        main_window.ui_manager.toolbar_actions[action_key].trigger()
        mock_dialog_manager.show_dialog.assert_called_with(expected_value)


def test_toolbar_position(main_window):
    """ツールバーが画面上部に配置されていることを確認"""
    toolbar = main_window.findChild(QToolBar, "review_toolbar")
    assert toolbar is not None
    assert toolbar.orientation() == Qt.Orientation.Horizontal
    assert main_window.toolBarArea(toolbar) == Qt.ToolBarArea.TopToolBarArea


def test_toolbar_action_shortcuts(main_window):
    """ツールバーアクションのショートカットが正しく設定されていることを確認"""
    action_names = [
        "translator_comment_action",
        "review_comment_action",
        "quality_score_action",
        "check_result_action",
        "debug_action",
    ]

    for name in action_names:
        action = main_window.findChild(QAction, name)
        assert action is not None
        assert action.shortcut() is not None


def test_toolbar_action_icons(main_window):
    """ツールバーアクションのアイコンが正しく設定されていることを確認"""
    action_names = [
        "translator_comment_action",
        "review_comment_action",
        "quality_score_action",
        "check_result_action",
        "debug_action",
    ]

    for name in action_names:
        action = main_window.findChild(QAction, name)
        assert action is not None
        assert action.icon() is not None


def test_toolbar_action_tooltips(main_window):
    """ツールバーアクションのツールチップが正しく設定されていることを確認"""
    action_names = [
        "translator_comment_action",
        "review_comment_action",
        "quality_score_action",
        "check_result_action",
        "debug_action",
    ]

    for name in action_names:
        action = main_window.findChild(QAction, name)
        assert action is not None
        assert action.toolTip() != ""


def test_toolbar_action_error_handling(main_window, mock_dialog_manager):
    """ツールバーアクションのエラーハンドリングを確認"""
    # エラーを発生させるモックを設定
    mock_dialog_manager.show_dialog.side_effect = Exception("Test error")

    # エラーが発生してもアプリケーションがクラッシュしないことを確認
    for action_key in main_window.ui_manager.toolbar_actions:
        try:
            main_window.ui_manager.toolbar_actions[action_key].trigger()
        except Exception as e:
            pytest.fail(f"Action {action_key} raised an unexpected exception: {e}")
